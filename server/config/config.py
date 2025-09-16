import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일 로드

# <--------- OpenAI ---------->
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MINI_MODEL = os.getenv("GPT_MINI_MODEL")

# <--------- Google Gemini ---------->
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")