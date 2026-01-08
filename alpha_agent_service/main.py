"""
AlphaGBM 智能体服务启动入口
独立运行在8001端口，与主服务(5002)分离
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as agent_router
from app.config import settings
import uvicorn

# 验证配置（开发环境可以跳过，但会显示警告）
try:
    settings.validate()
except ValueError as e:
    print(f"⚠️  配置警告: {e}")
    print("⚠️  某些功能可能无法使用，但服务仍可启动（用于测试）")
    print("⚠️  生产环境请务必配置完整的环境变量")
    # 开发环境不退出，允许部分功能测试

# 创建FastAPI应用
app = FastAPI(
    title="AlphaGBM Agent Service",
    description="基于G=B+M模型的AI投资分析智能体",
    version="1.0.0"
)

# 配置CORS（允许主站前端跨域调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agent_router, prefix="/api/v1", tags=["agent"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "AlphaGBM Agent Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/v1/chat",
            "health": "/api/v1/health",
            "guide": "/api/v1/guide"
        }
    }


if __name__ == "__main__":
    print(f"🚀 启动 AlphaGBM 智能体服务...")
    print(f"📡 服务地址: http://0.0.0.0:{settings.AGENT_SERVICE_PORT}")
    print(f"🔗 API文档: http://0.0.0.0:{settings.AGENT_SERVICE_PORT}/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.AGENT_SERVICE_PORT,
        log_level="info"
    )
