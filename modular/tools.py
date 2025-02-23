import json
from langchain_core.messages import ToolMessage
from langchain_community.tools import tool
from retrievertool import generate_retriever_tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import ast
import re


class BasicToolNode:
    """
    A node that processes and executes tool requests embedded in the last AI message.
    """

    def __init__(self, tools: list) -> None:
        # Create a dictionary of tools for easy access by their names.
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        """
        Process tool calls from the last AI message and execute them.
        """
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No messages found in input.")

        outputs = []

        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}
    
# ==========================================================================================
# Easily modify this list of tools to add or remove tools from the single agent.
# We can also add new agents with their own tools, as long as we route them properly in the workflow.
# Look at the example below to see how a tool is defined.

# [TEST]
# def sum(x,y):
#     z = x+y 
#     print("wtf")
#     return z
# @tool
# def add(a: int, b: int) -> int:
#     """Use this tool to add two numbers."""
#     return sum(a,b)
# ==========================================================================================


# No @tool decorator required. Simply call function in app.py when needed.
def evaluate_quiz_answers(quiz, answers):
    # PADDY TODO:
        # Render the bot_response in the chatbox after the quiz has been submitted. 
        # I've got you started, and right now, it just prints the responses after taking the quiz to the terminal where 
        # you run the server.
    
    tools = []
    llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)    
    graph = create_react_agent(llm, tools)

    print(quiz)
    print(answers)

    dict_template = """{
        "Questions": [
            {
                "Feedback": "",
                "Correct_Answer": "",
                "Student_Answer": ""
            }
        ]
    }"""

    pre_message  = f"You are an quiz evaluator for a psychology textbook. Based on the following psychology questions, evaluate the user's answers.\
                    Be optimistic in your responses and specifically ask if they need help on anything.\
                    USER QUIZ: {quiz}. USER ANSWERS: {answers}. Make sure to address every single question. Under all circumstances, you need to address\
                    every single question and answer that the user submitted. ALWAYS RETURN ALL ANSWERS AS A PYTHON DICT, THE PROGRAM MUST BE ABLE TO PARSE ON YOUR RESPONSE. Use this dict template {dict_template} " 

    print(pre_message)
    config = {"thread_id":"🦫"}
    
    agent_response = ""
    for event in graph.stream({"messages": [("user", pre_message)]}, config):
        for value in event.values():
            agent_response = value["messages"][-1].content
    print("---------------base------------------")
    print(agent_response)
    print("---------------base-end------------------")

    dict_pattern = r'(\{.*\})'

    match = re.search(dict_pattern, agent_response, re.DOTALL)

    if match:
        response_dict = match.group(1)
        try:
            response_dict = ast.literal_eval(response_dict)
            print("---------------dict------------------")
            print(response_dict)
            print("---------------dict-end------------------")
            score = 0
            total_questions = 0
            question_feedback = []
            correct_answers = []
            for question in response_dict["Questions"]:
                total_questions += 1
                question_feedback.append(question["Feedback"])
                correct_answers.append(question["Correct_Answer"])
                if question["Correct_Answer"] == question["Student_Answer"]:
                    score += 1
            print("Correct: ", score)
            print("Total questions: ", total_questions)
            print("Score: ", score/total_questions)
            print("Feedback: ", question_feedback)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print("Regex error")
    
        
    return agent_response, score, total_questions, question_feedback, correct_answers

    
def get_tools():
    """
    Returns a list of tools for the chatbot.
    """    
    textbook_retriever = generate_retriever_tool()
    
    tools = [textbook_retriever] 
    return tools

