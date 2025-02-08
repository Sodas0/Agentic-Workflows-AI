import json
from langchain_core.messages import ToolMessage
from langchain_community.tools import tool
from retrievertool import generate_retriever_tool
from langchain_openai import ChatOpenAI



class BasicToolNode:
    """
    A node that processes and executes tool requests embedded in the last AI message.
    """

    def __init__(self, tools: list) -> None:
        # Create a dictionary of tools for easy access by their names.
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        """
        Process tool calls from the last AI message and execute them.
        """
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No messages found in input.")

        outputs = []

        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}


# Easily modify this list of tools to add or remove tools from the single agent.
# We can also add new agents with their own tools, as long as we route them properly in the workflow.
# Look at the example below to see how a tool is defined.
# @tool
# def add(a: int, b: int) -> int:
#     """Use this tool to add two numbers."""
#     return a + b


@tool
def generate_prelearning_quiz():
    """Use this tool to generate a pre-learning quiz for the user."""
    # TODO:
        # Generate a pre-learning quiz depending on the current chapter of the textbook.
        # Can use hard coded pre learning questions but that's a terrible practice, since we ultimately want to be able to switch textbooks
        # LLM maybe?
        # First, display a popup
    return {"action": "display_popup", "content": "Pre-learning quiz content goes here."}


    
def get_tools():
    """
    Returns a list of tools for the chatbot.
    """    
    textbook_retriever = generate_retriever_tool()
    
    tools = [textbook_retriever, generate_prelearning_quiz] # add is_question tool here, along with other tools yet to be designed
    return tools

