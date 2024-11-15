import getpass
import os


def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


_set_env("OPENAI_API_KEY")


from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o", temperature=0)

from typing import Literal

from langchain_core.tools import tool


################################################################

### @ tool decorator ###

################################################################

@tool
def get_weather(city: Literal["nyc", "sf"]): #literal makes sure that our input is either nyc or sf.
    """Use this tool to get weather information."""
    print("[DEBUG] get_weather tool called")
    if city == "nyc":
        return "It's raining in NYC."
    elif city == "sf":
        return "It's sunny in SF."
    else:
        raise AssertionError("Unknown City")
    

@tool
def multiply(x: int, y: int) -> int:
    """Use this tool to multiply two numbers."""
    print("[DEBUG] multiply tool called")
    return x * y


from pydantic import BaseModel, Field

class CalculatorInput(BaseModel):
    a: int = Field(description="the first number")
    b: int = Field(description="the second number")

@tool("division-tool", args_schema=CalculatorInput)#, return_direct=True)
def divide(a: int, b: int) -> float:
    """Use this tool to divide two numbers."""
    print("[DEBUG] divide tool called")
    return a / b if b != 0 else "undefined"

################################################################

### StructuredTool ###

################################################################
# provides more connfigurability than the @tool decorator, without much more code

from langchain_core.tools import StructuredTool

def repeatedlyAdd(a: int, b: int) -> int:
    """multiply two numbers."""
    print("[DEBUG] StructuredTool tool called")
    return a * b


calculator = StructuredTool.from_function(
    func=repeatedlyAdd,
    name="Calculator",
    description="Multiply two numbers",
    args_schema=CalculatorInput,
    )


################################################################

### from Runnables ###

################################################################
# LangChain Runnables that accept string or dict inputs can be converted to tools using the as_tool() method.
# the method allows for the specification of names, descriptions, and any additional schema information for arguments.


from langchain_core.language_models import GenericFakeChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages(
    [("human", "Hello. Please respond in the style of {answer_style}.")]
)

# Placeholder LLM
llm = GenericFakeChatModel(messages=iter(["hello there, i'm an italian."]))

chain = prompt | llm | StrOutputParser()

as_tool = chain.as_tool(
    name="Style responder", description="Description of when to use tool."
)


response = as_tool.invoke({"answer_style": "pirate"})
print(response)

# confused still.




# note how list of tools consists of the function name
# tools = [get_weather, divide, calculator]
# prompt = (
#             "If you need to calculate something, don't. Let the tool do it."
#             "Respond in Mandarin. If you need to respond using a number, "
#             "write that number out in Mandarin. Additionally, before your answer, type 'Mao: '" 
#          )
# from langgraph.prebuilt import create_react_agent
# graph = create_react_agent(model, tools=tools, state_modifier=prompt)


# def print_stream(stream):
#     for s in stream:
#         message = s["messages"][-1]
#         if isinstance(message, tuple):
#             print(message)
#         else:
#             message.pretty_print()

# inputs = {"messages": [("user", "What is eighteen multiplied by forty-nine?")]}
# print_stream(graph.stream(inputs, stream_mode="values"))
