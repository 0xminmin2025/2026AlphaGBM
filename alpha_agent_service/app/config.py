"""
配置管理
从环境变量加载配置
"""
import os
from dotenv import load_dotenv
from typing import List

# 加载环境变量
load_dotenv()

class Settings:
    """应用配置"""
    
    # OpenAI配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Tushare配置
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")
    
    # Supabase配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # 服务配置
    AGENT_SERVICE_PORT: int = int(os.getenv("AGENT_SERVICE_PORT", "8001"))
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:5002,http://localhost:3000").split(",")
    
    # 可选API密钥
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    CRYPTOPANIC_API_KEY: str = os.getenv("CRYPTOPANIC_API_KEY", "")
    
    # 免费用户限制
    FREE_USER_DAILY_QUOTA: int = int(os.getenv("FREE_USER_DAILY_QUOTA", "5"))
    
    @classmethod
    def validate(cls):
        """验证必要的配置"""
        required = [
            ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
            ("SUPABASE_URL", cls.SUPABASE_URL),
            ("SUPABASE_SERVICE_KEY", cls.SUPABASE_SERVICE_KEY),
        ]
        
        missing = [name for name, value in required if not value]
        if missing:
            raise ValueError(f"缺少必要的环境变量: {', '.join(missing)}")
        
        return True

settings = Settings()
