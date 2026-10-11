import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from models.schema import AgentSchema, JudgeSchema
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from IPython.display import display, Image

#  --------------- AI Agent Code ----------------------

def curate_question(state: AgentSchema) -> AgentSchema:
    """
    Curates a question based on the user input.

    Args:
        state (AgentSchema): The current state of the agent containing relevant information.

    Returns:
        AgentSchema: The updated state of the agent with the curated question.
    """
    
    user_question = state.user_input ### Because this is a Pydantic model object
    llm = pick_llm("low") # Pick the appropriate LLM based on the level of the question

    response = llm.invoke(f"Curate the following question: {user_question}").content
    state.curated_question = response
    state.messages = state.messages + [HumanMessage(content=f"{response}")]
    return state

# Provide SQL DB context for the agent to generate the SQL query
def prompt_query_context(state: AgentSchema) -> AgentSchema:
    """
    Generates a detailed prompt with SQL DB context based on the curated question.

    Args:
        state (AgentSchema): The current state of the agent containing relevant information.

    Returns:
        AgentSchema: The updated state of the agent with the prompt query context.
    """

    curated_question = state.curated_question
    db_obj = DatabaseUtil("agenticai.db")

    # Fetch schema details
    schema_info = db_obj.schema_details("main")
    
    # Constructing the prompt query for the agent to generate the SQL query
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications. 

    User's Original Query: {curated_question}

    Database Schema Details:
    {schema_info}
    
    """    
    state.prompt_query_context = prompt
    return state

# Generate SQL Query
def generate_sql_query(state: AgentSchema) -> AgentSchema:
    """
    Generates the SQL query based on the prompt query context.

    Args:
        state (AgentSchema): The current state of the agent containing relevant information.

    Returns:
        AgentSchema: The updated state of the agent with the generated SQL query.
    """

    prompt = state.prompt_query_context
    llm = pick_llm("medium") # Pick the appropriate LLM based on the level of the question
    generated_sql_query = llm.invoke(prompt).content # Generate the SQL query based on the prompt
    state.generated_sql_query = generated_sql_query
    return state

# Is Safe Node
def is_safe_sql(state: AgentSchema) -> AgentSchema:
    """
    Determines whether the generated SQL query is safe to execute.

    Args:
        state (AgentSchema): The current state of the agent containing relevant information.

    Returns:
        AgentSchema: The updated state of the agent with the safety status of the SQL query.
    """

    generated_sql_query = state.generated_sql_query
    llm = pick_llm("medium") # Pick the appropriate LLM based on the level of the question
    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.

    Here is the SQL query to evaluate:
    {generated_sql_query}
    """

    judge_response = llm_judge.invoke(prompt).model_dump()  # Convert the structured output to a dictionary
    state.is_safe = judge_response.get("answer")
    state.comments = judge_response.get("comments")
    return state

# Cancelled SQL Node
def cancelled_sql_execution(state: AgentSchema) -> AgentSchema:
    """
    Handles the scenario when the SQL query execution is cancelled.

    Args:
        state (AgentSchema): The current state of the agent containing relevant information.

    Returns:
        AgentSchema: The updated state of the agent indicating the cancellation.
    """

    comments = state.comments
    state.final_answer = f"The generated SQL query was deemed unsafe to execute. The reason provided by the judge is: {comments}. Therefore, the SQL query will not be executed."
    state.messages = state.messages + [AIMessage(content=f"{state.final_answer}")]  # Append the final answer to the messages list  
    return state

# Executed SQL Node
def execute_sql_query(state: AgentSchema) -> AgentSchema:
    """
    Handles the scenario when the SQL query has been successfully executed.

    Args:
        state (AgentSchema): The current state of the agent containing relevant information.

    Returns:
        AgentSchema: The updated state of the agent indicating successful execution.
    """

    sql_query = state.generated_sql_query

    db_obj = DatabaseUtil("agenticai.db")

    result = db_obj.execute_sql(sql_query) # Execute the SQL query and fetch the result
    state.sql_query_execution_result = result
    return state

# Represent the final answer Node

def represent_final_answer(state: AgentSchema) -> AgentSchema:
    """
    Handles the scenario when the agent needs to represent the final answer based on the SQL query execution result.

    Args:
        state (AgentSchema): The current state of the agent containing relevant information.

    Returns:
        AgentSchema: The updated state of the agent with the final answer.
    """

    execution_result = state.sql_query_execution_result
    curated_question = state.curated_question

    llm = pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """

    llm_response = llm.invoke(prompt).content  # Get the final answer from the LLM

    state.final_answer = llm_response
    state.messages = state.messages + [AIMessage(content=f"{llm_response}")]  # Append the final answer to the messages list
    return state


# ------------------- Graph Building ----------------------------------

sql_agent_graph = StateGraph(AgentSchema)

## Nodes
sql_agent_graph.add_node("curate_question", curate_question)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql_query", generate_sql_query)
sql_agent_graph.add_node("is_safe_sql", is_safe_sql)
sql_agent_graph.add_node("cancelled_sql_execution", cancelled_sql_execution)
sql_agent_graph.add_node("execute_sql_query", execute_sql_query)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)

# Edges

sql_agent_graph.add_edge(START, "curate_question")
sql_agent_graph.add_edge("curate_question", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql_query")
sql_agent_graph.add_edge("generate_sql_query", "is_safe_sql")

# Conditional edge function
def is_safe_sql_conditional_edge(state: AgentSchema) -> str:
    is_safe = state.is_safe

    if is_safe.lower() == "yes":
        return "execute_sql_query" ## Node name

    else:
        return "cancelled_sql_execution"

# Explicitly map the conditional destinations
sql_agent_graph.add_conditional_edges(
    "is_safe_sql",
    is_safe_sql_conditional_edge,
    {
        "execute_sql_query": "execute_sql_query",
        "cancelled_sql_execution": "cancelled_sql_execution",
    }
)

sql_agent_graph.add_edge("cancelled_sql_execution", END)
sql_agent_graph.add_edge("execute_sql_query", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)

# Compile the Graph
sql_analyst = sql_agent_graph.compile()


if __name__ == "__main__":

    # To view the compiled graph
    img = Image(sql_analyst.get_graph().draw_mermaid_png())
    with open("sql_analyst_graph.png", "wb") as f:
        f.write(img.data)

   # define the input schema for the graph execution
    input_schema = {
            "messages": [],
            "user_input": "What are the different types of Payment Methods we have in our database",
            "curated_question": "",
            "prompt_query_context": "",
            "generated_sql_query": "",
            "is_safe": "No",
            "comments": "",
            "sql_query_execution_result": "",
            "final_answer": ""
        }

    # Execute the Graph
    sql_analyst_response = sql_analyst.invoke(input_schema)

    print(sql_analyst_response['messages'])  # Print the final output of the graph execution
    
    print("********************************")

    print(sql_analyst_response['generated_sql_query'])  # Print the generated SQL query

    print("********************************")

    print(sql_analyst_response['sql_query_execution_result'])  # Print the result of executing the SQL query

    print("********************************")

    print(sql_analyst_response['prompt_query_context'])  # Print the prompt query context

    print("********************************")

    print(sql_analyst_response['final_answer'])  # Print the final_answer
