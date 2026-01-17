"""FastAPI Main Application - Vietnam Labor Law RAG v3"""
import os
import sys
import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from llama_index.core.schema import TextNode

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import __version__
from src.config import settings
from src.api.routes import router
from src.engine.chat_engine import ChatEngineManager, set_chat_engine_manager


def setup_phoenix_tracing():
    """Setup Arize Phoenix for observability."""
    if not settings.ENABLE_TRACING:
        print("📊 Tracing disabled")
        return
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
        
        endpoint = settings.PHOENIX_COLLECTOR_ENDPOINT or "http://localhost:6006/v1/traces"
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)
        
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        LlamaIndexInstrumentor().instrument()
        
        print(f"📊 Phoenix tracing enabled: {endpoint}")
    except ImportError as e:
        print(f"⚠️ Phoenix tracing not available: {e}")
    except Exception as e:
        print(f"⚠️ Phoenix tracing setup failed: {e}")


def load_nodes_from_qdrant() -> List[TextNode]:
    """Load all nodes from Qdrant for BM25 index."""
    print("📚 Loading nodes from Qdrant for BM25 index...")
    
    try:
        if settings.QDRANT_API_KEY:
            client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
        else:
            client = QdrantClient(url=settings.QDRANT_URL)
        
        collections = [c.name for c in client.get_collections().collections]
        if settings.QDRANT_COLLECTION not in collections:
            print(f"⚠️ Collection '{settings.QDRANT_COLLECTION}' not found")
            return []
        
        points = []
        offset = None
        
        while True:
            result = client.scroll(
                collection_name=settings.QDRANT_COLLECTION,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            batch_points, offset = result
            points.extend(batch_points)
            if offset is None:
                break
        
        print(f"📄 Loaded {len(points)} points from Qdrant")
        
        nodes = []
        for i, point in enumerate(points):
            payload = point.payload or {}
            text = payload.get('text') or payload.get('_node_content') or ""
            
            if isinstance(text, str) and text.startswith('{'):
                try:
                    content_data = json.loads(text)
                    text = content_data.get('text', text)
                except:
                    pass
            
            if not text:
                continue
            
            metadata = {
                'doc_type': payload.get('doc_type', ''),
                'doc_number': payload.get('doc_number', ''),
                'doc_name': payload.get('doc_name', ''),
                'short_name': payload.get('short_name', ''),
                'chapter': payload.get('chapter', ''),
                'article_id': payload.get('article_id', ''),
                'article_title': payload.get('article_title', ''),
                'effective_date': payload.get('effective_date', ''),
                'status': payload.get('status', ''),
                'references': payload.get('references', '[]'),
            }
            
            nodes.append(TextNode(
                text=text,
                metadata=metadata,
                id_=str(point.id) if point.id else f"node_{i}"
            ))
        
        print(f"✅ Created {len(nodes)} TextNodes for BM25")
        return nodes
        
    except Exception as e:
        print(f"⚠️ Failed to load nodes: {e}")
        return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler."""
    print("=" * 60)
    print("🚀 RAG v3 - Vietnam Labor Law Assistant")
    print(f"   Version: {__version__}")
    print("=" * 60)
    
    print("\n📦 Starting up...")
    setup_phoenix_tracing()
    
    nodes = load_nodes_from_qdrant()
    
    print("\n🔧 Initializing Chat Engine...")
    engine = ChatEngineManager(nodes=nodes)
    engine.initialize()
    set_chat_engine_manager(engine)
    
    print("\n✅ Server ready!")
    print(f"   API: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"   Docs: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print("=" * 60)
    
    yield
    
    print("\n👋 Shutting down...")
    print("✅ Cleanup complete")


app = FastAPI(
    title="Vietnam Labor Law RAG v3",
    description="""
🏛️ **Vietnam Labor Law QA System**

- 🤖 Semantic Intent Routing (CHAT vs LAW)
- 💬 Conversational Memory
- 🔍 Hybrid Search (Vector + BM25 + RRF)
- 🎯 BGE Reranker
    """,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "Vietnam Labor Law RAG v3",
        "version": __version__,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
