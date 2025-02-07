from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from langchain_openai import ChatOpenAI
from graph import build_graph
from dotenv import load_dotenv
import os
import io
from PyPDF2 import PdfReader, PdfWriter

def get_config():
    configuration = {"configurable": {"thread_id": "🍅"}}
    return configuration

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session handling

# Initialize LLM and graph
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
graph = build_graph(llm)

pre_message  = "Give me a cool fact about beavers." 
config = get_config()
bot_response = ""
for event in graph.stream({"messages": [("user", pre_message)]}, config):
    for value in event.values():
        bot_response = value["messages"][-1].content


print(bot_response)
# Append the bot's message to chat history
# session["chat_history"].append({"sender": "bot", "message": bot_response})
