
import os
from dotenv import load_dotenv
from groq import Groq
from system_prompt import get_system_prompt

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask(user_message):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    print("=== TEST 1 ===")
    print("User: I need a waterproof jacket under $80 for hiking")
    print("Assistant:", ask("I need a waterproof jacket under $80 for hiking"))
    
    print("\n=== TEST 2 ===")
    print("User: Show me running shoes, my budget is $50")
    print("Assistant:", ask("Show me running shoes, my budget is $50"))

