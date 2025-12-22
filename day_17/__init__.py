"""
Day 17: Gemini 3 Flash - 可配置思考级别

学习要点:
1. ThinkingConfig 配置思考级别
2. BuiltInPlanner 内置规划器
3. 不同级别的使用场景
"""

from .thinking_demo import (
    create_agent,
    agent_minimal,
    agent_low,
    agent_high,
)

__all__ = [
    "create_agent",
    "agent_minimal",
    "agent_low",
    "agent_high",
]
