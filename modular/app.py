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

# 1) Import quiz tool:
from tools import evaluate_quiz_answers

# 2) Import from data.py
from data import (
    ch6_pre_quiz,
    ch6_1_reinforcement,
    ch6_2_reinforcement,
    ch6_3_reinforcement,
    ch6_4_reinforcement
)

answers = []  # Store user quiz answers in memory (global list)

# ============= Load environment variables =============
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

emoji_pool = [
    "🍅","😂","😎","😍","🤓","😜","🤩","🥳","😇","🤖","👻","👽","😩","🙈",
    "🐭","🐶","🦊","🐼","🐸","🐵","🦫"
]
thread_id = ''.join(random.choices(emoji_pool, k=7))
print("THREAD ID =>", thread_id)

# ============= Initialize LLM & Graph =============
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
graph = build_graph(llm)

# ============= PDF & Bookmark Setup =============
PDF_PATH = "../data/wholeTextbookPsych.pdf"
PAGE_RANGE_PATH = "../data/page_ranges.json"
SECTION_PATH = "../data/sections"

initialize_bookmarks(PDF_PATH, PAGE_RANGE_PATH)
PAGE_RANGES = get_page_ranges(PAGE_RANGE_PATH)
sub_chapter = get_num_buttons(PAGE_RANGE_PATH)
if not os.path.exists(SECTION_PATH):
    save_section_pdf(PDF_PATH, PAGE_RANGE_PATH, SECTION_PATH)

@app.route("/", methods=["GET"])
def home():
    """
    Home page. Lists all chapters (based on PAGE_RANGES).
    """
    chapters = [
        {"number": i + 1, "start_page": start, "end_page": end}
        for i, (start, end) in enumerate(PAGE_RANGES)
    ]
    return render_template("home.html", chapters=chapters)

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

@app.route("/chapter_pdf/<int:chapter_number>/<int:section_number>", methods=["GET"])
def serve_section_pdf_route(chapter_number, section_number):
    """
    Serve a sub-chapter's PDF from the pre-saved PDFs in data/sections/.
    """
    pdf_path = f"../data/sections/chapter {chapter_number}/{section_number}.pdf"
    if not os.path.exists(pdf_path):
        return f"Section PDF not found at: {pdf_path}", 404
    return send_file(pdf_path, as_attachment=False, mimetype="application/pdf")

@app.route("/chapter/<int:chapter_number>", methods=["GET", "POST"])
def serve_chapter(chapter_number):
    """
    Renders chapter_viewer.html and handles chat logic.
    """
    idx = chapter_number - 1
    if idx < 0 or idx >= len(sub_chapter):
        return f"Chapter {chapter_number} not found.", 404

    button_count = sub_chapter[idx]-1

    # Prepare dictionary for Chapter 6 quizzes
    ch6_quizzes = {
        0: ch6_pre_quiz,
        1: ch6_1_reinforcement,
        2: ch6_2_reinforcement,
        3: ch6_3_reinforcement,
        4: ch6_4_reinforcement
    }

    # If chat_history not in session, make a welcome message
    if "chat_history" not in session:
        pre_message = (
            f"Summarize briefly the main idea of chapter {chapter_number}. "
            f"Remind the user that they must take the pre-learning quiz using the quiz button "
            f"on the right to move on to the next subchapter."
        )
        session["chat_history"] = []
        bot_response = ""

        # Stream the LLM's answer
        for event in graph.stream({"messages": [("user", pre_message)]}, {"configurable":{"thread_id":thread_id}}):
            for value in event.values():
                bot_response = value["messages"][-1].content

        # Store in session
        session["chat_history"].append({"sender": "bot", "message": bot_response})

    # If the user sends a chat question (POST)
    if request.method == "POST":
        user_question = request.form.get("question", "").strip()
        if user_question:
            session["chat_history"].append({"sender": "user", "message": user_question})

            def generate():
                final_response = ""
                for event in graph.stream(
                    {"messages": [("user", user_question)]},
                    {"configurable":{"thread_id":thread_id}}
                ):
                    for value in event.values():
                        final_response = value["messages"][-1].content

                session["chat_history"].append({"sender": "bot", "message": final_response})
                session.modified = True

                # Stream out the final_response char by char
                for char in final_response:
                    yield char
                    time.sleep(0.01)

            return Response(stream_with_context(generate()), mimetype="text/plain")

        # If no user question, just re-render the chat
        return render_template("chat_messages.html", chat_history=session["chat_history"])

    # If GET request, show chapter_viewer.html
    if chapter_number == 6:
        # Pass the dictionary of quizzes
        return render_template(
            "chapter_viewer.html",
            chapter_number=chapter_number,
            button_count=button_count,
            chat_history=session["chat_history"],
            ch6_quizzes=ch6_quizzes
        )
    else:
        # No quizzes for other chapters
        return render_template(
            "chapter_viewer.html",
            chapter_number=chapter_number,
            button_count=button_count,
            chat_history=session["chat_history"],
            ch6_quizzes={}
        )

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
    print("---------answers-----------")
    print(request_data)
    print(submitted_answers)
    print("---------answers-end-----------")
    subchapter_idx = request_data.get("subchapter")  # e.g. 0, 1, 2, 3, 4

    # Rebuild the dictionary (same as above)
    ch6_quizzes = {
        0: ch6_pre_quiz,
        1: ch6_1_reinforcement,
        2: ch6_2_reinforcement,
        3: ch6_3_reinforcement,
        4: ch6_4_reinforcement
    }

    if isinstance(submitted_answers, list) and (subchapter_idx is not None):
        # 1) Append user's answers to global list
        answers.extend(submitted_answers)
        print("Stored answers so far:", answers)

        # 2) Grab the correct quiz from dictionary
        the_quiz = ch6_quizzes.get(subchapter_idx, [])
        print(f"Evaluating quiz for sub-chapter index {subchapter_idx}: {the_quiz}")

        # 3) Evaluate with the tool
        evaluation_response, score, total_questions, feedback, correct_answers = evaluate_quiz_answers(the_quiz, submitted_answers)
        print("Tool response from LLM:", evaluation_response)

        # 4) Return JSON back to the frontend
        return jsonify({
            "message": "Quiz submitted successfully!",
            "answers": correct_answers,
            "score": score,
            "total_questions": total_questions,
            "feedback": feedback
        })

    return jsonify({"error": "Invalid submission"}), 400

if __name__ == "__main__":
    app.run(debug=True)
