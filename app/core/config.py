import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "LauzHack API"
    API_V1_STR: str = "/api/v1"

    # Model configurations
    ORCHESTRATOR_MODEL: str = os.getenv("ORCHESTRATOR_MODEL", "gemini-2.5-flash")
    JUNIOR_DEV_MODEL: str = os.getenv("JUNIOR_DEV_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8")

    # Base URLs for API endpoints
    ORCHESTRATOR_BASE_URL: str = os.getenv("ORCHESTRATOR_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    JUNIOR_DEV_BASE_URL: str = os.getenv("JUNIOR_DEV_BASE_URL", "https://api.together.xyz/v1")

    # API Keys from environment
    TOGETHER_API_KEY: str = os.getenv("TOGETHER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    def get_orchestrator_api_key(self) -> str:
        """Get the appropriate API key for the orchestrator based on base URL."""
        if "generativelanguage.googleapis.com" in self.ORCHESTRATOR_BASE_URL:
            return self.GEMINI_API_KEY
        elif "api.together.xyz" in self.ORCHESTRATOR_BASE_URL:
            return self.TOGETHER_API_KEY
        else:
            return self.OPENAI_API_KEY

    def get_junior_dev_api_key(self) -> str:
        """Get the appropriate API key for junior dev based on base URL."""
        if "generativelanguage.googleapis.com" in self.JUNIOR_DEV_BASE_URL:
            return self.GEMINI_API_KEY
        elif "api.together.xyz" in self.JUNIOR_DEV_BASE_URL:
            return self.TOGETHER_API_KEY
        else:
            return self.OPENAI_API_KEY

settings = Settings()
