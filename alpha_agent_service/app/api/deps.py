"""
依赖注入：鉴权与收费检查
"""
from fastapi import HTTPException, Header, Depends
from typing import Optional
from supabase import create_client, Client
from app.config import settings
import os


# 初始化Supabase客户端
supabase: Optional[Client] = None

def get_supabase() -> Client:
    """获取Supabase客户端（单例）"""
    global supabase
    if supabase is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase配置缺失")
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return supabase


async def verify_agent_access(
    authorization: str = Header(..., description="Bearer Token"),
    supabase_client: Client = Depends(get_supabase)
) -> dict:
    """
    独立收费检查逻辑
    
    Args:
        authorization: Bearer Token
        supabase_client: Supabase客户端
    
    Returns:
        用户信息字典，包含user_id和权限信息
    
    Raises:
        HTTPException: 401未授权或402额度不足
    """
    # 提取Token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")
    
    try:
        # 验证Token并获取用户
        user_response = supabase_client.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = user_response.user
        user_id = user.id
        
        # 查询用户权限表（假设在profiles表中有agent相关字段）
        # 如果表结构不同，需要调整查询逻辑
        try:
            profile_response = supabase_client.table("profiles").select(
                "agent_tier, agent_daily_usage, agent_last_reset"
            ).eq("id", user_id).single().execute()
            
            profile = profile_response.data if profile_response.data else {}
        except Exception:
            # 如果profiles表不存在或查询失败，使用默认值
            profile = {
                "agent_tier": "free",
                "agent_daily_usage": 0,
                "agent_last_reset": None
            }
        
        agent_tier = profile.get("agent_tier", "free")
        daily_usage = profile.get("agent_daily_usage", 0)
        
        # 检查免费用户额度限制
        if agent_tier != "pro" and agent_tier != "plus":
            if daily_usage >= settings.FREE_USER_DAILY_QUOTA:
                raise HTTPException(
                    status_code=402,
                    detail=f"Daily quota exceeded ({daily_usage}/{settings.FREE_USER_DAILY_QUOTA}). Please upgrade to Agent Pro."
                )
        
        # 返回用户信息
        return {
            "user_id": user_id,
            "email": user.email,
            "agent_tier": agent_tier,
            "daily_usage": daily_usage
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def increment_usage(
    user_id: str,
    supabase_client: Client = Depends(get_supabase)
) -> None:
    """
    增加用户使用计数
    
    Args:
        user_id: 用户ID
        supabase_client: Supabase客户端
    """
    try:
        # 尝试使用RPC函数（如果存在）
        supabase_client.rpc("increment_agent_usage", {"user_id": user_id}).execute()
    except Exception:
        # 如果RPC不存在，直接更新表
        try:
            # 获取当前使用量
            profile = supabase_client.table("profiles").select("agent_daily_usage").eq("id", user_id).single().execute()
            current_usage = profile.data.get("agent_daily_usage", 0) if profile.data else 0
            
            # 更新使用量
            supabase_client.table("profiles").update({
                "agent_daily_usage": current_usage + 1
            }).eq("id", user_id).execute()
        except Exception as e:
            # 如果更新失败，记录日志但不中断流程
            print(f"Failed to increment usage for user {user_id}: {e}")
