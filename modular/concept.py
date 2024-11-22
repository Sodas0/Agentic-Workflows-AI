from langgraph.graph import StateGraph, START, END
from tools import BasicToolNode, get_tools
from state import State
from generateGraphPNG import generate_graph_png


def content_server(state: State):
    return {"messages": ["Content server invoked"]}

def question_answerer(state: State):
    return {"messages": ["Question answerer invoked"]}

def quiz_generator(state: State):
    return {"messages": ["Quiz generator invoked"]}

def answer_evaluator(state: State):
    return {"messages": ["Answer evaluator invoked"]}

def content_summarizer(state: State):
    return {"messages": ["Content summarizer invoked"]}

def textbook_content(state: State):
    return {"messages": ["Textbook content accessed"]}

def question_bank(state: State):
    return {"messages": ["Question bank accessed"]}

def context_node(state: State):
    return {"messages": ["Context node invoked"]}

def tools_node(state: State):
    return {"messages": ["Tools invoked"]}

# Define the routing logic for tools
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
        return "tools"  # Ensure "tools" node exists in the graph
    return "__end__"

# Build the graph based on the handwritten diagram
def build_graph(llm):
    graph_builder = StateGraph(State)

    # Bind tools to the LLM
    tools = get_tools()
    llm_with_tool = llm.bind_tools(tools)

    # Supervisor Node (Chatbot)
    def supervisor(state: State):
        return {"messages": [llm_with_tool.invoke(state["messages"])]}

    # Add nodes
    graph_builder.add_node("supervisor", supervisor)
    graph_builder.add_node("content_server", content_server)
    graph_builder.add_node("question_answerer", question_answerer)
    graph_builder.add_node("quiz_generator", quiz_generator)
    graph_builder.add_node("answer_evaluator", answer_evaluator)
    graph_builder.add_node("content_summarizer", content_summarizer)
    graph_builder.add_node("textbook_content", textbook_content)
    graph_builder.add_node("question_bank", question_bank)
    graph_builder.add_node("context_node", context_node)
    graph_builder.add_node("tools", tools_node)  # Add the tools node

    # Add edges (conditional and unconditional)
    graph_builder.add_edge(START, "supervisor")
    graph_builder.add_edge("supervisor", "content_server")
    graph_builder.add_edge("supervisor", "question_answerer")
    graph_builder.add_edge("supervisor", "quiz_generator")
    graph_builder.add_edge("supervisor", "answer_evaluator")
    graph_builder.add_edge("supervisor", "content_summarizer")
    
    # Internal edges
    graph_builder.add_edge("content_server", "textbook_content")
    graph_builder.add_edge("quiz_generator", "question_bank")
    graph_builder.add_edge("content_summarizer", "context_node")

    # Conditional edge for routing logic
    graph_builder.add_conditional_edges(
        "supervisor",
        route_tools,
        {"tools": "tools", "__end__": "__end__"},
    )

    generate_graph_png(graph_builder.compile())

    return graph_builder.compile()

from langchain_openai import ChatOpenAI

def main():
    llm = ChatOpenAI(temperature=0, model="gpt-4", streaming=True)
    graph = build_graph(llm, filename="modular/concept.png")

if __name__ == "__main__":
    main()
