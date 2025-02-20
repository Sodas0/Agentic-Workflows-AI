
from langchain_openai import ChatOpenAI
from graph import build_graph
from dotenv import load_dotenv
from bookmark import initialize_bookmarks, get_page_ranges, get_num_buttons, save_section_pdf

import os
import json
import re

import os
import json
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from graph import build_graph
from bookmark import (
    initialize_bookmarks, get_page_ranges, 
    get_num_buttons, save_section_pdf
)

class JSON_Agent:
    def __init__(self):
        load_dotenv()

        self.llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
        self.graph = build_graph(self.llm)

        self.QUIZ_PATH = "../quizes/"
        self.PDF_PATH = "../data/wholeTextbookPsych.pdf"
        self.PAGE_RANGE_PATH = "../data/page_ranges.json"
        self.SECTION_PATH = "../data/sections"

        initialize_bookmarks(self.PDF_PATH, self.PAGE_RANGE_PATH)
        self.PAGE_RANGES = get_page_ranges(self.PAGE_RANGE_PATH)
        self.chapter_sub_chapter_count = get_num_buttons(self.PAGE_RANGE_PATH)

        if not os.path.exists(self.SECTION_PATH):
            save_section_pdf(self.PDF_PATH, self.PAGE_RANGE_PATH, self.SECTION_PATH)

    def generate(self, prompt):
        final_response = ""
        for event in self.graph.stream(
            {"messages": [("user", prompt)]},
            {"configurable": {"thread_id": "JSON_Agent"}}
        ):
            for value in event.values():
                final_response = value["messages"][-1].content

        return final_response

    def json_returned_from_prompt(self, prompt):
        response = self.generate(prompt)

        # Extract JSON portion using regex
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)

        if json_match:
            json_str = json_match.group(0)  # Extract matched JSON part
            try:
                json_response = json.loads(json_str)  # Parse JSON safely
                return json_response
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                return None  # Placeholder for failed section
        else:
            print("No valid JSON found in response.")
            return None  # Placeholder for failed section
