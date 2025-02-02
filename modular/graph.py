from langgraph.graph import StateGraph, START, END
from tools import BasicToolNode, get_tools
from state import State
from langchain_core.messages import SystemMessage
from typing import Annotated
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

systemPrompt = SystemMessage(
        "You are a helpful tutor whose goal is to help students understand the concepts of textbook. \
        If the user asks a question about anything outside of the textbook, be polite and remind them that you're an \
        instructor. Use no formatting in your replies. Keep your responses brief, yet informative. The overall \
        goal is to help the user learn from the textbook. You have access to two tools: the textbook retriever, \
        which will retrieve the appropriate information for you to answer their questions, as well as a pre learning quiz generator.\
        Use the pre learning quiz generator to generate a quiz for the user as the FIRST message."

        # TODO: 
            # Let the system prompt know what chapter the user is currently on.
            # something like: "The user is currently reading chapter {chapterNumber}" appended to the prompt.
    )

#[DEBUG]
# systemPrompt = SystemMessage(
#         "You are a helpful tutor whose goal is to help students understand the concepts of textbook. \
#         Use no formatting in your replies, and keep your responses brief, yet informative. The overall \
#         goal is to help the user learn from the textbook. You have access to two tools: the textbook retriever, \
#         which will retrieve the appropriate information for you to answer their questions, as well as a quiz generator.\
#         Use the quiz generator to generate a quiz for the user as the FIRST message."
    
#     )



def build_graph(llm):
    """
    Builds and compiles the chatbot's state graph.
    """
    tools = get_tools()
    memory = MemorySaver()
    
    graph = create_react_agent(llm, tools,  checkpointer=memory, state_modifier=systemPrompt)
    return graph


def route_tools(state: State):
    """
    Determines the next node in the graph based on the presence of tool calls.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError("No messages found in the input state.")

    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"



### DEPRECATED, pending deletion ###

#
    #llm_with_tool = llm.bind_tools(tools)

    # Add chatbot node
    # def supervisor(state: State):
    #     return {"messages": [llm_with_tool.invoke([systemPrompt] + state["messages"])]}
    
    
    # This agent is the "supervisor" and has access to the tools
    # Previously, we defined nodes and edges, but using one such agent with capacity for memory is simpler 
    # both in terms of runtime, and in terms of code complexity.
    

##### NODES #####
    
    # tool_node = BasicToolNode(tools=tools)
    # graph_builder.add_node("tools", tool_node)
    # graph_builder.add_node("supervisor", supervisor)


    # graph_builder.add_edge(START, "supervisor")
    # graph_builder.add_edge("tools", "supervisor")


    # #### EDGES ####
    # # Add conditional edges
    # graph_builder.add_conditional_edges(
    #     "supervisor",  # Node to make the decision
    #     route_tools,  # Routing function
    #     {"tools": "tools", "__end__": "__end__"},
    # )

    #return graph_builder.compile()