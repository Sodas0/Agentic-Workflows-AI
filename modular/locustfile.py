from locust import HttpUser, task, between
import random
import time
from bs4 import BeautifulSoup  # Used for parsing bot response

class UserBehavior(HttpUser):
    wait_time = between(1, 3)  # Simulates user delay between actions

    @task
    def enter_code_and_chat(self):
        """Step 1: Enter 4-digit code and submit"""
        code = "".join(str(random.randint(0, 9)) for _ in range(4))
        response = self.client.post("/", data={"code": code}, name="Submit 4-Digit Code")

        if response.status_code == 200:
            print(f"✅ Successfully entered code: {code}")
        else:
            print(f"❌ Failed to enter code: {code} (Status: {response.status_code})")
            return  # Stop if login fails

        """Step 2: Navigate to chatbot page and wait for bot message"""
        chatbot_response = self.client.get("/chapter/6", name="Chatbot Page")
        if chatbot_response.status_code != 200:
            print("❌ Failed to load chatbot page")
            return

        # Step 2.1: Check if bot has initiated the conversation
        bot_message = self.extract_bot_message(chatbot_response.text)
        if bot_message:
            print(f"✅ Bot initiated conversation: {bot_message}")
        else:
            print("❌ Bot did not send an initial message!")
            return  # Stop test if no bot message is received

        """Step 3: Send first user message"""
        time.sleep(5)  # Simulate user reading time
        message_1 = "Hello, how does this work?"
        chat_response_1 = self.client.post("/chapter/6", data={"question": message_1}, name="Send First Chat Message")

        if chat_response_1.status_code == 200:
            print(f"✅ Sent first message: {message_1}")

            """Step 4: Wait for the bot to respond (polling mechanism)"""
            if self.wait_for_bot_response():
                print("✅ Bot responded to first message")
            else:
                print("❌ No bot response received for the first message!")

        else:
            print(f"❌ Failed to send first message")

        time.sleep(5)  # Simulate user reading time

        """Step 5: Send follow-up message"""
        message_2 = "Can you explain more?"
        chat_response_2 = self.client.post("/chapter/6", data={"question": message_2}, name="Send Follow-up Chat Message")

        if chat_response_2.status_code == 200:
            print(f"✅ Sent follow-up message: {message_2}")

            """Step 6: Wait for the bot to respond (polling mechanism)"""
            if self.wait_for_bot_response():
                print("✅ Bot responded to follow-up message")
            else:
                print("❌ No bot response received for the follow-up message!")

        else:
            print(f"❌ Failed to send follow-up message")

        """Step 7: Start the quiz"""
        self.start_quiz()

    def end_session_with_home_button(self):
        """Clicks the Home button to finalize the session"""
        print("🛑 Clicking Home button to end session...")
        
        home_response = self.client.get("/home", name="Click Home Button")

        if home_response.status_code == 200:
            print("✅ Successfully ended session by clicking Home button.")
        else:
            print(f"❌ Failed to end session (Status: {home_response.status_code})")

        """Wait a short time before allowing a new test to start"""
        time.sleep(3)  # Ensures previous session fully ends before restarting

    def start_quiz(self):
        """Starts the quiz and answers the questions."""
        message_1 = "I am ready for the quiz."
        chat_response_1 = self.client.post("/chapter/6", data={"question": message_1}, name="Ready for quiz")

        if chat_response_1.status_code == 200:
            print(f"✅ Sent follow-up message: {chat_response_1}")

            if self.wait_for_bot_response():
                print("✅ Bot responded to ready for quiz message")
            else:
                print("❌ No bot response received for the ready for quiz message!")
        else:
            print(f"❌ Failed to send ready for quiz message")

        print("🎯 Starting quiz...")
        
        # Get the current quiz data
        quiz_response = self.client.get("/get_current_quiz", name="Start Quiz")
        
        if quiz_response.status_code == 200:
            print("✅ Successfully started quiz.")
            
            # Parse the JSON response
            quiz_data = quiz_response.json()
            quiz = quiz_data.get("quiz", [])
            
            # Loop through the questions and answer them
            quiz_with_answers = []
            for question_data in quiz:
                question = question_data.get("question")
                options = question_data.get("options")
                correct_answer = question_data.get("answer")

                # Simulate a user answer (e.g., always picking the correct answer or random selection)
                user_answer = self.simulate_user_answer(options, correct_answer)

                # Create the answer object with question, answer, and user_answer
                quiz_with_answers.append({
                    "question": question,
                    "answer": correct_answer,
                    "user_answer": user_answer
                })
            
            # Submit the answers to the /submit-answer endpoint
            self.submit_answers(quiz_with_answers)
        else:
            print(f"❌ Failed to fetch quiz (Status: {quiz_response.status_code})")

    def simulate_user_answer(self, options, correct_answer):
        """Simulate the user answering the question."""
        # For simplicity, always choose the correct answer or you can use random selection
        return correct_answer  # Replace with random.choice(options) for random answers

    def submit_answers(self, quiz_with_answers):
        """Submit the answers to the backend."""
        # Submit the answers as a JSON object to the /submit-answer endpoint
        response = self.client.post("/submit-answer", json={"answers": quiz_with_answers})
        
        if response.status_code == 200:
            print("✅ Answers submitted successfully.")
        else:
            print(f"❌ Failed to submit answers (Status: {response.status_code})")

        self.end_session_with_home_button()

    def extract_bot_message(self, html_response):
        """Extracts the bot's message from the chat response using BeautifulSoup"""
        try:
            soup = BeautifulSoup(html_response, "html.parser")
            bot_messages = soup.find_all("div", class_="bot-message")
            if bot_messages:
                return bot_messages[-1].text.strip()  # Get latest bot response
            return None
        except Exception as e:
            print(f"Error extracting bot message: {e}")
            return None

    def wait_for_bot_response(self, max_wait_time=20, poll_interval=1):
        """
        Polls the chat page for a bot response, waiting up to `max_wait_time` seconds.
        Checks every `poll_interval` seconds.
        """
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            chat_history_response = self.client.get("/chapter/6", name="Check Bot Response")

            if chat_history_response.status_code == 200:
                bot_reply = self.extract_bot_message(chat_history_response.text)
                if bot_reply:
                    print(f"🗨️ Bot response received: {bot_reply}")
                    return True  # Bot responded

            time.sleep(poll_interval)  # Wait before checking again

        return False  # No bot response after max_wait_time


