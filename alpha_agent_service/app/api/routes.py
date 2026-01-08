"""
API路由：流式对话接口
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List
from app.agent.graph import agent_app
from app.api.deps import verify_agent_access, increment_usage, get_supabase
from app.agent.prompts import USER_GUIDE
from langchain_core.messages import HumanMessage, AIMessage
import json

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(
    payload: Dict[str, Any],
    user_info: dict = Depends(verify_agent_access),
    supabase_client = Depends(get_supabase)
):
    """
    流式对话接口
    
    Request Body:
        {
            "messages": [
                {"role": "user", "content": "分析一下AAPL"}
            ]
        }
    
    Returns:
        StreamingResponse: 流式返回AI回答
    """
    messages = payload.get("messages", [])
    
    if not messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")
    
    # 转换消息格式为LangChain格式
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
    
    # 增加使用计数
    await increment_usage(user_info["user_id"], supabase_client)
    
    async def event_generator():
        """生成流式事件"""
        try:
            # 使用astream_events获取流式事件
            async for event in agent_app.astream_events(
                {"messages": langchain_messages},
                version="v1"
            ):
                # 只返回聊天模型的流式输出
                if event["event"] == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # 返回SSE格式
                        yield f"data: {json.dumps({'content': chunk.content})}\n\n"
                
                # 工具调用完成时，可以发送通知
                elif event["event"] == "on_tool_end":
                    tool_name = event.get("name", "")
                    yield f"data: {json.dumps({'tool': tool_name, 'status': 'completed'})}\n\n"
            
            # 发送结束标记
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/guide")
async def get_user_guide():
    """获取用户使用指南"""
    return {"guide": USER_GUIDE}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "alpha_agent_service",
        "version": "1.0.0"
    }
