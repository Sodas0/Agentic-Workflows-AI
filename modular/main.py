from langchain_openai import ChatOpenAI
from graph import build_graph
from generateGraphPNG import generate_graph_png

def main():
    """
    Main function to run the chatbot.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
    graph = build_graph(llm)
    generate_graph_png(graph)

    print("BeaverBot123 is running. Type 'exit', 'quit', or 'q' to end the session.")
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Later tater")
            break

        # Process user input and output responses
        for event in graph.stream({"messages": [("user", user_input)]}):
            for value in event.values():
                print("Assistant: ", value["messages"][-1].content)


if __name__ == "__main__":
    main()
