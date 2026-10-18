import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_pick import pick_llm
from models.schema import RouterSchema, DataAgentSchema
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool

llm = pick_llm("high")
llm_router = llm.with_structured_output(RouterSchema)

# ---------------------------- DATA AGENT GRAPH ---------------------------- 

def router_node(state:DataAgentSchema):

    message = state.messages[-1].content
    route_response_dict = llm_router.invoke(message).model_dump()
    route_response = route_response_dict['answer']

    state.route_response = route_response
    return state



def etl_node(state: DataAgentSchema):
    message = state.messages[-1].content

    response = etl_analyst.invoke({
        "messages": [HumanMessage(content=message)]
    })

    # Extract the final AI message from the ETL response
    final_answer = response.get("final_answer", "")

    if not final_answer:
        for item in reversed(response.get("messages", [])):
            if isinstance(item, dict):
                nested_messages = item.get("messages", [])
                for msg in reversed(nested_messages):
                    if isinstance(msg, AIMessage) and msg.content.strip():
                        final_answer = msg.content
                        break
            elif isinstance(item, AIMessage) and item.content.strip():
                final_answer = item.content

            if final_answer:
                break

    state.messages = state.messages + [
        AIMessage(content=final_answer or "The ETL operation finished without a response.")
    ]

    return state


def sql_node(state:DataAgentSchema):

    message = state.messages[-1].content

    input_schema = {
        "messages": [],
        "user_input": f"{message}",
        "curated_question": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    response = sql_analyst.invoke(input_schema)

    # Extract the final answer from the SQL agent
    final_answer = response["final_answer"]

    state.messages = state.messages + [AIMessage(content=final_answer)]

    return state

# --------------------- GRAPH CREATION------------------------

data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")

data_agent_graph.add_conditional_edges("router_node", route_edge, {"sql_node": "sql_node", "etl_node": "etl_node"})
data_agent = data_agent_graph.compile()

# Optional to generate the compiled graph
from IPython.display import display, Image
img = Image(data_agent.get_graph().draw_mermaid_png())
with open("data_agent_graph.png", "wb") as f:
    f.write(img.data)