from langgraph.graph import StateGraph, START, END
from tools import BasicToolNode, get_tools
from state import State


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


def build_graph(llm):
    """
    Builds and compiles the chatbot's state graph.
    """
    graph_builder = StateGraph(State)

    # Bind tools to the LLM
    tools = get_tools()
    llm_with_tool = llm.bind_tools(tools)

    # Add chatbot node
    def chatbot(state: State):
        return {"messages": [llm_with_tool.invoke(state["messages"])]}

    # Add nodes and edges to the graph
    tool_node = BasicToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("chatbot", chatbot)

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("tools", "chatbot")

    # Add conditional edges
    graph_builder.add_conditional_edges(
        "chatbot",  # Node to make the decision
        route_tools,  # Routing function
        {"tools": "tools", "__end__": "__end__"},
    )

    return graph_builder.compile()
