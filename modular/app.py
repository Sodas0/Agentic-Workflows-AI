from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from langchain_openai import ChatOpenAI
from graph import build_graph
from dotenv import load_dotenv
import os
import io
from PyPDF2 import PdfReader, PdfWriter

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session handling

# Initialize LLM and graph
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
graph = build_graph(llm)

# Textbook and page ranges
PDF_PATH = "../data/wholeTextbookPsych.pdf"
PAGE_RANGES = [
        (19,46),(47,82),(83,120),(121,156),
        (157,192),(193,224),(225,258),(259,290),
        (291,332),(333,370),(371,410),(411,458),
        (459,496),(497,548),(549,610),(611,644)
    ] # Should be built by the textbook's table of contents





@app.route("/", methods=["GET"])
def home():
    # Dynamically create a list of chapters based on PAGE_RANGES
    chapters = [{"number": i + 1, "start_page": start, "end_page": end} for i, (start, end) in enumerate(PAGE_RANGES)]
    return render_template("home.html", chapters=chapters)



# @app.route("/", methods=["GET", "POST"])
# def home():
#     return redirect(url_for("chat"))

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

# Serve chapter to user

@app.route("/chapter_pdf/<int:chapter_number>", methods=["GET"])
def serve_chapter_pdf(chapter_number):
    chapter_number -= 1
    try:
        chapter_page_range = PAGE_RANGES[chapter_number]
    except:
        return f"Chapter {chapter_number} not found.", 404
    
    start_page, end_page = chapter_page_range
    output_pdf = io.BytesIO()
    reader = PdfReader(PDF_PATH)
    writer = PdfWriter()

    for i in range(start_page - 1, end_page):
        writer.add_page(reader.pages[i])
    
    writer.write(output_pdf)
    output_pdf.seek(0)

    return send_file(output_pdf, as_attachment=False, mimetype="application/pdf")

# Serve the HTML page with the iframe
@app.route("/chapter/<int:chapter_number>", methods=["GET", "POST"])
def serve_chapter(chapter_number):
    if "chat_history" not in session:
        session["chat_history"] = []

    if request.method == "POST":
        user_question = request.form.get("question", "").strip()
        if user_question:
            session["chat_history"].append({"sender": "user", "message": user_question})
            # TODO:
                # configure thread_id to individual users (or create a new thread ID per reload for simplicity)
                
            config = {"configurable": {"thread_id": "🍅"}} #previously: 🐭
            bot_response = ""
            for event in graph.stream({"messages": [("user", user_question)]}, config):
                for value in event.values():
                    bot_response = value["messages"][-1].content
            session["chat_history"].append({"sender": "bot", "message": bot_response})
            session.modified = True

        # Render only the chat messages as a response for AJAX
        return render_template("chat_messages.html", chat_history=session["chat_history"])

    # For GET requests, serve the full page
    return render_template("chapter_viewer.html", chapter_number=chapter_number, chat_history=session["chat_history"])


@app.route("/logout")
def logout():
    session.clear()
    chapters = [{"number": i + 1, "start_page": start, "end_page": end} for i, (start, end) in enumerate(PAGE_RANGES)]
    return render_template("home.html", chapters=chapters)

if __name__ == "__main__":
    app.run(debug=True)
