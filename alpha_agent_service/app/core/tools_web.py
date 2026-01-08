"""
网页爬虫工具：使用Crawl4AI进行深度阅读
用于分析财经新闻、财报、深度文章等
"""
import asyncio
from typing import Optional
from langchain_core.tools import tool
from crawl4ai import AsyncWebCrawler


@tool
def read_webpage_content(url: str, max_length: int = 8000) -> str:
    """
    [深度阅读] 爬取指定 URL 的网页全文，并自动转换为 Markdown。
    当用户需要分析一篇具体的财经新闻、财报或深度文章时使用。
    
    Args:
        url: 要爬取的网页URL
        max_length: 最大返回长度（防止Token溢出）
    
    Returns:
        Markdown格式的网页内容，或错误信息
    """
    async def _crawl():
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                
                if result.success:
                    # 获取Markdown内容
                    content = result.markdown or result.html
                    
                    if not content:
                        return f"无法提取网页内容: {url}"
                    
                    # 截取前 max_length 字符防止 Token 溢出
                    if len(content) > max_length:
                        content = content[:max_length] + "\n\n[内容已截断...]"
                    
                    return f"网页内容 (来源: {url}):\n\n{content}"
                else:
                    return f"爬取失败: {result.error_message or '未知错误'}"
                    
        except Exception as e:
            return f"爬取过程出错: {str(e)}"
    
    try:
        return asyncio.run(_crawl())
    except Exception as e:
        return f"执行爬取任务失败: {str(e)}"


@tool
def search_web_content(query: str, max_results: int = 3) -> str:
    """
    [网络搜索] 搜索网络上的相关信息（用于补充数据）
    
    Args:
        query: 搜索关键词
        max_results: 最大结果数
    
    Returns:
        搜索结果摘要
    """
    # 这里可以集成Perplexity API或其他搜索服务
    # 暂时返回提示信息
    return f"[搜索功能] 关键词: {query}\n注意: 网络搜索功能需要配置Perplexity API或其他搜索服务。"
