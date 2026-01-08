"""
LangGraph 状态定义
"""
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """智能体状态"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # 可以添加其他状态字段，如：
    # user_id: str
    # session_id: str
    # analysis_result: dict
