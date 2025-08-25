# app.py

import os
import streamlit as st
from dotenv import load_dotenv

# --- Load Environment Variables ---
# CRITICAL: This MUST be the first line of code to run
# It loads the keys from .env before any other module tries to use them.
load_dotenv()

# --- Now, we can safely import our modules ---
from rag_pipeline.main import process_query
from database.connector import init_db, log_interaction

# --- Page Configuration ---
st.set_page_config(
    page_title="ScholarRAG: Academic Research Assistant",
    page_icon="🧠",
    layout="wide"
)

# --- Initialization ---
# This runs once at the start to ensure the DB table exists.
init_db()

# --- Main UI ---
st.title("🧠 ScholarRAG: Academic Research Assistant")
st.markdown("Enter a research query to get a summarized answer with cited sources from academic papers, powered by Google Gemini.")

# --- Form for User Input ---
with st.form("query_form"):
    query_text = st.text_input("Enter your research query:", "")
    submit_button = st.form_submit_button("Get Answer")

# --- Processing and Output ---
if submit_button and query_text:
    # Check for API keys first
    semantic_scholar_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not semantic_scholar_api_key or not google_api_key or "PASTE_YOUR" in semantic_scholar_api_key or "PASTE_YOUR" in google_api_key:
        st.error("API keys for Semantic Scholar or Google AI are not set correctly. Please check your .env file.")
    else:
        with st.spinner("Searching papers, building knowledge base, and generating answer with Gemini..."):
            try:
                response = process_query(query_text, semantic_scholar_api_key)
                answer = response.get("answer", "No answer found.")
                sources = response.get("sources", "No sources found.")

                st.success("**Answer:**")
                st.markdown(answer)

                if sources:
                    st.info("**Sources:**")
                    source_list = sources.split('\n')
                    for source in source_list:
                        if source.strip():
                            st.markdown(f"- {source.strip()}")

                log_interaction(query=query_text, answer=answer, sources=sources)
                
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
                log_interaction(query=query_text, answer=f"ERROR: {e}", sources="")

elif submit_button:
    st.warning("Please enter a query.")