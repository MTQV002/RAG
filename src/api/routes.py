"""API Routes - Chat (SSE), Query, Health"""
import json
import logging
from typing import List, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    ChatRequest, QueryRequest, QueryResponse,
    ResetMemoryResponse, HealthResponse, SourceNode
)
from src.engine.chat_engine import ChatEngineManager, get_chat_engine_manager
from src import __version__

logger = logging.getLogger("uvicorn")
router = APIRouter()


def _convert_source_nodes(source_nodes: List[Any]) -> List[SourceNode]:
    """Convert LlamaIndex nodes to API schema with deduplication by article."""
    seen = {}
    for node in source_nodes:
        meta = node.node.metadata or {}
        article_key = f"{meta.get('doc_number', '')}_{meta.get('article_id', '')}_{meta.get('chapter', '')}"
        score = node.score or 0.0
        
        if article_key not in seen or score > (seen[article_key].score or 0.0):
            seen[article_key] = node
    
    result = [
        SourceNode(
            text=node.node.get_content(),
            score=node.score,
            id=node.node.node_id,
            metadata=node.node.metadata or {}
        )
        for node in seen.values()
    ]
    result.sort(key=lambda x: x.score or 0.0, reverse=True)
    return result


@router.post("/chat")
async def chat(
    request: ChatRequest,
    engine: ChatEngineManager = Depends(get_chat_engine_manager)
):
    """Streaming Chat Endpoint (SSE)."""
    async def event_generator():
        try:
            async for text, intent, nodes in engine.astream_chat(request.content):
                payload = {}
                
                if text:
                    payload["token"] = text
                
                if intent:
                    payload["intent"] = str(intent.value) if hasattr(intent, 'value') else str(intent)
                
                if nodes:
                    converted_nodes = _convert_source_nodes(nodes)
                    payload["nodes"] = [node.model_dump() for node in converted_nodes]
                
                if payload:
                    json_data = json.dumps(payload, ensure_ascii=False)
                    yield f"data: {json_data}\n\n"
                    
        except Exception as e:
            logger.error(f"Chat Error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    engine: ChatEngineManager = Depends(get_chat_engine_manager)
):
    """Simple RAG Query (non-conversational)."""
    try:
        response = await engine.chat_engine.achat(request.question)
        return QueryResponse(
            result=str(response),
            source_nodes=_convert_source_nodes(response.source_nodes)
        )
    except Exception as e:
        logger.error(f"Query Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-memory", response_model=ResetMemoryResponse)
async def reset_memory(engine: ChatEngineManager = Depends(get_chat_engine_manager)):
    """Reset conversation memory."""
    try:
        engine.reset()
        return ResetMemoryResponse(success=True, message="Memory reset successfully")
    except Exception as e:
        return ResetMemoryResponse(success=False, message=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check."""
    try:
        engine = get_chat_engine_manager()
        status = "healthy" if engine._initialized else "initializing"
        
        components = {
            "llm": "ready" if engine.llm else "not loaded",
            "embedding": "ready" if engine.embed_model else "not loaded",
            "vector_store": "ready" if engine.vector_store else "not loaded",
        }
        
        return HealthResponse(status=status, version=__version__, components=components)
    except Exception as e:
        return HealthResponse(status="unhealthy", version=__version__, components={"error": str(e)})