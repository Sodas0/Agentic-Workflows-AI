from flask import Flask, render_template, request, session, send_file, jsonify, Response, stream_with_context
from langchain_openai import ChatOpenAI
from graph import build_graph
from dotenv import load_dotenv
from bookmark import initialize_bookmarks, get_page_ranges, get_num_buttons, save_section_pdf
from PyPDF2 import PdfReader, PdfWriter
import random
import os
import io
import time

# If you have quiz data in a separate file, import it:
from data import data, quiz
# Otherwise, define quiz inline:
# quiz = [
#     {
#         "question": "What is 2+2?",
#         "answers": ["3", "4", "22", "5"],
#         "correct": 1
#     },
#     {
#         "question": "Which letter comes after B?",
#         "answers": ["A", "C", "D", "Z"],
#         "correct": 1
#     }
# ]
answers = []  # Will store user quiz answers

# ============= Load environment variables =============
load_dotenv()

# ============= Initialize Flask App =============
app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============= Print some debug info =============
emoji_pool = [
    "🍅","😂","😎","😍","🤓","😜","🤩","🥳","😇","🤖","👻","👽","😩","🙈",
    "🐭","🐶","🦊","🐼","🐸","🐵","🦫"
]
thread_id = ''.join(random.choices(emoji_pool, k=7))
print("="*19 + " SECRET KEY " + "="*19)
print(app.secret_key)
print("="*19 + " THREAD ID " + "="*19)
print(thread_id)

# ============= Initialize LLM and Graph =============
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
graph = build_graph(llm)

# ============= PDF & Bookmark Setup =============
PDF_PATH = "../data/wholeTextbookPsych.pdf"
PAGE_RANGE_PATH = "../data/page_ranges.json"
SECTION_PATH = "../data/sections"

# Build bookmarks
initialize_bookmarks(PDF_PATH, PAGE_RANGE_PATH)
PAGE_RANGES = get_page_ranges(PAGE_RANGE_PATH)
sub_chapter = get_num_buttons(PAGE_RANGE_PATH)
if not os.path.exists(SECTION_PATH):
    save_section_pdf(PDF_PATH, PAGE_RANGE_PATH, SECTION_PATH)

# ============= ROUTES =============

@app.route("/", methods=["GET"])
def home():
    """
    Main home page. Lists chapters (based on PAGE_RANGES).
    """
    chapters = [
        {"number": i + 1, "start_page": start, "end_page": end}
        for i, (start, end) in enumerate(PAGE_RANGES)
    ]
    return render_template("home.html", chapters=chapters)


@app.route("/chapter_pdf/<int:chapter_number>", methods=["GET"])
def serve_chapter_pdf(chapter_number):
    """
    Serve the entire PDF for a given chapter (by slicing the main PDF).
    """
    # Adjust for zero-based Python list
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


@app.route("/chapter_pdf/<int:chapter_number>/<int:section_number>", methods=["GET"])
def serve_section_pdf_route(chapter_number, section_number):
    """
    Serve the sub-section PDF (like chapter 2.1, 2.2) from pre-saved files.
    """
    pdf_path = f"../data/sections/chapter {chapter_number}/{section_number}.pdf"
    if not os.path.exists(pdf_path):
        return f"Section PDF not found at: {pdf_path}", 404
    
    return send_file(pdf_path, as_attachment=False, mimetype="application/pdf")


@app.route("/chapter/<int:chapter_number>", methods=["GET", "POST"])
def serve_chapter(chapter_number):
    """
    Renders the chapter viewer page:
      - PDF toggling
      - Chat
      - Quiz button & modal
    """
    idx = chapter_number - 1
    if idx < 0 or idx >= len(sub_chapter):
        return f"Chapter {chapter_number} not found.", 404
    
    # This is how many sub-sections the chapter has
    button_count = sub_chapter[idx]

    # Initialize chat if needed
    if "chat_history" not in session:
        # Summarize briefly the main idea of the chapter for the first message
        pre_message = f"Summarize briefly the main idea of chapter {chapter_number}."
        session["chat_history"] = []
        bot_response = ""

        # Stream from LLM
        for event in graph.stream({"messages": [("user", pre_message)]}, {"configurable":{"thread_id":thread_id}}):
            for value in event.values():
                bot_response = value["messages"][-1].content
        
        session["chat_history"].append({"sender": "bot", "message": bot_response})

    # If user is sending a question (POST)
    if request.method == "POST":
        user_question = request.form.get("question", "").strip()
        if user_question:
            session["chat_history"].append({"sender": "user", "message": user_question})
            
            def generate():
                final_response = ""
                # Stream from the LLM
                for event in graph.stream({"messages": [("user", user_question)]}, {"configurable":{"thread_id":thread_id}}):
                    for value in event.values():
                        final_response = value["messages"][-1].content

                # Append final response to chat history
                session["chat_history"].append({"sender": "bot", "message": final_response})
                session.modified = True

                # Yield the final response char-by-char for streaming
                for char in final_response:
                    yield char
                    time.sleep(0.01)
            
            return Response(stream_with_context(generate()), mimetype="text/plain")
        
        # If no question, just re-render
        return render_template("chat_messages.html", chat_history=session["chat_history"])

    # For GET requests, render the full page
    return render_template(
        "chapter_viewer.html",
        chapter_number=chapter_number,
        button_count=button_count,
        chat_history=session["chat_history"],
        quiz=quiz   # pass quiz data so we can use it in the template
    )


@app.route("/home")
def go_home():
    """
    Clears session and goes back to home.
    """
    session.clear()
    chapters = [
        {"number": i + 1, "start_page": start, "end_page": end}
        for i, (start, end) in enumerate(PAGE_RANGES)
    ]
    return render_template("home.html", chapters=chapters)


@app.route("/submit-answer", methods=["POST"])
def submit_answers():
    """
    Receives quiz answers, extends the global 'answers' list.
    """
    request_data = request.json
    submitted_answers = request_data.get("answers")

    if isinstance(submitted_answers, list) and len(submitted_answers) == len(quiz):
        answers.extend(submitted_answers)
        print("All answers so far:", answers)
        return jsonify({"message": "Quiz submitted successfully!", "answers": answers})

    return jsonify({"error": "Invalid submission"}), 400


if __name__ == "__main__":
    app.run(debug=True)
