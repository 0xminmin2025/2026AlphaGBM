"""
LangGraph 工作流：构建智能体决策图
"""
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.prompts import ALPHA_AGENT_SYSTEM
from app.agent.state import AgentState
from app.core import (
    get_stock_metrics,
    get_stock_news,
    read_webpage_content,
    search_web_content,
    check_chain_token,
    get_crypto_news
)
from app.config import settings
import os


# 1. 绑定所有工具
ALL_TOOLS = [
    get_stock_metrics,
    get_stock_news,
    read_webpage_content,
    search_web_content,
    check_chain_token,
    get_crypto_news
]

# 2. 初始化模型
llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    api_key=settings.OPENAI_API_KEY,
    temperature=0.3  # 降低温度，使回答更专业
)
model_with_tools = llm.bind_tools(ALL_TOOLS)

# 3. 定义节点函数
def agent_node(state: AgentState) -> AgentState:
    """智能体节点：调用LLM"""
    messages = list(state['messages'])
    
    # 确保 System Prompt 永远在最前（如果还没有）
    has_system = any(isinstance(msg, SystemMessage) for msg in messages)
    if not has_system:
        messages = [SystemMessage(content=ALPHA_AGENT_SYSTEM)] + messages
    
    # 调用模型
    response = model_with_tools.invoke(messages)
    
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """判断是否继续执行工具"""
    last_msg = state['messages'][-1]
    
    # 如果最后一条消息包含工具调用，则执行工具
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "tools"
    
    return END


# 4. 构建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(ALL_TOOLS))

# 设置入口点
workflow.set_entry_point("agent")

# 添加条件边
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

# 工具执行后回到agent
workflow.add_edge("tools", "agent")

# 编译图
agent_app = workflow.compile()
