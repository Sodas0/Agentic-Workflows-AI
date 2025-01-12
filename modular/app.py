from flask import Flask, render_template, request, redirect, url_for, session
from langchain_openai import ChatOpenAI
from graph import build_graph
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session handling

# Initialize LLM and graph
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
graph = build_graph(llm)

@app.route("/", methods=["GET", "POST"])
def home():
    return redirect(url_for("chat"))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    # Initialize session variables if not present
    if "chat_history" not in session:
        session["chat_history"] = []

    if request.method == "POST":
        user_question = request.form.get("question", "").strip()
        if user_question:  # If the question is not empty
            # Append the user's message to chat history
            session["chat_history"].append({"sender": "user", "message": user_question})

            # Generate a bot response
            config = {"configurable": {"thread_id": "🐭"}}
            bot_response = ""
            for event in graph.stream({"messages": [("user", user_question)]}, config):
                for value in event.values():
                    bot_response = value["messages"][-1].content

            # Append the bot's message to chat history
            session["chat_history"].append({"sender": "bot", "message": bot_response})

            # Save session to persist changes
            session.modified = True

    # Pass the full chat history to the template
    return render_template("chat.html", chat_history=session["chat_history"])
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("chat"))

if __name__ == "__main__":
    app.run(debug=True)
