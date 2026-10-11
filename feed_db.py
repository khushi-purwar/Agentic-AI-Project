import csv
import sqlite3
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "agenticai.db"

# Set to True to delete existing records and reload all CSV data.
# Set to False to preserve existing records.
CLEAR_EXISTING_DATA = True


# ============================================================
# DATABASE SCHEMA
# ============================================================

CREATE_TABLES_SQL = """

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    city VARCHAR(100),
    province VARCHAR(50),
    user_type VARCHAR(20) NOT NULL,
    signup_date DATE,
    is_active BOOLEAN
);


CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY,
    driver_id INTEGER NOT NULL,
    make VARCHAR(50),
    model VARCHAR(50),
    year INTEGER,
    license_plate VARCHAR(20) UNIQUE,
    color VARCHAR(30),
    is_active BOOLEAN,

    CONSTRAINT fk_vehicle_driver
        FOREIGN KEY (driver_id)
        REFERENCES users(user_id)
);


CREATE TABLE IF NOT EXISTS rides (
    ride_id INTEGER PRIMARY KEY,
    rider_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,

    requested_at TIMESTAMP,
    pickup_time TIMESTAMP,
    dropoff_time TIMESTAMP,

    pickup_latitude DECIMAL(9,6),
    pickup_longitude DECIMAL(9,6),
    dropoff_latitude DECIMAL(9,6),
    dropoff_longitude DECIMAL(9,6),

    distance_km DECIMAL(10,2),
    fare DECIMAL(10,2),
    surge_multiplier DECIMAL(4,2),

    status VARCHAR(30),
    cancellation_reason VARCHAR(100),

    CONSTRAINT fk_ride_rider
        FOREIGN KEY (rider_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_ride_driver
        FOREIGN KEY (driver_id)
        REFERENCES users(user_id)
);


CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY,
    ride_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,

    amount DECIMAL(10,2),
    payment_method VARCHAR(50),
    payment_status VARCHAR(30),

    transaction_id VARCHAR(100) UNIQUE,
    payment_time TIMESTAMP,

    CONSTRAINT fk_payment_ride
        FOREIGN KEY (ride_id)
        REFERENCES rides(ride_id),

    CONSTRAINT fk_payment_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);


CREATE TABLE IF NOT EXISTS ratings (
    rating_id INTEGER PRIMARY KEY,
    ride_id INTEGER NOT NULL,
    rider_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,

    rating INTEGER,
    comment TEXT,
    rated_at TIMESTAMP,

    CONSTRAINT fk_rating_ride
        FOREIGN KEY (ride_id)
        REFERENCES rides(ride_id),

    CONSTRAINT fk_rating_rider
        FOREIGN KEY (rider_id)
        REFERENCES users(user_id),

    CONSTRAINT fk_rating_driver
        FOREIGN KEY (driver_id)
        REFERENCES users(user_id),

    CONSTRAINT chk_rating
        CHECK (rating BETWEEN 1 AND 5)
);


-- ==========================================================
-- INDEXES
-- ==========================================================

CREATE INDEX IF NOT EXISTS idx_vehicles_driver_id
ON vehicles(driver_id);

CREATE INDEX IF NOT EXISTS idx_rides_rider_id
ON rides(rider_id);

CREATE INDEX IF NOT EXISTS idx_rides_driver_id
ON rides(driver_id);

CREATE INDEX IF NOT EXISTS idx_rides_requested_at
ON rides(requested_at);

CREATE INDEX IF NOT EXISTS idx_rides_status
ON rides(status);

CREATE INDEX IF NOT EXISTS idx_payments_ride_id
ON payments(ride_id);

CREATE INDEX IF NOT EXISTS idx_payments_user_id
ON payments(user_id);

CREATE INDEX IF NOT EXISTS idx_ratings_ride_id
ON ratings(ride_id);

CREATE INDEX IF NOT EXISTS idx_ratings_driver_id
ON ratings(driver_id);

"""


# ============================================================
# CSV COLUMN CONFIGURATION
# ============================================================

TABLE_COLUMNS = {
    "users": [
        "user_id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "city",
        "province",
        "user_type",
        "signup_date",
        "is_active",
    ],

    "vehicles": [
        "vehicle_id",
        "driver_id",
        "make",
        "model",
        "year",
        "license_plate",
        "color",
        "is_active",
    ],

    "rides": [
        "ride_id",
        "rider_id",
        "driver_id",
        "requested_at",
        "pickup_time",
        "dropoff_time",
        "pickup_latitude",
        "pickup_longitude",
        "dropoff_latitude",
        "dropoff_longitude",
        "distance_km",
        "fare",
        "surge_multiplier",
        "status",
        "cancellation_reason",
    ],

    "payments": [
        "payment_id",
        "ride_id",
        "user_id",
        "amount",
        "payment_method",
        "payment_status",
        "transaction_id",
        "payment_time",
    ],

    "ratings": [
        "rating_id",
        "ride_id",
        "rider_id",
        "driver_id",
        "rating",
        "comment",
        "rated_at",
    ],
}


# CSV files and their corresponding tables
CSV_FILES = {
    "users": "users.csv",
    "vehicles": "vehicles.csv",
    "rides": "rides.csv",
    "payments": "payments.csv",
    "ratings": "ratings.csv",
}


# Columns that should be stored as SQLite integers 0 or 1
BOOLEAN_COLUMNS = {
    "users": {"is_active"},
    "vehicles": {"is_active"},
}


# ============================================================
# HELPER: CONVERT CSV VALUES
# ============================================================

def clean_value(value, table_name, column_name):
    """
    Convert CSV values into appropriate SQLite values.

    Empty strings become NULL.
    Boolean strings become 1 or 0.
    Other values are returned as strings; SQLite applies
    the column's type affinity where appropriate.
    """

    if value is None:
        return None

    value = value.strip()

    if value == "":
        return None

    if column_name in BOOLEAN_COLUMNS.get(table_name, set()):
        normalized = value.lower()

        if normalized in ("true", "1", "yes"):
            return 1

        if normalized in ("false", "0", "no"):
            return 0

        raise ValueError(
            f"Invalid Boolean value in {table_name}.{column_name}: "
            f"{value!r}"
        )

    return value


# ============================================================
# CREATE DATABASE, TABLES, AND INDEXES
# ============================================================

def create_database(conn):
    conn.executescript(CREATE_TABLES_SQL)
    print("Tables and indexes created successfully.")


# ============================================================
# OPTIONAL: CLEAR EXISTING DATA
# ============================================================

def clear_existing_data(conn):
    """
    Delete child records before parent records to satisfy
    foreign-key constraints.
    """

    deletion_order = [
        "ratings",
        "payments",
        "rides",
        "vehicles",
        "users",
    ]

    for table in deletion_order:
        conn.execute(f"DELETE FROM {table}")

    print("Existing records deleted.")


# ============================================================
# LOAD CSV DATA
# ============================================================

def load_csv(conn, table_name, csv_file):
    """
    Load a CSV file into its corresponding SQLite table.
    The CSV header must contain the expected column names.
    """

    file_path = CSV_DIR / csv_file

    if not file_path.is_file():
        raise FileNotFoundError(
            f"CSV file not found: {file_path}"
        )

    columns = TABLE_COLUMNS[table_name]

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"CSV file has no header: {file_path}"
            )

        # Validate required column names.
        missing_columns = set(columns) - set(reader.fieldnames)

        if missing_columns:
            raise ValueError(
                f"{csv_file} is missing columns: "
                f"{sorted(missing_columns)}"
            )

        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(f'"{c}"' for c in columns)

        insert_sql = (
            f'INSERT INTO "{table_name}" '
            f"({column_sql}) VALUES ({placeholders})"
        )

        rows = []

        for row_number, row in enumerate(reader, start=2):
            try:
                values = tuple(
                    clean_value(
                        row.get(column),
                        table_name,
                        column
                    )
                    for column in columns
                )
            except ValueError as exc:
                raise ValueError(
                    f"{csv_file}, row {row_number}: {exc}"
                ) from exc

            rows.append(values)

        conn.executemany(insert_sql, rows)

    print(f"Loaded {len(rows):,} records from {csv_file}.")


# ============================================================
# VERIFY RECORD COUNTS
# ============================================================

def verify_record_counts(conn):
    print("\nRecord counts:")
    print("-" * 40)

    for table_name in TABLE_COLUMNS:
        result = conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}"'
        )

        count = result.fetchone()[0]

        print(f"{table_name:<15} {count:>10,}")


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    # Create the CSV directory only if you need it.
    if not CSV_DIR.is_dir():
        raise FileNotFoundError(
            f"CSV directory does not exist: {CSV_DIR}"
        )

    # Open or create the SQLite database.
    conn = sqlite3.connect(DB_PATH)

    try:
        # Enable foreign-key enforcement for this connection.
        conn.execute("PRAGMA foreign_keys = ON")

        # Create tables and indexes.
        create_database(conn)

        # Execute the data load as a transaction.
        with conn:
            if CLEAR_EXISTING_DATA:
                clear_existing_data(conn)

            # Parent table first, then dependent tables.
            for table_name in [
                "users",
                "vehicles",
                "rides",
                "payments",
                "ratings",
            ]:
                load_csv(
                    conn,
                    table_name,
                    CSV_FILES[table_name]
                )

            # Check counts before the transaction commits.
            verify_record_counts(conn)

        print("\nData loaded successfully!")
        print("Transaction committed.")

        # Check foreign-key consistency.
        violations = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            print("\nForeign-key violations detected:")
            for violation in violations:
                print(violation)
        else:
            print("Foreign-key check passed.")

        print(f"\nDatabase location: {DB_PATH.resolve()}")

    except Exception:
        # Undo uncommitted data changes on failure.
        conn.rollback()
        print("\nError occurred. Uncommitted changes rolled back.")
        raise

    finally:
        conn.close()
        print("SQLite connection closed.")


if __name__ == "__main__":
    main()

## Testing

# conn = sqlite3.connect("agenticai.db")

# tables = conn.execute("""
#     SELECT name
#     FROM sqlite_master
#     WHERE type = 'table'
#     ORDER BY name
# """).fetchall()

# print("Tables:", tables)

# users = conn.execute("""
#     SELECT user_id, first_name, last_name, email
#     FROM users
#     LIMIT 5
# """).fetchall()

# for user in users:
#     print(user)

# conn.close()