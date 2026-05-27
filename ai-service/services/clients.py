import sys
import logging
from groq import AsyncGroq
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
from config import GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("ai-service")

if not all([GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    logger.error("Missing critical environment variables. Check your .env file.")

groq_client = AsyncGroq(api_key=GROQ_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logger.info("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
logger.info("Embedding model loaded successfully.")
