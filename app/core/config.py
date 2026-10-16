from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "anthropic"  # "anthropic" or "openai" (OpenAI-compatible, incl. Ollama)
    llm_model: str = ""              # empty = default for anthropic; required for openai
    llm_api_key: str = ""
    llm_base_url: str = ""           # e.g. Ollama: http://host.docker.internal:11434/v1
    llm_timeout: float = 90.0


settings = Settings()