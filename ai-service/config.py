import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "Uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
