from agents.data_agent import data_agent
from langchain_core.messages import HumanMessage

if __name__ == "__main__":

    # Extract tool testing
    # response = data_agent.invoke(
    #     {"messages":[HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder")],
    #      "route_response": ""}
    # )
    # print(response)

    # Transform tool testing
    response = data_agent.invoke(
         {"messages":[HumanMessage(content=f"""
            I want to transform the data stored in the 'C:\\Users\\v-kpurwar\\Downloads\\demo\\AI Agent Project\\data\\extract\\extracted_data.csv' file 
            and save the transformed data in the 'C:\\Users\\v-kpurwar\\Downloads\\demo\\AI Agent Project\\data\\transform' folder in the csv format.
            The transformation should filter the data to show squirtle pokemon only.
            """)], "route_response": ""}
    )  

    print(response)

    # # SQL Analyst testing
    # response = data_agent.invoke(
    #      {"messages":[HumanMessage(content=f"""
    #         What are the different types of Payment Methods we have in our database
    #     """)], "route_response": ""}
    # )  

    # print(response['messages'][-1].content)
