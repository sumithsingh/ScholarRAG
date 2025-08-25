import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from rag_pipeline.main import process_query
from database.connector import init_db, log_interaction, update_feedback

st.set_page_config(
    page_title="ScholarRAG: Academic Research Assistant",
    page_icon="🧠",
    layout="wide"
)

if 'last_interaction_id' not in st.session_state:
    st.session_state.last_interaction_id = None
if 'feedback_given' not in st.session_state:
    st.session_state.feedback_given = False

init_db()

st.title("🧠 ScholarRAG: Academic Research Assistant")
st.markdown("Enter a research query to get a summarized answer with cited sources from academic papers, powered by Google Gemini.")

with st.form("query_form"):
    query_text = st.text_input("Enter your research query:", "")
    submit_button = st.form_submit_button("Get Answer")

if submit_button and query_text:
    st.session_state.feedback_given = False
    
    with st.spinner("Searching papers, building knowledge base, and generating answer..."):
        try:
            response_data = process_query(query_text, os.getenv("SEMANTIC_SCHOLAR_API_KEY"))
            
            # Use .get() for safe access to prevent crashes from unexpected backend responses
            answer = response_data.get("answer", "An unexpected error occurred. No answer was returned.")
            sources = response_data.get("sources", "")
            metrics = response_data.get("metrics", {})

            # Construct the complete log dictionary for the success case
            log_data = {
                "query": query_text,
                "answer": answer,
                "sources": sources,
                "feedback_score": None, # Initial feedback is null
                **metrics
            }
            
            st.session_state.last_interaction_id = log_interaction(log_data)
            
            st.success("**Answer:**")
            st.markdown(answer)
            if sources:
                st.info("**Sources:**")
                links = [f"- [{s.split('/')[-1]}]({s})" for s in sources.split('\n')]
                st.markdown("\n".join(links), unsafe_allow_html=True)

        except Exception as e:
            st.error(f"A critical error occurred in the application: {e}")
            # Construct a complete log dictionary for the failure case
            error_log_data = {
                "query": query_text,
                "answer": f"CRITICAL ERROR: {e}",
                "sources": "",
                "response_time_ms": -1,
                "sources_found": 0,
                "docs_retrieved": 0,
                "is_error": True,
                "feedback_score": None
            }
            log_interaction(error_log_data)

if st.session_state.last_interaction_id and not st.session_state.feedback_given:
    st.write("---")
    st.write("**Was this answer helpful?**")
    
    col1, col2, _ = st.columns([1, 1, 10])
    
    with col1:
        if st.button("👍"):
            update_feedback(st.session_state.last_interaction_id, 1)
            st.success("Thank you for your feedback!")
            st.session_state.feedback_given = True
            st.rerun()

    with col2:
        if st.button("👎"):
            update_feedback(st.session_state.last_interaction_id, -1)
            st.success("Thank you for your feedback!")
            st.session_state.feedback_given = True
            st.rerun()