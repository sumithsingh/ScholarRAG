# config.py

# --- Model and Embedding Settings ---
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
LLM_TEMPERATURE = 0.2
VECTOR_DB_SEARCH_NEIGHBORS = 3  # How many documents to retrieve (k)

# --- Text Splitting Settings ---
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# --- Semantic Scholar API Settings ---
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
MAX_SEARCH_RESULTS = 5
SEARCH_RETRY_ATTEMPTS = 3