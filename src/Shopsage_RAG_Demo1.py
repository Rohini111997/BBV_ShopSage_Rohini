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


#------------------------- Set up your Groq API key --------------------------

load_dotenv()
groq_api_key = os.environ["GROQ_API_KEY"]

print("API key configured!")


#------------------------- Catalog Data Import --------------------------

import DataBase.Catalog_V1 as Catalog_V1  

product_catalog = Catalog_V1.product_catalog

print(f"Created knowledge base with:")
print(f"- {len(product_catalog)} category catalog created")