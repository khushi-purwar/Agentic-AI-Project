from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

def pick_llm(level: str):
    """
    Picks the appropriate LLM based on the level of the question.

    Args:
        level (str): The level of the question to determine the appropriate LLM.

    Returns:
        ChatGroq: The instance of the selected LLM to be used.
    """
    if level.lower() == "low":
        llm = ChatGroq(model="openai/gpt-oss-20b",temperature=0, reasoning_effort="low")
    elif level.lower() == "medium":
        llm = ChatGroq(model="openai/gpt-oss-20b",temperature=0, reasoning_effort="low")
    elif level.lower() == "high":
        llm = ChatGroq(model="openai/gpt-oss-120b",temperature=0, reasoning_effort="low")
    else:
        raise ValueError(f"Unsupported level: {level}")

    return llm
