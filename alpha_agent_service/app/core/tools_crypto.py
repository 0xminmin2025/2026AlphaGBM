"""
币圈工具：链上代币数据查询
用于分析Meme币、DeFi代币等
"""
import httpx
from typing import Dict, Any, Optional
from langchain_core.tools import tool


@tool
def check_chain_token(token_address: str, chain: str = "solana") -> Dict[str, Any]:
    """
    [Crypto] 查询链上代币(Meme币)的实时数据: 流动性、FDV、交易量。
    
    Args:
        token_address: 代币合约地址
        chain: 链名称 ('solana', 'ethereum', 'bsc')
    
    Returns:
        代币数据字典，或错误信息
    """
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get('pairs') or len(data['pairs']) == 0:
                return {"error": f"未找到代币 {token_address} 在 {chain} 链上的数据"}
            
            # 获取主要交易对（通常是流动性最高的）
            pair = data['pairs'][0]
            
            return {
                "name": pair.get('baseToken', {}).get('name', 'Unknown'),
                "symbol": pair.get('baseToken', {}).get('symbol', 'Unknown'),
                "price_usd": pair.get('priceUsd', '0'),
                "price_change_24h": pair.get('priceChange', {}).get('h24', '0'),
                "liquidity_usd": pair.get('liquidity', {}).get('usd', '0'),
                "fdv": pair.get('fdv', 'N/A'),  # Fully Diluted Valuation
                "volume_24h": pair.get('volume', {}).get('h24', '0'),
                "chain": chain,
                "source": "DexScreener"
            }
            
    except httpx.HTTPError as e:
        return {"error": f"HTTP请求失败: {str(e)}"}
    except Exception as e:
        return {"error": f"链上查询错误: {str(e)}"}


@tool
def get_crypto_news(limit: int = 5) -> Dict[str, Any]:
    """
    [Crypto新闻] 获取加密货币相关新闻（用于情绪分析）
    
    Args:
        limit: 返回新闻数量
    
    Returns:
        新闻列表
    """
    # 这里可以集成CryptoPanic API
    # 暂时返回提示信息
    return {
        "message": "[Crypto新闻] 功能需要配置CryptoPanic API",
        "limit": limit
    }
