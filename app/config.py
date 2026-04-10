from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    # Gemini 2.5 Flash — current free tier with best quota
    # Alternatives: gemini-2.5-flash-lite, gemini-2.0-flash, gemini-2.0-flash-lite
    model_name: str = "gemini-2.5-flash"
    max_pdf_size_mb: int = 50
    max_batch_size: int = 10
    upload_dir: str = "uploads"

    model_config = {"env_file": ".env"}


settings = Settings()
