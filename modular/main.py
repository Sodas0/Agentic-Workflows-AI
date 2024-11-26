from langchain_openai import ChatOpenAI
# from graph import build_graph
# from generateGraphPNG import generate_graph_png
import os
from dotenv import load_dotenv


def main():
    """
    Main function to run the chatbot.
    """
    # Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not load_dotenv(env_path):
        print(f"Failed to load .env file from {env_path}")
    else:
        print(f".env file loaded successfully from {env_path}")

    # Retrieve the API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set in environment variables.")

    os.environ["OPENAI_API_KEY"] = api_key  # Ensure it's in os.environ for libraries that require it

    from graph import build_graph
    from generateGraphPNG import generate_graph_png

    llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
    graph = build_graph(llm)
    # generate_graph_png(graph)

    # Start the chatbot
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