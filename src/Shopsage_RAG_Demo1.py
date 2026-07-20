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
from Agent_2 import rag_agent   # importing runs the bootstrap at the bottom of Agent_2.py




def chat_fn(message, history):
    try:
        return rag_agent.get_rag_product_recommendation(message, history=history)
    except Exception as e:
        import traceback; traceback.print_exc()
        return f"Sorry, something went wrong: {e}"

custom_css = """
.gradio-container {
    background: linear-gradient(160deg, #fff1f2 0%, #fffbeb 100%) !important;
}

/* Belt-and-suspenders: even if dark mode is active, force light colors */
.dark {
    --body-background-fill: #fff1f2;
    --background-fill-primary: #ffffff;
    --background-fill-secondary: #fff7ed;
    --block-background-fill: #ffffff;
    --body-text-color: #1f2937;
    --body-text-color-subdued: #6b7280;
    --block-label-text-color: #1f2937;
    --block-title-text-color: #1f2937;
    --input-background-fill: #ffffff;
    --input-placeholder-color: #9ca3af;
    --border-color-primary: #fecdd3;
    --chatbot-text-color: #1f2937;
}
"""

# Officially documented way to force light mode via URL param
force_light = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'light') {
        url.searchParams.set('__theme', 'light');
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
    js=force_light,
)