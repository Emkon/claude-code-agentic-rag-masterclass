import os
from app.config import settings

# Must be set before importing langsmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI


def get_traced_client() -> AsyncOpenAI:
    client = AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=settings.groq_api_key,
    )
    return wrap_openai(client)
