from locust import HttpUser, task, between
import random
import time

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

        """Step 2: Navigate to chatbot page (assuming redirect)"""
        chatbot_response = self.client.get("/chapter/1", name="Chatbot Page")
        if chatbot_response.status_code != 200:
            print("❌ Failed to load chatbot page")
            return
        
        """Step 3: Send first message to chatbot"""
        message_1 = "Hello, how does this work?"
        chat_response_1 = self.client.post("/chapter/1", data={"question": message_1}, name="Send First Chat Message")
        if chat_response_1.status_code == 200:
            print(f"✅ Sent first message: {message_1}")
        else:
            print(f"❌ Failed to send first message")

        """Step 4: Wait for 20 seconds"""
        time.sleep(20)

        """Step 5: Send follow-up message"""
        message_2 = "Can you explain more?"
        chat_response_2 = self.client.post("/chapter/1", data={"question": message_2}, name="Send Follow-up Chat Message")
        if chat_response_2.status_code == 200:
            print(f"✅ Sent follow-up message: {message_2}")
        else:
            print(f"❌ Failed to send follow-up message")
