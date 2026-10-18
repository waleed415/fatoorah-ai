from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: str = "anthropic"  # "anthropic" or "openai" (OpenAI-compatible, incl. Ollama)
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_timeout: float = 90.0
    llm_script: str = "all"          # "all" or "latin"
    llm_input_mode: str = "layout"   # "layout" or "plain"

    # OCR
    ocr_mode: str = "single"         # "single" = Arabic model only, "dual" = Arabic + English
    ocr_max_side: int = 2000

        # VLM (vision model, one-step extraction). Reuses llm_base_url and llm_api_key.
    vlm_model: str = "qwen2.5vl-invoice"
    vlm_max_side: int = 1600     # page images are shrunk to this many pixels on the long side
    vlm_timeout: float = 300.0


settings = Settings()