# Day 18: Cloud API Registry + ADK

## 一句话理解

**Cloud API Registry = 企业级工具商店**

以前：每个开发者自己找 API、配置权限、管理工具
现在：公司统一管理，开发者直接"领取"已审批的工具

## 核心概念

### 问题：企业开发 Agent 最大的痛点是什么？

不是模型，是**工具管理**：
- 哪些 API 可以用？
- 谁有权限用？
- 怎么保证安全合规？

### 解决方案：Cloud API Registry

```
┌─────────────────────────────────────────┐
│         Cloud API Registry              │
│  (企业工具仓库 - 管理员统一管理)          │
├─────────────────────────────────────────┤
│  BigQuery Tool  ✅ 已审批               │
│  Cloud Storage  ✅ 已审批               │
│  Gmail API      ❌ 未授权               │
│  自定义内部API   ✅ 已审批               │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│         开发者的 Agent                   │
│  registry.get_tool("bigquery")          │
│  → 直接获取已配置好的工具                 │
└─────────────────────────────────────────┘
```

## 两个角色

| 角色 | 职责 |
|------|------|
| **管理员** | 在 Cloud Console 审批/管理可用工具 |
| **开发者** | 用 `ApiRegistry` 获取已审批的工具 |

## 使用步骤

### 步骤 1：管理员启用 MCP 服务

```bash
# 启用 BigQuery 的 MCP 服务
gcloud beta services mcp enable bigquery.googleapis.com \
    --project=YOUR_PROJECT_ID
```

### 步骤 2：开发者使用工具

```python
from google.adk import Agent
from google.adk.tools.google_cloud import ApiRegistry

# 1. 连接到企业的工具仓库
registry = ApiRegistry(project_id="your-project-id")

# 2. 获取已审批的工具
bq_tool = registry.get_tool("google-bigquery")

# 3. 给 Agent 装上这个工具
agent = Agent(
    model="gemini-3-pro",
    tools=[bq_tool]
)
```

就这么简单！不用自己配置 API 密钥、权限等。

## 支持的 Google Cloud 工具

| 工具 | 用途 |
|------|------|
| `google-bigquery` | 数据仓库查询 |
| `google-cloud-storage` | 文件存储 |
| `google-spanner` | 分布式数据库 |
| `google-youtube` | YouTube 数据 |
| 更多... | 持续增加中 |

## 核心优势

### 1. 统一发现
所有可用工具在一个地方，不用到处找文档

### 2. 集中治理
管理员控制谁能用什么工具，保证合规

### 3. 简化集成
开发者不用关心底层配置，拿来就用

## 与普通方式对比

### 以前（手动配置）
```python
# 需要自己处理认证、配置
from google.cloud import bigquery
client = bigquery.Client(project="xxx", credentials=xxx)
# 还要自己封装成 Agent 工具...
```

### 现在（API Registry）
```python
# 一行搞定
bq_tool = registry.get_tool("google-bigquery")
```

## 适用场景

- 企业级 Agent 开发
- 需要统一管理 API 权限
- 多团队协作开发
- 合规性要求高的项目

## 前置要求

1. Google Cloud 项目
2. 启用 Cloud API Registry
3. 配置好 `gcloud` CLI 认证

## 参考资料

- [Cloud API Registry 文档](https://docs.cloud.google.com/api-registry/docs/overview)
- [ADK Cloud API Registry 指南](https://google.github.io/adk-docs/tools/google-cloud/api-registry/)
- [Tool Governance 博客](https://cloud.google.com/blog/products/ai-machine-learning/new-enhanced-tool-governance-in-vertex-ai-agent-builder)
- [官方教程 Notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/tutorial_get_started_with_cloud_api_registry.ipynb)
