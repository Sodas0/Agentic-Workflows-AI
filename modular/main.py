from langchain_openai import ChatOpenAI
from graph import build_graph
from generateGraphPNG import generate_graph_png

filename = "concept.png"
config = {"configurable": {"thread_id": "🐭"}}

def main():
    """
    Main function to run the chatbot.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
    graph = build_graph(llm)
    generate_graph_png(graph, filename)

    print("BeaverBot123 is running. Type 'exit', 'quit', or 'q' to end the session.")
    while True:
        
        # Serve content from textbook here
        # # any questions?
        
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Later tater")
            break
        
        # Can do another simple input processing step to immediately decide if user_input is a question.
            # if yes, answer
            # if no, do mini quiz
        
        
        # Process user input and output responses
        for event in graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant: ", value["messages"][-1].content)


if __name__ == "__main__":
    main()
