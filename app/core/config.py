import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "LauzHack API"
    API_V1_STR: str = "/api/v1"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ORCHESTRATOR_MODEL: str = "gemini-2.5-flash"
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY", "")
    JUNIOR_MODEL: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8"

settings = Settings()
