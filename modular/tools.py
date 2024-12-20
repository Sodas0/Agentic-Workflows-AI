import json
from langchain_core.messages import ToolMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import tool
from retrievertool import textbook_retriever_tool

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
# I will create a diagram of a workflow to show how multi-agents can interact. (probably over the weekend)

@tool
def add(a: int, b: int) -> int:
    """Use this tool to add two numbers."""
    return a + b



from langchain_openai import ChatOpenAI

@tool
def is_question(message: str) -> str:
    """Determines whether a message is a question."""
    tempLLM = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    messages = [
    (
        "system",
        "Your task is to determine whether the given sentence is a question or not. Return 'yes' if it is, and 'no' if it isn't.",
    ),
    ("human", {message}),
]
    return tempLLM.invoke(messages)


textbook_retriever = textbook_retriever_tool


    
def get_tools():
    """
    Returns a list of tools for the chatbot.
    """

    tools = [textbook_retriever, add, is_question]
    return tools

