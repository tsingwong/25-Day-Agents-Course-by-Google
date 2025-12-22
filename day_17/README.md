# Day 17: Gemini 3 Flash - 可配置思考级别

## 核心概念

Gemini 3 Flash 是 Google 最新的快速模型，最大亮点是**可配置的思考级别（Thinking Level）**。

### 什么是 Thinking Level？

简单说：控制模型"想多久"再回答。

| 级别 | 特点 | 适用场景 |
|------|------|----------|
| `MINIMAL` | 最快响应，几乎不思考 | 简单问答、聊天 |
| `LOW` | 快速响应，少量推理 | 日常任务、一般查询 |
| `MEDIUM` | 平衡模式 | 中等复杂度任务 |
| `HIGH` | 深度推理，更长思考 | 复杂问题、数学、编程 |

### 为什么重要？

1. **省钱** - 低思考级别消耗更少 token
2. **更快** - 简单任务不需要深度思考
3. **更准** - 复杂任务可以开启深度推理

## 在 ADK 中使用

```python
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types

agent = Agent(
    model='gemini-3-flash-preview',
    name='my_agent',
    instruction="你是一个有用的助手",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_level="LOW"  # 可选: MINIMAL, LOW, MEDIUM, HIGH
        )
    ),
)
```

## 关键配置

### ThinkingConfig 参数

```python
types.ThinkingConfig(
    thinking_level="HIGH"  # 思考级别
)
```

### BuiltInPlanner

- ADK 的内置规划器
- 用于配置模型的思考行为
- 通过 `thinking_config` 传入配置

## 与 Gemini 2.5 的区别

| 特性 | Gemini 2.5 | Gemini 3 |
|------|------------|----------|
| 配置参数 | `thinking_budget` | `thinking_level` |
| 控制方式 | token 预算 | 级别选择 |
| 效率 | 基准 | 平均减少 30% token |

**注意**: 参数不通用！Gemini 3 用 `thinking_level`，Gemini 2.5 用 `thinking_budget`。

## 定价

- 输入: $0.50 / 百万 token
- 输出: $3.00 / 百万 token
- 比 Gemini 3 Pro 便宜 4 倍

## 文件说明

| 文件 | 说明 |
|------|------|
| `gemini3_flash_thinking.ipynb` | 基础教程 - 思考级别入门 |
| `adaptive_thinking_demo.ipynb` | 扩展案例 - 智能客服自适应思考 |
| `thinking_demo.py` | Python 脚本版本 |

## 运行示例

```bash
# 安装依赖
pip install google-adk google-genai python-dotenv

# 设置 API Key
export GOOGLE_API_KEY=your_key_here

# 运行 Jupyter
jupyter notebook
```

## 参考资料

- [Gemini 3 Flash 官方公告](https://blog.google/products/gemini/gemini-3-flash/)
- [ADK 模型配置文档](https://google.github.io/adk-docs/agents/models/)
- [多智能体系统指南](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- [TechCrunch 报道](https://techcrunch.com/2025/12/17/google-launches-gemini-3-flash-makes-it-the-default-model-in-the-gemini-app/)
