from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str
    groq_api_key: str
    langsmith_api_key: str
    langchain_project: str
    huggingface_api_key: str


settings = Settings()
