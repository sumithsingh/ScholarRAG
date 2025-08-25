# --- AI Model and Vector Database Settings ---
# The embedding model is used to turn text into numerical vectors
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# A balanced temperature for creative yet factual synthesis
LLM_TEMPERATURE = 0.25

# This defines how many relevant text chunks are sent to the AI for answering
VECTOR_DB_SEARCH_NEIGHBORS = 4

# --- Text Processing Settings ---
# How large each text chunk should be in characters
CHUNK_SIZE = 1000
# How much overlap there should be between chunks to maintain context
CHUNK_OVERLAP = 200

# --- Academic Paper Search Settings ---
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
# The number of papers to fetch for a given query
MAX_SEARCH_RESULTS = 5
# How many times to retry if the API call fails
SEARCH_RETRY_ATTEMPTS = 3