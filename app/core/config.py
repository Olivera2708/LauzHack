import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "LauzHack API"
    API_V1_STR: str = "/api/v1"

    # Model configurations
    ORCHESTRATOR_MODEL: str = os.getenv("ORCHESTRATOR_MODEL", "gpt-4")
    JUNIOR_DEV_MODEL: str = os.getenv("JUNIOR_DEV_MODEL", "gpt-3.5-turbo")

    # Base URLs for API endpoints
    ORCHESTRATOR_BASE_URL: str = os.getenv("ORCHESTRATOR_BASE_URL", "https://api.openai.com/v1")
    JUNIOR_DEV_BASE_URL: str = os.getenv("JUNIOR_DEV_BASE_URL", "https://api.openai.com/v1")

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
