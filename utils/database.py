import sqlite3


class DatabaseUtil:

    def __init__(self, db_path="agenticai.db"):
        self.db_path = db_path

    def schema_details(self, schema_name="main"):

        schema_info_context = f"Database Schema: {schema_name}\n"

        try:
            with sqlite3.connect(self.db_path) as connection:

                cursor = connection.cursor()

                # Get all tables
                cursor.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                    ORDER BY name;
                """)

                tables_list = cursor.fetchall()

                for table in tables_list:
                    table_name = table[0]

                    schema_info_context += (
                        f"\nTable: {table_name}\n"
                    )

                    # Get column names and data types
                    cursor.execute(
                        f'PRAGMA table_info("{table_name}")'
                    )

                    columns_list = cursor.fetchall()

                    for column in columns_list:
                        column_name = column[1]
                        data_type = column[2]

                        schema_info_context += (
                            f"  Column: {column_name}, "
                            f"Data Type: {data_type}\n"
                        )

                    # Get sample data
                    cursor.execute(
                        f'SELECT * FROM "{table_name}" LIMIT 5'
                    )

                    sample_data = cursor.fetchall()

                    schema_info_context += "  Sample Data:\n"

                    for row in sample_data:
                        schema_info_context += f"    {row}\n"

        except sqlite3.Error as e:
            schema_info_context = (
                f"Error fetching schema details: {e}"
            )

        return schema_info_context

    def execute_sql(self, query, params=()):

        try:
            with sqlite3.connect(self.db_path) as connection:

                # Enable foreign-key enforcement
                connection.execute("PRAGMA foreign_keys = ON")

                cursor = connection.cursor()
                cursor.execute(query, params)

                # Return rows only when the query produces a result set
                if cursor.description is not None:
                    result = cursor.fetchall()
                    return str(result)

                return f"Query executed successfully. Rows affected: {cursor.rowcount}"

        except sqlite3.Error as e:
            print(f"Error executing query: {e}")
            return None



# ============================================================
# USAGE
# ============================================================

if __name__ == "__main__":  # Run the following code only if this Python file is executed directly.
    obj = DatabaseUtil("agenticai.db")

    # Fetch schema details
    result = obj.schema_details("main")

    with open(
        "test_schema_details.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(result)

    print("Schema details saved successfully.")
