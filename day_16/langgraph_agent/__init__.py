"""
Day 16: LangGraph Agent with A2A support

这个模块提供了:
1. 基于 LangGraph 构建的 ReAct Agent (agent.py)
2. 生产级 Human-in-the-Loop 实现 (hitl_agent.py)
3. REST API 服务 (server.py)
4. 状态持久化支持 (checkpointer.py)
"""

from .agent import create_langgraph_agent, run_langgraph, langgraph_adk_agent, app
from .hitl_agent import (
    create_hitl_graph,
    run_hitl_agent,
    resume_after_approval,
    RiskLevel,
    HITLState,
)
from .checkpointer import (
    get_checkpointer,
    get_task_store,
    TaskStore,
    TaskMetadata,
    CheckpointerType,
)

__all__ = [
    # 原有的 ReAct Agent
    "create_langgraph_agent",
    "run_langgraph",
    "langgraph_adk_agent",
    "app",
    # HITL Agent
    "create_hitl_graph",
    "run_hitl_agent",
    "resume_after_approval",
    "RiskLevel",
    "HITLState",
    # Checkpointer
    "get_checkpointer",
    "get_task_store",
    "TaskStore",
    "TaskMetadata",
    "CheckpointerType",
]
