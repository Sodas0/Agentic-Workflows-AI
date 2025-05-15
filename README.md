# Multi-Agent AI Tutor for Psychology Students

This repository utilizes the powerful capabilities of primarily **LangChain** and **LangGraph** to implement a multi-agent-based AI tutor. The project is a hands-on approach to learning and experimenting AI based technologies to make learning more engaging for students.

---

## **Purpose**

The primary objective of this repository is to:

1. **Experiment with LangChain and LangGraph:** Understand how these frameworks can be used to create and manage multi-agent systems for educational purposes.
    - We utilize Retrieval Augmented Generation techniques to tailor our chatbot's responses specifically for the user's textbook, so that any questions answered are directly relevant.
2. **Develop AI-Driven Learning Tools:** Design a prototype AI tutor capable of interacting with students, answering questions, and creating an engaging learning experience.
3. **Enhance Understanding of AI in Education:** Test workflows and frameworks that integrate AI into education to better understand their potential and limitations.

---


## **Goals**

2. Build a foundational educational platform to make textbook learning engaging and interactive
3. Test and refine AI-agent communication strategies to ensure accurate and meaningful responses tailored to students’ needs.

---

## **Running the Code**

Before running the code, navigate to the modular directory and add a file name ".env". Your .env file needs to contain a Qdrant cluster key, a LangChain API key, a name, and four OpenAI keys separated by dashes. Example:

```QDRANT_KEY=your_qdrant_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_key
NAME=your_name
OPENAI_API_KEYS=key1-key2-key3-key4
```


1. Run the command "pip install -r requirements.txt" to install all necessary requirements.
2. Naviate to the modular directory by running "cd modular"
3. Run the application by running "python app.py"
