from langgraph.graph import StateGraph, START, END
from tools import BasicToolNode, get_tools
from state import State
from langchain_core.messages import SystemMessage
from typing import Annotated

systemPrompt = SystemMessage("You are a helpful psychology tutor whose goal is to help students understand the concepts of psychology.")



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


from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
def build_graph(llm):
    """
    Builds and compiles the chatbot's state graph.
    """
    graph_builder = StateGraph(State)

    # Bind tools to the LLM
    tools = get_tools()
    llm_with_tool = llm.bind_tools(tools)

    # Add chatbot node
    def supervisor(state: State):
        return {"messages": [llm_with_tool.invoke([systemPrompt] + state["messages"])]}
    
    memory = MemorySaver()
    
    graph = create_react_agent(llm, tools, checkpointer=memory)
    
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
    return graph
