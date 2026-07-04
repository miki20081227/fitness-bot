import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
#OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")

# Модель OpenRouter (роутер по бесплатным моделям)
#OPENROUTER_MODEL = "nousresearch/hermes-3-llama-3.1-405b:free"
OLLAMA_MODEL = "qwen2.5-coder:3b "