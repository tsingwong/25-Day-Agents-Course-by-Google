---
name: api-designer
description: 帮助设计 RESTful API，遵循最佳实践和一致的命名规范
---

# API Designer Skill

当用户请求设计 API 或讨论 API 结构时，应用此技能。

## RESTful 设计原则

### URL 命名规范

```
# 资源集合 - 复数名词
GET    /users          # 获取用户列表
POST   /users          # 创建用户

# 单个资源
GET    /users/{id}     # 获取特定用户
PUT    /users/{id}     # 更新用户（全量）
PATCH  /users/{id}     # 更新用户（部分）
DELETE /users/{id}     # 删除用户

# 嵌套资源
GET    /users/{id}/orders    # 用户的订单
```

### HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 成功的 GET/PUT/PATCH |
| 201 | Created | 成功的 POST |
| 204 | No Content | 成功的 DELETE |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 验证失败 |
| 500 | Internal Server Error | 服务器错误 |

### 响应格式

```json
{
  "data": {
    "id": "123",
    "type": "user",
    "attributes": {
      "name": "张三",
      "email": "zhang@example.com"
    }
  },
  "meta": {
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

### 分页

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

### 错误响应

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": [
      {
        "field": "email",
        "message": "邮箱格式不正确"
      }
    ]
  }
}
```

## API 文档模板

为每个端点提供：
1. **端点**: `METHOD /path`
2. **描述**: 功能说明
3. **请求参数**: Query/Path/Body 参数
4. **响应示例**: 成功和失败情况
5. **权限要求**: 需要的认证/授权
