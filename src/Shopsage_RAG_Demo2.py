from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
import os
import pandas as pd
import json
from typing import List, Dict
from dotenv import load_dotenv
import gradio as gr

#------------------------- Set up your Groq API key --------------------------

load_dotenv()
groq_api_key = os.environ["GROQ_API_KEY"]

print("API key configured!")


# app.py
from src.Agent_2 import rag_agent   # importing runs the bootstrap at the bottom of Agent_2.py


rag_agent.vectorstore._collection.count()


# ------------------------- Shopper login (terminal, pre-launch) -------------
# Enter a customer ID before the UI starts. Blank = anonymous guest session.
shopper_line = ""
cid = input("\nCustomer ID (e.g. CUST-0028, blank for guest): ").strip()
if cid:
    status = rag_agent.set_shopper(cid)     # loads profile + personalizes prompt
    print(f"[login] {status}")
    shopper_line = f"\n\n{status}."
else:
    print("[login] anonymous guest session")


def chat_fn(message, history):
    try:
        result = rag_agent.get_rag_product_recommendation(message, history=history)
        return result["reply"]
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"Sorry, something went wrong: {e}"

custom_css = """
.gradio-container {
    background: linear-gradient(160deg, #2a1418 0%, #2b2012 100%) !important;
}

/* Slight translucency so the gradient glows through panels */
.dark {
    --body-background-fill: transparent;
    --background-fill-primary: rgba(255, 241, 242, 0.04);
    --block-background-fill: rgba(255, 241, 242, 0.05);
    --border-color-primary: rgba(254, 205, 211, 0.18);
}
"""

# Force dark mode via the documented URL param
force_dark = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

demo = gr.ChatInterface(
    fn=chat_fn,
    title="ShopSage 🛍️",
    description=(
        "Welcome! I'm ShopSage, your personal shopping assistant. "
        "Tell me what you're looking for and I'll find pieces you'll love."
        + shopper_line
    ),
    examples=[
        "Breathable gym socks for women under ₹600",
        "A crisp formal shirt for office wear, men, size L",
        "Casual cotton t-shirt under 700 rupees",
    ],
    chatbot=gr.Chatbot(
        height=480,
        avatar_images=(None, "https://em-content.zobj.net/source/apple/391/shopping-bags_1f6cd-fe0f.png"),
    ),
    textbox=gr.Textbox(placeholder="What are you shopping for today?"),
)

demo.launch(
    share=True,
    debug=True,
    theme=gr.themes.Soft(),
    css=custom_css,
    js=force_dark,
)