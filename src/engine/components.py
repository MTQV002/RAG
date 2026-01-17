"""Engine Components Factory - LLM, Embedding, Reranker, Qdrant"""
import os
from typing import Optional
from functools import lru_cache

from llama_index.core.llms import LLM
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.postprocessor.sbert_rerank import SentenceTransformerRerank
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from llama_index.core import Settings
from qdrant_client import QdrantClient, AsyncQdrantClient

from src.config import settings


@lru_cache()
def get_llm() -> LLM:
    """Get LLM instance based on configuration (Groq/Gemini/OpenAI)."""
    debug_handler = LlamaDebugHandler(print_trace_on_end=True)
    callback_manager = CallbackManager([debug_handler])
    Settings.callback_manager = callback_manager
    if settings.LLM_PROVIDER == "groq":
        from llama_index.llms.groq import Groq
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required")
        print(f"🚀 Loading Groq LLM: {settings.llm_model}")
        llm = Groq(
            api_key=settings.GROQ_API_KEY,
            model=settings.llm_model,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            context_window=settings.LLM_CONTEXT_WINDOW,
            callback_manager=callback_manager,
        )
    elif settings.LLM_PROVIDER == "gemini":
        from llama_index.llms.gemini import Gemini
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        print(f"🤖 Loading Gemini LLM: {settings.llm_model}")
        llm = Gemini(
            api_key=settings.GEMINI_API_KEY,
            model=settings.llm_model,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    else:
        from llama_index.llms.openai import OpenAI
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        print(f"🤖 Loading OpenAI LLM: {settings.llm_model}")
        llm = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.llm_model,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    
    print("✅ LLM loaded successfully")
    return llm


@lru_cache()
def get_embed_model() -> BaseEmbedding:
    """Get Vietnamese embedding model (HuggingFace)."""
    print(f"🔤 Loading embedding model: {settings.EMBEDDING_MODEL}")
    
    cache_folder = os.path.expanduser("~/.cache/huggingface/hub")
    os.makedirs(cache_folder, exist_ok=True)
    
    embed_model = HuggingFaceEmbedding(
        model_name=settings.EMBEDDING_MODEL,
        embed_batch_size=settings.EMBEDDING_BATCH_SIZE,
        trust_remote_code=True,
        cache_folder=cache_folder,
    )
    print("✅ Embedding model loaded successfully")
    return embed_model


@lru_cache()
def get_reranker(top_n: Optional[int] = None) -> BaseNodePostprocessor:
    """Get reranker model (SentenceTransformer)."""
    top_n = top_n or settings.RERANKER_TOP_N
    print(f"🎯 Loading reranker: {settings.RERANKER_MODEL}")
    
    reranker = SentenceTransformerRerank(model=settings.RERANKER_MODEL, top_n=top_n)
    print("✅ Reranker loaded successfully")
    return reranker


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client (sync)."""
    if settings.QDRANT_API_KEY:
        print(f"☁️  Connecting to Qdrant Cloud: {settings.QDRANT_URL}")
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    else:
        print(f"🖥️  Connecting to local Qdrant: {settings.QDRANT_URL}")
        client = QdrantClient(url=settings.QDRANT_URL)
    
    print("✅ Qdrant client connected")
    return client


def get_vector_store(client=None, collection_name: Optional[str] = None) -> QdrantVectorStore:
    """Get Qdrant vector store with both sync and async clients."""
    if client is None:
        client = get_qdrant_client()
    
    if settings.QDRANT_API_KEY:
        aclient = AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    else:
        aclient = AsyncQdrantClient(url=settings.QDRANT_URL)

    collection_name = collection_name or settings.QDRANT_COLLECTION
    
    vector_store = QdrantVectorStore(
        client=client,
        aclient=aclient,
        collection_name=collection_name,
    )
    
    print(f"✅ Vector store ready: {collection_name}")
    return vector_store