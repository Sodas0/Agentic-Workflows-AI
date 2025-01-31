import os
import json
from openai import OpenAI
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import re

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), ".env")
if not load_dotenv(env_path):
    print(f"Failed to load .env file from {env_path}")
else:
    print(f".env file loaded successfully from {env_path}")

client = OpenAI()

# Ensure OpenAI API key is available
client.api_key = os.getenv("OPENAI_API_KEY")
if not client.api_key:
    raise EnvironmentError("OPENAI_API_KEY not set in environment variables.")

os.environ["OPENAI_API_KEY"] = client.api_key  # Ensure it's in os.environ

class Grader:
    def __init__(self, chat_url="http://127.0.0.1:5000/chat", max_retries=3):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0)
        self.chat_url = chat_url
        self.max_retries = max_retries
        self.base_json_template = {
            "chapter": "",
            "section": "",
            "difficulty": "",
            "number_of_questions": 0,
            "questions": []
        }

        # MCQ Subtemplate
        self.mcq_json_template = {
            "question": "",
            "options": [],  # List of options for MCQ
            "answer": "",  # Correct answer for MCQ
            "student_response": "",
            "score": 0,
            "feedback": ""
        }

        # SAQ Subtemplate
        self.saq_json_template = {
            "question": "",
            "answer": "",  # Correct answer for SAQ
            "student_response": "",
            "score": 0,
            "feedback": ""
        }

        # String version of the templates for use in prompts
        self.base_json_template_txt = """{
            "chapter": "",
            "section": "",
            "difficulty": "",
            "number_of_questions": 0,
            "questions": []
        }"""

        self.mcq_json_template_txt = """{
            "question": "",
            "options": [],
            "answer": "",
            "student_response": "",
            "score": 0,
            "feedback": ""
        }"""

        self.saq_json_template_txt = """{
            "question": "",
            "answer": "",
            "student_response": "",
            "score": 0,
            "feedback": ""
        }"""

    def clean_and_parse_response(self, response_text):
        """Clean and parse the response from OpenAI."""
        # Remove any leading/trailing whitespace
        response_text = response_text.strip()
        
        # Check if the response is already a valid JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass  # If it's not valid JSON, continue with cleaning

        # Try to extract JSON from the response
        match = re.search(r'(\{.*\}|\[.*\])', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                print(f"Error decoding extracted JSON: {e}")
                return None
        else:
            print("No valid JSON found in the response")
            return None

    def send_to_openai(self, prompt, base_template, question_template):
        """Sends a prompt to OpenAI and returns a validated JSON response."""
        for attempt in range(self.max_retries):
            # try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Your response must strictly follow the required JSON format with no additional text or explanation."},
                        {"role": "user", "content": prompt}
                    ]
                )
                response_text = response.choices[0].message.content
                response_json = self.clean_and_parse_response(response_text)
                print(response_json)
                return response_json
            #     if response_json and self.validate_json(response_json, base_template, question_template):
            #         return response_json
            #     else:
            #         print(f"Attempt {attempt + 1}: Invalid JSON format, retrying...")
            # except Exception as e:
            #     print(f"Attempt {attempt + 1}: Error - {e}, retrying...")
        
        return {"score": 0, "feedback": "Failed to generate valid response after multiple attempts."}

    def validate_json(self, response_json, base_template, question_template):
        """Validates whether the response_json matches the expected base and question templates."""
        if not isinstance(response_json, dict):
            return False
        
        # Validate base template
        for key in base_template.keys():
            if key not in response_json:
                return False
            if isinstance(base_template[key], list):  # Validate questions list
                if not isinstance(response_json[key], list):
                    return False
                # Validate each question in the list
                for item in response_json[key]:
                    if not isinstance(item, dict):
                        return False
                    # Validate each question against the question template
                    if not self.validate_question(item, question_template):
                        return False
            elif type(response_json[key]) is not type(base_template[key]):
                return False
        return True

    def validate_question(self, question_item, question_template):
        """Validates that each question matches the question template."""
        for key, value in question_template.items():
            if key not in question_item:
                return False
            if isinstance(value, list) and not isinstance(question_item[key], list):
                return False
            if type(question_item[key]) is not type(value):
                return False
        return True

    def call_rag(self, prompt, question_type, is_generation=False):
        """Calls the external RAG chat endpoint to fetch an answer or generate questions."""
        # Choose the correct template based on the question type
        if question_type == "MCQ":
            template = self.mcq_json_template
        elif question_type == "SAQ":
            template = self.saq_json_template
        else:
            print("Invalid question type.")
            return "Error: Invalid question type."

        try:
            payload = {
                "message": prompt,
                "template": template,
                "is_generation": is_generation
            }
            response = requests.post(self.chat_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "No response provided.")
            else:
                print(f"RAG API Error: {response.status_code}")
        except requests.RequestException as e:
            print(f"RAG API request failed: {e}")
        return "Error retrieving response from RAG."

    def generate_multiple_choice_questions(self, chapter, section, difficulty, number_of_questions, context):
        """Generates multiple-choice questions using RAG and formats them using OpenAI."""
        # Generate questions using RAG
        rag_prompt = f"Generate {number_of_questions} multiple-choice questions from Chapter {chapter}, Section {section}, with difficulty level {difficulty} (1 being easiest, 5 being hardest). Use the following context: {context}"
        rag_response = self.call_rag(rag_prompt, "MCQ", is_generation=True)
        print(rag_response)
        # Format RAG response using OpenAI
        formatting_prompt = f"""
        Format the following multiple-choice questions into the required JSON structure:

        {rag_response}

        REQUIRED JSON format:
        {{
            "chapter": "{chapter}",
            "section": "{section}",
            "difficulty": "{difficulty}",
            "number_of_questions": {number_of_questions},
            "questions": [
                {{
                    "question": "Question text here",
                    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                    "answer": "Correct answer here",
                    "student_answer": "Will be filled in later",
                    "score": 0,
                    "feedback": ""
                }}
            ]
        }}
        """

        response = self.send_to_openai(formatting_prompt, self.base_json_template, self.mcq_json_template)
        return response if isinstance(response, dict) else {}

    def generate_short_answer_questions(self, chapter, section, difficulty, number_of_questions, context):
        """Generates short answer questions using RAG and formats them using OpenAI."""
        # Generate questions using RAG
        rag_prompt = f"Generate {number_of_questions} short answer questions from Chapter {chapter}, Section {section}, with difficulty level {difficulty} (1 being easiest, 5 being hardest). Use the following context: {context}"
        rag_response = self.call_rag(rag_prompt, "SAQ", is_generation=True)

        # Format RAG response using OpenAI
        formatting_prompt = f"""
        Format the following short answer questions into the required JSON structure:

        {rag_response}

        REQUIRED JSON format:
        {{
            "chapter": "{chapter}",
            "section": "{section}",
            "difficulty": "{difficulty}",
            "number_of_questions": {number_of_questions},
            "questions": [
                {{
                    "question": "Question text here",
                    "answer": "Answer text here",
                    "student_answer": "Will be filled in later",
                    "score": 0,
                    "feedback": ""
                }}
            ]
        }}
        """

        response = self.send_to_openai(formatting_prompt, self.base_json_template, self.saq_json_template)
        return response if isinstance(response, dict) else {}

    def get_answers_from_rag(self, questions, question_type):
        """Fetches answers for generated questions using the RAG endpoint."""
        answers = []
        for q in questions:
            retrieved_answer = self.call_rag(q["question"], question_type)
            q["answer"] = retrieved_answer
            answers.append(q)
        return answers

    def grade_answers(self, questions, question_type, response, context):
        """Grades student answers based on expected answers."""
        # Select the correct template based on the question type
        if question_type == "MCQ":
            question_template_txt = self.mcq_json_template_txt
            question_template = self.mcq_json_template
        elif question_type == "SAQ":
            question_template_txt = self.saq_json_template_txt
            question_template_txt = self.saq_json_template
        else:
            print("Invalid question type.")
            return {"score": 0, "feedback": "Error: Invalid question type."}

        for q in questions:
            grading_prompt = f"""
            Grade the following question and answer on a scale of 0-100.
            Context: {context}
            Question: {q["question"]}
            Expected Answer: {q["answer"]}
            Student Answer: {response}
            Provide a numerical score and a brief explanation.

            Example JSON format:
            {{
                "chapter": "1",
                "section": "1",
                "difficulty": "3",
                "number_of_questions": 1,
                "questions": [
                    {question_template_txt}
                ]
            }}
            """
            eval = self.send_to_openai(grading_prompt, self.base_json_template, question_template)

            q["score"] = eval.get("score", 0)
            q["feedback"] = eval.get("feedback", "No feedback provided.")
        
        return questions
