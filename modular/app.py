from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify, Response, stream_with_context
from langchain_openai import ChatOpenAI
from graph import build_graph
from dotenv import load_dotenv
import os
import io
import time
from PyPDF2 import PdfReader, PdfWriter

def get_config():
    configuration = {"configurable": {"thread_id": "🍅"}}
    return configuration

config = get_config()

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "my_secret_key" #os.urandom(24)  # Required for session handling
# Initialize LLM and graph
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
graph = build_graph(llm)

from bookmark import initialize_bookmarks, get_page_ranges, get_num_buttons, save_section_pdf

# Textbook and page ranges
PDF_PATH = "../data/wholeTextbookPsych.pdf"
PAGE_RANGE_PATH = "../data/page_ranges.json"
SECTION_PATH = "../data/sections"
# Build bookmarks
initialize_bookmarks(PDF_PATH, PAGE_RANGE_PATH)
PAGE_RANGES = get_page_ranges(PAGE_RANGE_PATH)
sub_chapter = get_num_buttons(PAGE_RANGE_PATH)
print(f"num_buttons = {sub_chapter}")
if not os.path.exists(SECTION_PATH):
        save_section_pdf(PDF_PATH, PAGE_RANGE_PATH, SECTION_PATH)

@app.route("/", methods=["GET"])
def home():
    # Dynamically create a list of chapters based on PAGE_RANGES
    chapters = [{"number": i + 1, "start_page": start, "end_page": end} for i, (start, end) in enumerate(PAGE_RANGES)]
    return render_template("home.html", chapters=chapters)

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

# Serve the section to user
@app.route("/chapter_pdf/<int:chapter_number>/<int:section_number>", methods=["GET"])
def serve_section_pdf(chapter_number, section_number):
    output_pdf = f"../data/sections/chapter {chapter_number}/{section_number}.pdf"

    return send_file(output_pdf, as_attachment=False, mimetype="application/pdf")

# Serve the HTML page with the iframe
@app.route("/chapter/<int:chapter_number>", methods=["GET", "POST"])
def serve_chapter(chapter_number):
    button_count = sub_chapter[chapter_number- 1] -1
    print(button_count)
    # Initialize chat history if it doesn't exist
    if "chat_history" not in session:
        pre_message  = f"Summarize briefly the main idea of chapter {chapter_number}." 
        session["chat_history"] = []
        bot_response = ""
        for event in graph.stream({"messages": [("user", pre_message)]}, config):
            for value in event.values():
                bot_response = value["messages"][-1].content
        session["chat_history"].append({"sender": "bot", "message": bot_response})
    
    # Handle POST (user message) requests.
    if request.method == "POST":
        user_question = request.form.get("question", "").strip()
        if user_question:
            session["chat_history"].append({"sender": "user", "message": user_question})
            
            def generate():
                # First, accumulate the final bot response.
                final_response = ""
                for event in graph.stream({"messages": [("user", user_question)]}, config):
                    for value in event.values():
                        # Overwrite with the latest content from the event.
                        final_response = value["messages"][-1].content
                print("Final bot response:", final_response)
                
                # Update session with the final response.
                session["chat_history"].append({"sender": "bot", "message": final_response})
                session.modified = True

                # Now, stream out the final response gradually.
                for char in final_response:
                    yield char
                    # Adjust or remove the delay as needed.
                    time.sleep(0.01)
            
            # Return a streaming response. The MIME type is text/plain,
            # but you can change it to "text/event-stream" if using SSE.
            return Response(stream_with_context(generate()), mimetype="text/plain")
        
        # If no question was provided, just re-render the chat messages.
        return render_template("chat_messages.html", chat_history=session["chat_history"])
    
    # For GET requests, render the full page.
    return render_template("chapter_viewer.html", chapter_number=chapter_number, chat_history=session["chat_history"], button_count=int(button_count))




@app.route("/home")
def go_home():
    session.clear()
    chapters = [{"number": i + 1, "start_page": start, "end_page": end} for i, (start, end) in enumerate(PAGE_RANGES)]
    return render_template("home.html", chapters=chapters)

if __name__ == "__main__":
    app.run(debug=True)
