from langchain_openai import ChatOpenAI
from graph import build_graph
#from generateGraphPNG import generate_graph_png
from serve_pdf import interactive_pdf_reader
import fitz  # PyMuPDF
import re



# ignore this, this is for debug
#filename = "concept.png"

config = {"configurable": {"thread_id": "🐭"}}

def main():
    """
    Main function to run the chatbot.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
    graph = build_graph(llm)
    
    #[debug]
    #generate_graph_png(graph, filename)

    print("BeaverBot123 is running. Type 'exit', 'quit', or 'q' to end the session.")
    while True:
        
        # Serve content from textbook here. Let's use chapter 6 for now
        # TODO:
            # 1. Serve content from the textbook autonomously
                # a. pause between sections to offer opportunities for questions (can accomplish using a concept known as generators)
                # b. if there are questions, pause the content loop and answer the questions using retriever tool
                # c. need to account for follow-up questions (don't resume the content loop until all questions are answered)
            
    

        
        # prompt for questions 
        # This section answers the questions that the user has about the content.
        user_input = input("User: ")
        
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Later tater")
            break    
        
        # Process user input and output responses
        # TODO:
            # figure out how to only print the last BeaverBot123 response: currently it prints all retrieved chunks
        for event in graph.stream({"messages": [("user", user_input)]}, config):
            for value in event.values():
                print("Assistant: ", value["messages"][-1].content)


if __name__ == "__main__":
    main()
