"""
Day 5: Production Observability Demo

演示如何在 Agent 中集成 OpenTelemetry 进行可观测性监控。
这是一个简化版本，展示核心概念。

实际生产中请使用 Agent Starter Pack 的完整 telemetry 模块。
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# Span 数据结构
# ============================================================

@dataclass
class Span:
    """表示一个追踪 Span"""
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: dict = field(default_factory=dict)
    status: str = "OK"

    def end(self):
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0

    def set_attribute(self, key: str, value):
        self.attributes[key] = value

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "status": self.status
        }


# ============================================================
# 简化版 Tracer
# ============================================================

class SimpleTracer:
    """简化版追踪器，用于演示概念"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.spans: list[Span] = []
        self._current_span: Optional[Span] = None
        self._trace_id = self._generate_id()

    def _generate_id(self) -> str:
        import random
        return hex(random.getrandbits(64))[2:]

    def start_span(self, name: str) -> Span:
        """开始一个新的 Span"""
        span = Span(
            name=name,
            trace_id=self._trace_id,
            span_id=self._generate_id(),
            parent_id=self._current_span.span_id if self._current_span else None
        )
        span.set_attribute("service.name", self.service_name)
        self.spans.append(span)
        self._current_span = span
        return span

    def end_span(self, span: Span):
        """结束一个 Span"""
        span.end()
        # 恢复到父 Span
        if span.parent_id:
            for s in reversed(self.spans):
                if s.span_id == span.parent_id:
                    self._current_span = s
                    break
        else:
            self._current_span = None

    def get_trace_summary(self) -> dict:
        """获取追踪摘要"""
        return {
            "trace_id": self._trace_id,
            "service": self.service_name,
            "total_spans": len(self.spans),
            "spans": [s.to_dict() for s in self.spans]
        }


# ============================================================
# GenAI Telemetry 记录器
# ============================================================

@dataclass
class GenAITelemetryRecord:
    """GenAI 调用遥测记录"""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    status: str = "success"
    # NO_CONTENT 模式下不记录以下字段
    # prompt: str = ""
    # response: str = ""


class GenAITelemetryLogger:
    """GenAI 遥测记录器（模拟 GCS 上传）"""

    def __init__(self, bucket_name: Optional[str] = None, capture_content: str = "NO_CONTENT"):
        self.bucket_name = bucket_name
        self.capture_content = capture_content
        self.records: list[GenAITelemetryRecord] = []

        if bucket_name:
            logger.info(f"GenAI Telemetry enabled - bucket: {bucket_name}, mode: {capture_content}")
        else:
            logger.info("GenAI Telemetry disabled (no bucket configured)")

    def log_completion(self, model: str, input_tokens: int, output_tokens: int,
                       latency_ms: float, status: str = "success"):
        """记录一次 LLM 调用"""
        record = GenAITelemetryRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            status=status
        )
        self.records.append(record)

        # 模拟上传到 GCS（实际中使用 JSONL 格式）
        if self.bucket_name:
            logger.info(f"[Telemetry] {model}: {input_tokens}+{output_tokens} tokens, {latency_ms:.0f}ms")

    def export_jsonl(self) -> str:
        """导出为 JSONL 格式"""
        lines = []
        for record in self.records:
            lines.append(json.dumps(asdict(record)))
        return "\n".join(lines)

    def get_summary(self) -> dict:
        """获取统计摘要"""
        if not self.records:
            return {"total_calls": 0}

        total_input = sum(r.input_tokens for r in self.records)
        total_output = sum(r.output_tokens for r in self.records)
        avg_latency = sum(r.latency_ms for r in self.records) / len(self.records)

        return {
            "total_calls": len(self.records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "avg_latency_ms": round(avg_latency, 2)
        }


# ============================================================
# 模拟 Agent 执行
# ============================================================

class MockLLM:
    """模拟 LLM 调用"""

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model

    def generate(self, prompt: str) -> dict:
        """模拟生成响应"""
        # 模拟延迟
        time.sleep(0.1 + len(prompt) * 0.001)

        return {
            "text": f"这是对 '{prompt[:20]}...' 的回复",
            "usage": {
                "input_tokens": len(prompt) * 2,
                "output_tokens": 50 + len(prompt)
            }
        }


def simulate_agent_request(tracer: SimpleTracer, telemetry: GenAITelemetryLogger,
                           llm: MockLLM, user_input: str):
    """模拟一次 Agent 请求处理"""

    # 主 Span
    main_span = tracer.start_span("agent.handle_request")
    main_span.set_attribute("user_input_length", len(user_input))

    try:
        # 解析输入
        parse_span = tracer.start_span("agent.parse_input")
        time.sleep(0.02)  # 模拟解析
        tracer.end_span(parse_span)

        # 第一次 LLM 调用（理解意图）
        llm_span_1 = tracer.start_span("llm.generate")
        llm_span_1.set_attribute("model", llm.model)
        llm_span_1.set_attribute("purpose", "intent_understanding")

        start = time.time()
        response1 = llm.generate(f"理解用户意图: {user_input}")
        latency1 = (time.time() - start) * 1000

        llm_span_1.set_attribute("input_tokens", response1["usage"]["input_tokens"])
        llm_span_1.set_attribute("output_tokens", response1["usage"]["output_tokens"])
        tracer.end_span(llm_span_1)

        telemetry.log_completion(
            model=llm.model,
            input_tokens=response1["usage"]["input_tokens"],
            output_tokens=response1["usage"]["output_tokens"],
            latency_ms=latency1
        )

        # 工具执行
        tool_span = tracer.start_span("tool.execute")
        tool_span.set_attribute("tool_name", "search_database")
        time.sleep(0.05)  # 模拟工具执行
        tracer.end_span(tool_span)

        # 第二次 LLM 调用（生成回复）
        llm_span_2 = tracer.start_span("llm.generate")
        llm_span_2.set_attribute("model", llm.model)
        llm_span_2.set_attribute("purpose", "response_generation")

        start = time.time()
        response2 = llm.generate(f"基于搜索结果回复: {user_input}")
        latency2 = (time.time() - start) * 1000

        llm_span_2.set_attribute("input_tokens", response2["usage"]["input_tokens"])
        llm_span_2.set_attribute("output_tokens", response2["usage"]["output_tokens"])
        tracer.end_span(llm_span_2)

        telemetry.log_completion(
            model=llm.model,
            input_tokens=response2["usage"]["input_tokens"],
            output_tokens=response2["usage"]["output_tokens"],
            latency_ms=latency2
        )

        # 格式化响应
        format_span = tracer.start_span("agent.format_response")
        time.sleep(0.01)
        tracer.end_span(format_span)

        main_span.set_attribute("status", "success")

    except Exception as e:
        main_span.set_attribute("status", "error")
        main_span.set_attribute("error.message", str(e))
        main_span.status = "ERROR"

    finally:
        tracer.end_span(main_span)


# ============================================================
# 演示
# ============================================================

def main():
    print("=" * 60)
    print("Day 5: Production Observability Demo")
    print("=" * 60)
    print()

    # 初始化组件
    tracer = SimpleTracer(service_name="my-agent")
    telemetry = GenAITelemetryLogger(
        bucket_name="gs://demo-bucket/logs",  # 模拟 bucket
        capture_content="NO_CONTENT"
    )
    llm = MockLLM(model="gemini-2.0-flash")

    # 模拟多个请求
    requests = [
        "北京今天天气怎么样？",
        "帮我找一家附近评分高的西餐厅",
        "解释一下什么是 OpenTelemetry"
    ]

    print("\n📨 处理用户请求...")
    print("-" * 60)

    for req in requests:
        print(f"\n用户: {req}")
        simulate_agent_request(tracer, telemetry, llm, req)

    # 输出追踪结果
    print("\n" + "=" * 60)
    print("📊 Trace Summary (类似 Cloud Trace)")
    print("=" * 60)

    trace_data = tracer.get_trace_summary()
    print(f"\nTrace ID: {trace_data['trace_id']}")
    print(f"Service: {trace_data['service']}")
    print(f"Total Spans: {trace_data['total_spans']}")

    print("\nSpans:")
    for span in trace_data['spans']:
        indent = "  " if span['parent_id'] else ""
        print(f"{indent}├── {span['name']}: {span['duration_ms']:.1f}ms")
        for key, value in span['attributes'].items():
            if key not in ['service.name']:
                print(f"{indent}│   └── {key}: {value}")

    # 输出遥测摘要
    print("\n" + "=" * 60)
    print("📈 GenAI Telemetry Summary (类似 BigQuery 查询结果)")
    print("=" * 60)

    summary = telemetry.get_summary()
    print(f"""
Total LLM Calls: {summary['total_calls']}
Total Tokens: {summary['total_tokens']}
  - Input: {summary['total_input_tokens']}
  - Output: {summary['total_output_tokens']}
Avg Latency: {summary['avg_latency_ms']}ms
""")

    # 输出 JSONL 格式
    print("=" * 60)
    print("📄 JSONL Export (类似 GCS 日志文件)")
    print("=" * 60)
    print()
    print(telemetry.export_jsonl())
    print()

    print("=" * 60)
    print("✅ Demo 完成")
    print("=" * 60)
    print("""
实际生产中：
- Traces 导出到 Cloud Trace，可视化查看调用链
- JSONL 上传到 GCS，通过 BigQuery 外部表查询
- 可以按 model、时间、user 等维度分析 Token 消耗和延迟
""")


if __name__ == "__main__":
    main()
