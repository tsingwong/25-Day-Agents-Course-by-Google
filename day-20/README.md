# Day 20: A2A Extensions - Sidecar 模式

## 核心概念

A2A 协议格式严格，但实际应用需要传递自定义数据。**Sidecar 模式**允许附加可选扩展，不破坏向后兼容性。

```
┌─────────────────────────────────────────────────┐
│              A2A Message                         │
├──────────────────────┬──────────────────────────┤
│   Core (必需)        │   Sidecar (可选)          │
│   - type: "task"     │   - client_id            │
│   - content: {...}   │   - state (tier 等)      │
│                      │   - signature            │
└──────────────────────┴──────────────────────────┘
```

**关键特性**: 不支持扩展的 Agent 可以安全忽略 Sidecar，不会崩溃。

## Secure Passport Extension

| 字段 | 用途 | 示例 |
|------|------|------|
| `client_id` | Agent 身份 | `a2a://travel-orchestrator.com` |
| `state` | 自定义数据 | `{"tier": "Platinum"}` |
| `signature` | 签名验证 | `"abc123..."` |

## 快速开始

```bash
cd day-20/secure-auth-agent

# 运行扩展演示
python3 app/secure_passport_ext.py
```

## 代码示例

**发送方 - 附加 Passport:**
```python
from secure_passport_ext import CallerContext, A2AMessage, add_secure_passport

passport = CallerContext(
    client_id="a2a://travel-orchestrator.com",
    state={"tier": "Platinum", "billing_code": "US-123"},
).sign()

message = A2AMessage(type="task", content="Book flight")
add_secure_passport(message, passport)
```

**接收方 - 检查 Passport:**
```python
from secure_passport_ext import get_secure_passport

passport = get_secure_passport(message)

if passport and passport.is_verified:
    print(f"✅ Verified: {passport.client_id}")
else:  # 向后兼容：无 passport 时不崩溃
    print(f"ℹ️ 标准处理流程")
```

## 文件结构

```
day-20/secure-auth-agent/
├── app/
│   ├── secure_passport_ext.py  # 扩展实现
│   └── agent.py                # Travel Agent 示例
└── pyproject.toml
```

## 参考

- [A2A Extensions 文档](https://a2a-protocol.org/latest/topics/extensions/)
- [Secure Passport 示例](https://github.com/a2aproject/a2a-samples/tree/main/extensions/secure-passport)
