# Day 5: Production Observability - 生产级可观测性

## 凌晨 3 点的噩梦

你的 Agent 上线了，用户反馈"有时候回答很慢"、"偶尔答非所问"。

你打开日志，看到的是：

```
INFO: Request received
INFO: Response sent
INFO: Request received
INFO: Response sent
```

这能告诉你什么？什么都没有。

- 哪个请求慢？慢在哪里？
- LLM 调用了几次？每次花了多久？
- Token 消耗多少？成本怎么样？
- 用户问了什么？Agent 答了什么？

## 生产环境需要的是可观测性

Agent Starter Pack 提供了两层可观测性：

| 层级 | 内容 | 导出目标 | 默认状态 |
|------|------|----------|----------|
| **Agent Telemetry** | 执行追踪、延迟、系统指标 | Cloud Trace | 始终开启 |
| **Prompt-Response Logging** | LLM 交互、Token 使用 | GCS + BigQuery + Cloud Logging | 部署环境开启 |

## 快速开始

### 1. 创建 Agent 项目

```bash
# 使用 agent-starter-pack 创建项目
uvx agent-starter-pack create

# 选择 adk_base 模板
```

### 2. 本地运行（Telemetry 自动配置）

```bash
cd your-agent-project
make playground
```

### 3. 部署到 Cloud Run（完整可观测性）

```bash
gcloud config set project YOUR_PROJECT_ID
make deploy
```

部署后，Terraform 会自动配置：
- Cloud Trace 分布式追踪
- GCS 存储 JSONL 日志
- BigQuery 外部表（SQL 查询日志）
- Cloud Logging 专用 bucket

## 核心概念

### OpenTelemetry 追踪

```
用户请求
    │
    ▼
┌─────────────────────────────────────────────┐
│  Span: handle_request (总耗时 2.5s)          │
│  ├── Span: parse_input (50ms)               │
│  ├── Span: llm_call_1 (800ms)               │
│  │      └── model: gemini-2.0-flash         │
│  │      └── tokens: 1500                    │
│  ├── Span: tool_execution (600ms)           │
│  │      └── tool: search_database           │
│  ├── Span: llm_call_2 (900ms)               │
│  │      └── model: gemini-2.0-flash         │
│  │      └── tokens: 2000                    │
│  └── Span: format_response (150ms)          │
└─────────────────────────────────────────────┘
```

每个 Span 记录：
- 开始/结束时间
- 父子关系
- 自定义属性（model、tokens 等）
- 错误信息

### 隐私保护模式

默认使用 `NO_CONTENT` 模式，只记录元数据：

```python
# 记录的内容
{
    "model": "gemini-2.0-flash",
    "input_tokens": 1500,
    "output_tokens": 500,
    "latency_ms": 800,
    "timestamp": "2025-01-15T10:30:00Z"
}

# 不记录
# - 用户的 prompt
# - LLM 的 response
```

这样既能监控性能，又保护用户隐私。

## 代码示例

### 基础 Telemetry 配置

```python
# app_utils/telemetry.py
import os
import logging

def setup_telemetry() -> str | None:
    """配置 OpenTelemetry 和 GenAI 遥测"""

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )

    if bucket and capture_content != "false":
        logging.info("Prompt-response logging enabled - mode: NO_CONTENT")

        # 设置为 NO_CONTENT 模式（只记录元数据）
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")

        # 配置上传路径
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logging.info("Prompt-response logging disabled")

    return bucket
```

### 自定义 Span 添加

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_request(request):
    with tracer.start_as_current_span("process_request") as span:
        # 添加自定义属性
        span.set_attribute("user_id", request.user_id)
        span.set_attribute("request_type", request.type)

        # 调用 LLM
        with tracer.start_as_current_span("llm_call") as llm_span:
            response = await model.generate(request.prompt)
            llm_span.set_attribute("model", "gemini-2.0-flash")
            llm_span.set_attribute("tokens", response.usage.total_tokens)

        return response
```

### 查询 BigQuery 日志

```sql
-- 查询过去 24 小时的 LLM 调用统计
SELECT
    DATE(timestamp) as date,
    model,
    COUNT(*) as calls,
    AVG(latency_ms) as avg_latency,
    SUM(input_tokens + output_tokens) as total_tokens
FROM `your-project.telemetry.genai_logs`
WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY date, model
ORDER BY date DESC, calls DESC
```

## 环境配置

### 本地开发

```bash
# .env 文件
GOOGLE_CLOUD_PROJECT=your-project-id

# 可选：启用本地 prompt-response 日志
LOGS_BUCKET_NAME=gs://your-bucket
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT
```

### 生产环境（Terraform 自动配置）

```hcl
# 环境变量由 Terraform 自动设置
resource "google_cloud_run_service" "agent" {
  template {
    spec {
      containers {
        env {
          name  = "LOGS_BUCKET_NAME"
          value = google_storage_bucket.logs.name
        }
        env {
          name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
          value = "NO_CONTENT"
        }
      }
    }
  }
}
```

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent 应用                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              OpenTelemetry SDK                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Traces    │  │   Metrics   │  │    Logs     │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │  │
│  └─────────┼────────────────┼────────────────┼─────────┘  │
└────────────┼────────────────┼────────────────┼────────────┘
             │                │                │
             ▼                ▼                ▼
     ┌───────────┐    ┌───────────┐    ┌───────────────┐
     │Cloud Trace│    │Cloud      │    │Cloud Logging  │
     │           │    │Monitoring │    │(10年保留)      │
     └───────────┘    └───────────┘    └───────┬───────┘
                                               │
                                               ▼
                                       ┌───────────────┐
                                       │     GCS       │
                                       │  (JSONL)      │
                                       └───────┬───────┘
                                               │
                                               ▼
                                       ┌───────────────┐
                                       │   BigQuery    │
                                       │ (外部表/SQL)   │
                                       └───────────────┘
```

## 验证部署

### 1. 检查 Cloud Trace

```bash
# 打开 Cloud Trace 控制台
open "https://console.cloud.google.com/traces/list?project=YOUR_PROJECT_ID"
```

### 2. 检查 GCS 日志

```bash
# 列出日志文件
gsutil ls gs://YOUR_BUCKET/completions/

# 查看日志内容
gsutil cat gs://YOUR_BUCKET/completions/2025/01/15/12/completions_*.jsonl | head -5
```

### 3. BigQuery 查询

```bash
# 运行测试查询
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) as total_calls FROM `your-project.telemetry.genai_logs`'
```

## 常见问题

### Q: 本地开发时看不到日志？

本地开发默认禁用 prompt-response 日志，只有 Cloud Trace 开启。如需启用：

```bash
export LOGS_BUCKET_NAME=gs://your-bucket
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT
```

### Q: LangGraph 模板支持吗？

LangGraph 模板只支持 Agent Telemetry（Cloud Trace），不支持 Prompt-Response Logging，因为 SDK 限制。

### Q: 如何记录完整的 prompt/response？

将环境变量改为 `ALL`（注意隐私合规）：

```bash
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=ALL
```

## 核心价值

| 没有可观测性 | 有可观测性 |
|-------------|-----------|
| "用户说慢" → 不知道哪里慢 | 精确定位到某次 LLM 调用耗时 3s |
| "成本超支" → 不知道哪里花的 | Token 使用量按 model/user/time 统计 |
| "有时出错" → 无法复现 | 追踪链完整记录每一步 |

**生产环境的 Agent，可观测性不是可选项，而是必需品。**

## 扩展阅读

- [Observability Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/observability.html)
- [Agent Starter Pack GitHub](https://github.com/GoogleCloudPlatform/agent-starter-pack)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Cloud Trace 文档](https://cloud.google.com/trace/docs)
