from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class State(TypedDict):
    """
    State definition for the chatbot, including messages.
    Messages are appended instead of being overwritten.
    """
    messages: Annotated[list, add_messages]
