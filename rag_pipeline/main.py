# rag_pipeline/main.py

import os
import requests
import time
from typing import List, Dict, Any

from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import PromptTemplate

from config import (
    EMBEDDING_MODEL_NAME, LLM_TEMPERATURE, VECTOR_DB_SEARCH_NEIGHBORS,
    CHUNK_SIZE, CHUNK_OVERLAP, SEMANTIC_SCHOLAR_API_URL,
    MAX_SEARCH_RESULTS, SEARCH_RETRY_ATTEMPTS
)

def _refine_search_query(query: str) -> str:
    """
    Refines a user query into a more effective search query for an academic database
    using a fast, rule-based approach.
    """
    # Keywords that encourage definitional and explanatory results
    definitional_keywords = [
        "definition", "explanation", "key concepts", "introduction to",
        "principles of", "overview of", "what is"
    ]
    # Check if the query already seems detailed or definitional
    if not any(keyword in query.lower() for keyword in definitional_keywords):
        refined_query = f"explanation and key concepts of {query}"
        print(f"Refined search query: {refined_query}")
        return refined_query
    return query # Return original query if it's already good

def search_semantic_scholar(query: str, api_key: str) -> List[Dict[str, Any]]:
    """Searches Semantic Scholar for academic papers with retry logic."""
    params = {"query": query, "limit": MAX_SEARCH_RESULTS, "fields": "title,abstract,url"}
    headers = {"x-api-key": api_key}
    for attempt in range(SEARCH_RETRY_ATTEMPTS):
        try:
            response = requests.get(SEMANTIC_SCHOLAR_API_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            return [{"title": p.get("title", "No title"), "abstract": p.get("abstract") or "No abstract available.", "url": p.get("url", "No URL")} for p in data]
        except Exception:
            time.sleep(2)
    return []

def build_vector_store(papers: List[Dict[str, Any]]) -> Chroma:
    """Builds a Chroma vector store using a smarter text splitter."""
    docs = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", ", ", " "]
    )
    
    for paper in papers:
        if paper['abstract'] and paper['abstract'] != "No abstract available.":
            chunks = splitter.split_text(paper['abstract'])
            for chunk in chunks:
                docs.append(Document(page_content=chunk, metadata={"source": paper['url']}))

    if not docs:
        raise ValueError("No valid abstracts found in search results to build a knowledge base.")

    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    db = Chroma.from_documents(docs, embedding=embedder)
    return db

def process_query(query: str, api_key: str) -> Dict[str, Any]:
    """The main RAG pipeline, now with efficient query refinement."""
    start_time = time.time()
    metrics = {"sources_found": 0, "docs_retrieved": 0, "is_error": False}

    if not os.getenv("GOOGLE_API_KEY"):
        metrics["is_error"] = True
        return {"answer": "Error: GOOGLE_API_KEY is not configured.", "sources": "", "metrics": metrics}
    
    # Use the cost-effective and efficient Flash model
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=LLM_TEMPERATURE)

    # Step 1: Efficiently refine the search query
    refined_query = _refine_search_query(query)
    
    # Step 2: Search with the better query
    papers = search_semantic_scholar(refined_query, api_key)
    metrics["sources_found"] = len(papers)

    if not papers:
        return {"answer": "I could not find any relevant academic papers for this query.", "sources": "", "metrics": metrics}
    
    try:
        vector_db = build_vector_store(papers)
        retriever = vector_db.as_retriever(search_kwargs={"k": VECTOR_DB_SEARCH_NEIGHBORS})
        # Use the original user query for retrieval for maximum relevance
        retrieved_docs = retriever.invoke(query)
        metrics["docs_retrieved"] = len(retrieved_docs)

        if not retrieved_docs:
            return {"answer": "Could not find a specific answer in the retrieved papers.", "sources": "", "metrics": metrics}

        prompt_template = """
        You are an expert research assistant and an excellent tutor. Your goal is to provide a clear, insightful, and helpful answer to the user's question.
        Your answer must be based **exclusively** on the following sources. Do not use any other knowledge.
        Follow these instructions precisely:
        1.  Begin your response with a direct and clear definition of the main topic.
        2.  After the definition, synthesize the key concepts, methodologies, and applications mentioned across all the provided sources.
        3.  Organize your answer logically. Use paragraphs to separate different ideas.
        4.  If the sources do not contain enough information to answer the question, you must state: "I could not find a definitive answer in the provided sources."

        SOURCES:
        {context}

        QUESTION:
        {question}

        YOUR HELPFUL AND DETAILED ANSWER:
        """
        prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        
        combine_docs_chain = create_stuff_documents_chain(llm, prompt)
        response = combine_docs_chain.invoke({"context": retrieved_docs, "question": query})
        
        sources = set(doc.metadata['source'] for doc in retrieved_docs)
        metrics["response_time_ms"] = int((time.time() - start_time) * 1000)
        
        return {
            "answer": response,
            "sources": "\n".join(sources),
            "metrics": metrics
        }
        
    except Exception as e:
        metrics["is_error"] = True
        metrics["response_time_ms"] = int((time.time() - start_time) * 1000)
        return {"answer": f"An error occurred: {e}", "sources": "", "metrics": metrics}