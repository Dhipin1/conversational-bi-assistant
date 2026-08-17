import os
from dotenv import load_dotenv

load_dotenv(override=True)

_LLM_CACHE: dict = {}


def get_llm():
    """
    Returns a cached LLM instance based on LLM_PROVIDER env var.

    Supported providers:
      - ollama (default): local, free, private. Requires Ollama running.
      - groq: cloud, very fast inference, free tier. Good for public deployment.
      - openai: cloud fallback.

    Caching avoids re-instantiating the client on every question,
    which matters especially for Ollama (connection/model handshake overhead).
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider in _LLM_CACHE:
        return _LLM_CACHE[provider]

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        llm = ChatOllama(model=model, base_url=base_url, temperature=0)

    elif provider == "groq":
        from langchain_groq import ChatGroq
        model = os.getenv("GROQ_MODEL", "qwen2.5-7b-instruct")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set but LLM_PROVIDER=groq")
        llm = ChatGroq(model=model, api_key=api_key, temperature=0)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set but LLM_PROVIDER=openai")
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

    _LLM_CACHE[provider] = llm
    return llm


def clear_llm_cache():
    """Call this if provider/model changes at runtime (e.g. Admin Settings page)."""
    _LLM_CACHE.clear()