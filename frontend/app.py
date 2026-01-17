
import os
import json
import chainlit as cl
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# def serialize_nodes(nodes):
#     results = []
#     for node in nodes:
#         meta = node.get("metadata", {})
#         results.append({
#             "doc_name": meta.get("doc_name"),
#             "short_name": meta.get("short_name"),
#             "article_id": meta.get("article_id"),
#             "article_title": meta.get("article_title"),
#             "chapter": meta.get("chapter"),
#             "effective_date": meta.get("effective_date"),
#             "score": node.get("score"),
#             "text": node.get("text")
#         })
#     return results

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

@cl.on_chat_start
async def start():
    """Initialize chat session with Welcome Message"""
    
    # Store session info
    cl.user_session.set("session_id", cl.user_session.get("id"))
    
    # 1. Welcome Message
    welcome_msg = """
Xin chào! Tôi là trợ lý AI chuyên về **Pháp luật Lao động Việt Nam**.
Tôi có thể giúp bạn trả lời các câu hỏi pháp lý dựa trên văn bản luật chính thức.

*(Dữ liệu được trích xuất từ văn bản gốc, có dẫn chứng Điều/Khoản cụ thể)*
"""
    await cl.Message(content=welcome_msg).send()


@cl.on_message
async def main(message: cl.Message):
    """
    Handle incoming messages and Stream response from SSE Backend
    """
    # 1. Create an empty message for streaming
    msg = cl.Message(content="")
    await msg.send()
    
    # final_answer = ""
    payload = {"content": message.content}
    
    # 2. Call Backend with httpx
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            async with client.stream("POST", f"{BACKEND_URL}/chat", json=payload) as response:
                
                if response.status_code != 200:
                    err_text = await response.aread()
                    msg.content = f"**Lỗi Server ({response.status_code}):**\n{err_text.decode()}"
                    await msg.update()
                    return

                # Local storage for accumulation
                source_nodes = []
                intent = None

                # 3. Process SSE Stream
                async for line in response.aiter_lines():
                    line = line.strip()
                    
                    # Filter for 'data:' lines
                    if not line.startswith("data:"):
                        continue
                    
                    json_str = line[5:].strip()
                    if not json_str or json_str == "[DONE]":
                        continue
                        
                    try:
                        data = json.loads(json_str)
                        
                        # Handle Errors
                        if "error" in data:
                            msg.content += f"\n\n**Lỗi:** {data['error']}"
                            await msg.update()
                            continue

                        # A. Stream Text Token
                        if "token" in data:
                            # token = data["token"]
                            # final_answer += token
                            await msg.stream_token(data["token"])
                        
                        # B. Capture Metadata
                        if "intent" in data:
                            intent = data["intent"]
                        if "nodes" in data:
                            source_nodes = data["nodes"]
                            
                    except json.JSONDecodeError:
                        continue
                
                # 4. Display Sources (After stream finishes)
                if source_nodes:
                    elements = []
                    ref_names = []
                    
                    for idx, node in enumerate(source_nodes):
                        # Extract metadata (new schema)
                        meta = node.get("metadata", {})
                        score = node.get("score", 0)
                        
                        # Get fields from new schema
                        doc_name = meta.get('doc_name', 'Văn bản pháp luật')
                        short_name = meta.get('short_name', '')
                        article_id = meta.get('article_id', '?')
                        article_title = meta.get('article_title', '')
                        chapter = meta.get('chapter', '')
                        effective_date = meta.get('effective_date', '')
                        
                        # Short display name: "Đ.80 BLLĐ" hoặc "Đ.5 NĐ145"
                        display_short = short_name if short_name else doc_name[:15]
                        ref_name = f"Đ.{article_id} {display_short}"
                        
                        # Chỉ hiển thị nội dung gốc (đã có đầy đủ metadata)
                        display_content = node.get('text', '')
                        if effective_date:
                            display_content += f"\n\n---\n*Hiệu lực: {effective_date}*"
                        
                        # Create Chainlit Text Element with SIDE display
                        elements.append(
                            cl.Text(
                                name=ref_name,
                                content=display_content,
                                display="side"  # Click để mở side panel
                            )
                        )
                        ref_names.append(ref_name)
                    
                    # Attach elements to message
                    msg.elements = elements
                    
                    # Add footer with clickable references
                    if intent == "LAW":
                        ref_links = " | ".join(ref_names)
                        await msg.stream_token(f"\n\n---\n **Căn cứ pháp lý:** {ref_links}")
                        
                    from datetime import datetime
                    import os

                    # LOG_PATH = "logs/chat_outputs.jsonl"
                    # os.makedirs("logs", exist_ok=True)

                    # record = {
                    #     "question": message.content,
                    #     "model": "LLM+RAG",  # hoặc LLM-base
                    #     "answer": final_answer.strip(),
                    #     "intent": intent,
                    #     "retrieved_nodes": serialize_nodes(source_nodes),
                    #     "timestamp": datetime.utcnow().isoformat()
                    # }

                    # with open(LOG_PATH, "a", encoding="utf-8") as f:
                    #     f.write(json.dumps(record, ensure_ascii=False) + "\n")

                await msg.update()

        except Exception as e:
            msg.content = f"**Lỗi kết nối:** {str(e)}"
            await msg.update()


# ============================================================================
# ACTIONS & CALLBACKS
# ============================================================================

@cl.action_callback("reset_memory")
async def on_reset_memory(action: cl.Action):
    """Callback to reset conversation memory via UI button (if used)"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{BACKEND_URL}/reset-memory")
            data = resp.json()
            
        if data.get("success"):
            await cl.Message(content="**Đã xóa bộ nhớ hội thoại!**").send()
        else:
            await cl.Message(content=f"**Lỗi:** {data.get('message')}").send()
            
    except Exception as e:
        await cl.Message(content=f"**Lỗi kết nối:** {str(e)}").send()

@cl.on_settings_update
async def setup_agent(settings):
    """Handle settings update"""
    pass