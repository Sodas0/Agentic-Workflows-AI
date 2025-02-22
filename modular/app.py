from flask import Flask, render_template, request, session, send_file, jsonify, Response, stream_with_context, redirect
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfWriter
import random
import os
import io
import time
import json
import re


MAX_SESSION_SIZE = 1200

answers = []  # Store user quiz answers in memory (global list, probably a bad practice but uhhh)

# ============= Load environment variables =============
load_dotenv(override=True)

# Get API keys as a list
API_KEYS = os.getenv("OPENAI_API_KEYS").split(",")

def get_random_api_key():
    """Selects a random API key from the list."""
    return random.choice(API_KEYS)

selected_api_key = get_random_api_key()
print("Selected API Key:", selected_api_key)
os.environ["OPENAI_API_KEY"] = selected_api_key

from tools import evaluate_quiz_answers
from graph import build_graph
from bookmark import initialize_bookmarks, get_page_ranges, get_num_buttons, save_section_pdf

app = Flask(__name__)
app.secret_key = os.urandom(24)

thread_id = 'participant_'

# ============= Initialize LLM & Graph =============
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True, openai_api_key=selected_api_key)
graph = build_graph(llm)

# ============= PDF & Bookmark Setup =============
PDF_PATH = "../data/wholeTextbookPsych.pdf"
PAGE_RANGE_PATH = "../data/page_ranges.json"
SECTION_PATH = "../data/sections"

initialize_bookmarks(PDF_PATH, PAGE_RANGE_PATH)
PAGE_RANGES = get_page_ranges(PAGE_RANGE_PATH)

# ----------------------------------------------------------------------
# NEW HOME ROUTE: Enter 4-Digit Code & Store in Session
 # TODO:
        # CREATE A DATABASE TO STORE CHAT_HISTORY LOGS FOR EACH UNIQUE ID.
# ----------------------------------------------------------------------


def trim_chat_history():
    """Trims the chat history to fit within the session size limit."""
    while len(str(session.get("chat_history", ""))) > MAX_SESSION_SIZE:
        session["chat_history"].pop(0)  # Remove the oldest message

@app.route("/", methods=["GET", "POST"])
def home():
    """
    Home page. Used to correlate Qualtrics ID to chatlogs in Langsmith and our own logs.
    Now this page allows the user to enter a four-digit code which is stored in the session
    (as 'user_id'). Upon valid entry, the user is redirected to /chapter/6/1.
    """
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if not (code.isdigit() and len(code) == 4):
            error = "Please enter a valid 4-digit code."
            return render_template("code_entry.html", error=error)
        session["user_id"] = code
        
        print("="*40)
        print(f'Detected ID: {session["user_id"]}')
        return redirect("/chapter/6")
    return render_template("home.html", error=None)

@app.route("/chapter_pdf/<int:chapter_number>", methods=["GET"])
def serve_chapter_pdf(chapter_number):
    """
    Serve the entire PDF for a given chapter (by slicing the big PDF).
    """
    idx = chapter_number - 1
    if idx < 0 or idx >= len(PAGE_RANGES):
        return f"Chapter {chapter_number} not found.", 404

    start_page, end_page = PAGE_RANGES[idx]
    output_pdf = io.BytesIO()
    reader = PdfReader(PDF_PATH)
    writer = PdfWriter()
    for i in range(start_page - 1, end_page):
        writer.add_page(reader.pages[i])
    writer.write(output_pdf)
    output_pdf.seek(0)

    return send_file(output_pdf, as_attachment=False, mimetype="application/pdf")

@app.route("/chapter/<int:chapter_number>", methods=["GET", "POST"])
def serve_chapter(chapter_number):
    """
    Renders chapter_viewer.html and handles chat logic.
    """

    idx = chapter_number - 1

    if "chat_history" not in session:
        pre_message = (
            f"Introduce yourself and how you hope to help the user. We will be going through chapter {chapter_number}. "
            f"Summarize briefly the main idea of chapter {chapter_number}.1. Spark interest in the user and prepare them for the first MCQ you will generate."
            f"Explain that the start quiz button will appear in the top right corner"
        )
        session["chat_history"] = []
        bot_response = ""

        # Stream the LLM's answer
        for event in graph.stream({"messages": [("user", pre_message)]}, {"configurable":{"thread_id":thread_id}}):
            for value in event.values():
                bot_response = value["messages"][-1].content

        # Store in session
        session["chat_history"].append({"sender": "bot", "message": bot_response})
        trim_chat_history()
    # print(session["chat_history"])
    quiz = {}
    if request.method == "POST":
        user_question = request.form.get("question", "").strip()
        if user_question:
            session["chat_history"].append({"sender": "user", "message": user_question})
            final_response = ""

            # Process LLM response before streaming
            for event in graph.stream(
                {"messages": [("user", user_question)]},
                {"configurable": {"thread_id": thread_id}}
            ):
                for value in event.values():
                    final_response = value["messages"][-1].content

            # Extract JSON for the quiz
            json_match = re.search(r'```json\s*({.*?})\s*```', final_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)  # Extract matched JSON part
                try:
                    quiz = json.loads(json_str)  # Parse JSON safely
                    print(quiz)
                    session["current_quiz"] = json.dumps(quiz)
                    # Remove extracted quiz from final response
                    final_response = re.sub(r'```json\s*{.*?}\s*```', '', final_response, flags=re.DOTALL).strip()
                except json.JSONDecodeError as e:
                    print(f"Failed to parse JSON: {e}")
                    quiz = {}

            session["chat_history"].append({"sender": "bot", "message": final_response})
            session.modified = True

            def generate():
                # Stream out the cleaned final_response char by char
                for char in final_response:
                    yield char
                    time.sleep(0.01)

            return Response(stream_with_context(generate()), mimetype="text/plain")

        # If no user question, just re-render the chat
        return render_template("chat_messages.html", chat_history=session["chat_history"])

    # If GET request, show chapter_viewer.html
    return render_template(
        "chapter_viewer.html",
        chapter_number=chapter_number,
        chat_history=session["chat_history"],
        quiz=json.dumps(quiz)  # Pass extracted quiz
    )

@app.route("/get_current_quiz", methods=["GET"])
def get_current_quiz():
    quiz_data = session.get("current_quiz", "{}")  # Default to '{}' to prevent errors
    try:
        return jsonify(json.loads(quiz_data))  # Parse string back into JSON object
    except json.JSONDecodeError as e:
        print(f"Error decoding session quiz JSON: {e}")
        return jsonify({})  # Return empty JSON if there's an error
        
@app.route("/home")
def go_home():
    # Clears the session and returns to home
    session.clear()
    chapters = [
        {"number": i + 1, "start_page": start, "end_page": end}
        for i, (start, end) in enumerate(PAGE_RANGES)
    ]
    return render_template("home.html", chapters=chapters)

@app.route("/submit-answer", methods=["POST"])
def submit_answers():
    """
    Receives quiz answers, extends the global 'answers' list,
    then calls our 'evaluate_quiz_answers' tool using the CORRECT sub-chapter quiz.
    """
    request_data = request.json
    submitted_answers = request_data["answers"]
    chapter_number = request_data["chapter_number"]
    print("quiz ----------------")
    print(submitted_answers)
    print("quiz ----------------")

    prompt = (
        "Evaluate the following quiz answers, according to the given instructions."
        "After evaluation is done, prepare the user to move onto the next sub-section, only if another sub-section exists."
        "If no other sub-section exists, congratuate the user on completing the chapter and tell them that you remain open to discussion."
        f"{json.dumps(submitted_answers)}"
    )
    session["chat_history"] = session.get("chat_history")
    bot_response = ""
    session["chat_history"].append({"sender": "user", "message": prompt})
    # Stream the LLM's answer
    for event in graph.stream({"messages": [("user", prompt)]}, {"configurable":{"thread_id":thread_id}}):
        for value in event.values():
            bot_response = value["messages"][-1].content
    print(bot_response)
    # Store in session
    session["chat_history"].append({"sender": "bot", "message": bot_response})
    def generate():
        # Stream out the cleaned final_response char by char
        for char in bot_response:
            yield char
            time.sleep(0.01)
    
    # Remove "current_quiz" from the session
    session.pop("current_quiz", None)
    return Response(stream_with_context(generate()), mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)