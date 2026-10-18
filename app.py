
import sys
from PIL import Image
from pathlib import Path
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

# --------------------------------------------------
# Project paths and imports
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from main import data_agent


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="AI Data Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "question_input" not in st.session_state:
    st.session_state.question_input = ""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --------------------------------------------------
# Main header
# --------------------------------------------------

st.title("🤖 AI Data Agent")
st.caption(
    "Your intelligent assistant for database queries, "
    "data extraction, and transformation."
)


# --------------------------------------------------
# Tabs
# --------------------------------------------------

overview_tab, ask_tab, workflow_tab = st.tabs(
    [
        "🏠 Overview",
        "💬 Ask Data Agent",
        "🔀 Workflow",
    ]
)


# --------------------------------------------------
# Tab 1: Overview
# --------------------------------------------------

with overview_tab:

    st.header("Welcome to the AI Data Agent")

    st.write(
        """
        The AI Data Agent is a natural-language interface for working
        with databases and data pipelines. Ask a question or describe
        a data operation, and the router sends your request to the
        appropriate analyst.
        """
    )

    st.divider()

    st.subheader("Available capabilities")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.subheader("🗄️ SQL Analyst")

            st.write(
                """
                Query your database using natural language.
                The SQL Analyst interprets the request, generates
                SQL, executes safe queries, and returns the result.
                """
            )

            st.markdown(
                """
                **Example questions**
                - What payment methods are available?
                - How many rides were completed?
                - What is the average ride fare?
                """
            )

    with col2:
        with st.container(border=True):
            st.subheader("🔄 ETL Analyst")

            st.write(
                """
                Extract data from APIs and perform data
                transformation operations. The analyst uses
                the appropriate tools to process and save data.
                """
            )

            st.markdown(
                """
                **Example requests**
                - Extract data from a REST API.
                - Save API data as a CSV file.
                - Filter a dataset to include specific records.
                """
            )

    st.divider()

    st.subheader("How it works")

    st.markdown(
        """
        1. **Ask:** Enter your question in the Ask Data Agent tab.
        2. **Route:** The router determines whether SQL or ETL is needed.
        3. **Execute:** The selected analyst processes your request.
        4. **Respond:** The application displays the final answer.
        5. **Visualize:** Open the Workflow tab to view the relevant analyst graph.
        """
    )


# --------------------------------------------------
# Tab 2: Ask Data Agent
# --------------------------------------------------

with ask_tab:

    st.header("Ask Data Agent")

    st.write(
        "Enter a database question or describe the data operation "
        "you want to perform."
    )

    # clear_on_submit resets the question field after submission.
    with st.form("question_form", clear_on_submit=True):

        question = st.text_area(
            "Question",
            key="question_input",
            placeholder=(
                "Examples:\n"
                "What payment methods are available in the database?\n"
                "Extract data from https://pokeapi.co/api/v2/pokemon\n"
            ),
            height=130,
        )

        submitted = st.form_submit_button(
            "Ask Data Agent",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        if not question.strip():
            st.warning("Please enter a question.")

        else:

            with st.spinner("Processing your question..."):

                try:
                    response = data_agent.invoke(
                        {
                            "messages": [
                                HumanMessage(
                                    content=question.strip()
                                )
                            ],
                            "route_response": "",
                        }
                    )

                    # Determine which analyst handled the request.
                    route = str(
                        response.get("route_response", "")
                    ).lower()

                    # Find the final non-empty AI message.
                    messages = response.get("messages", [])
                    answer = None

                    for message in reversed(messages):

                        if (
                            isinstance(message, AIMessage)
                            and isinstance(message.content, str)
                            and message.content.strip()
                        ):
                            answer = message.content
                            break

                    if not answer:
                        answer = (
                            "The agent completed, but no final "
                            "answer was returned."
                        )

                    # Save the question, answer, and route.
                    st.session_state.chat_history.append(
                        {
                            "question": question.strip(),
                            "answer": answer,
                            "route": route,
                        }
                    )

                except Exception as exc:
                    st.error(
                        f"An error occurred while processing "
                        f"your question: {exc}"
                    )

    # Display the most recent answer first.
    if st.session_state.chat_history:

        st.divider()

        for item in reversed(st.session_state.chat_history):

            st.markdown("**Question:**")
            st.write(item["question"])

            route_label = item.get("route", "unknown").upper()
            st.caption(f"Routed to: {route_label} Analyst")

            st.markdown("**Answer:**")
            st.markdown(item["answer"])

            st.divider()

    else:
        st.info(
            "Your question and its answer will appear here."
        )


# --------------------------------------------------
# Tab 3: Workflow
# --------------------------------------------------

def display_workflow_image(image_path, graph_title):
    """Display a centered, resized workflow image."""

    image_path = BASE_DIR / image_path

    if not image_path.exists():
        st.warning(f"Workflow image not found: {image_path}")
        return

    with Image.open(image_path) as img:
        workflow_img = img.copy()

    max_width = 1000

    if workflow_img.width > max_width:
        new_height = int(
            workflow_img.height * max_width / workflow_img.width
        )

        workflow_img = workflow_img.resize(
            (max_width, new_height),
            Image.Resampling.LANCZOS,
        )

    # Center the diagram using three columns
    left_col, center_col, right_col = st.columns([1, 3, 1])

    with center_col:
        st.image(
            workflow_img,
            caption=graph_title,
            use_container_width=True,
        )



# --------------------------------------------------
# Tab 3: Workflow
# --------------------------------------------------

def display_workflow_image(image_path, caption, max_width=650):
    """Display a centered, resized workflow diagram."""

    image_path = Path(image_path)

    if not image_path.exists():
        st.warning(f"Workflow image not found: {image_path}")
        return

    with Image.open(image_path) as img:
        workflow_img = img.copy()

    # Resize while preserving aspect ratio
    if workflow_img.width > max_width:
        new_height = int(
            workflow_img.height * max_width / workflow_img.width
        )

        workflow_img = workflow_img.resize(
            (max_width, new_height),
            Image.Resampling.LANCZOS,
        )

    # Center the image horizontally
    _, center_col, _ = st.columns([1, 3, 1])

    with center_col:
        st.image(
            workflow_img,
            caption=caption,
            use_container_width=False,
        )


with workflow_tab:

    st.header("Agent Workflow")

    # Default workflow before any question is submitted
    workflow_image_path = BASE_DIR / "data_agent_graph.png"
    graph_title = "Data Agent Workflow"
    description = (
        "Default workflow: the Data Agent routes the user's "
        "question to the appropriate analyst."
    )

    # Display the workflow associated with the latest question
    if st.session_state.chat_history:

        latest_route = (
            st.session_state.chat_history[-1]
            .get("route", "")
            .lower()
        )

        if latest_route == "etl":
            workflow_image_path = BASE_DIR / "etl_analyst_graph.png"
            graph_title = "ETL Analyst Workflow"
            description = (
                "Your question was routed to the ETL Analyst. "
                "Here is the ETL Analyst workflow diagram."
            )

        elif latest_route == "sql":
            workflow_image_path = BASE_DIR / "sql_analyst_graph.png"
            graph_title = "SQL Analyst Workflow"
            description = (
                "Your question was routed to the SQL Analyst. "
                "Here is the SQL Analyst workflow diagram."
            )

    st.markdown(f"### {graph_title}")
    st.write(description)

    display_workflow_image(
        workflow_image_path,
        caption=graph_title,
        max_width=650,
    )
