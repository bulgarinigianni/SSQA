from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    model_name: str = "claude-sonnet-4-20250514"
    max_pdf_size_mb: int = 50
    max_batch_size: int = 10
    upload_dir: str = "uploads"

    model_config = {"env_file": ".env"}


settings = Settings()
