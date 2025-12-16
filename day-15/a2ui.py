"""
A2UI Python SDK - Agent-to-User Interface 生成器

这个模块提供了生成 A2UI JSONL 的 Python API。
A2UI 是 Google 推出的声明式 UI 协议，让 Agent 能安全地生成动态界面。
"""

import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field


@dataclass
class A2UIComponent:
    """A2UI 组件"""
    id: str
    type: str
    props: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "component": {self.type: self.props}
        }


class A2UI:
    """
    A2UI 消息构建器

    使用链式 API 构建 A2UI JSONL 消息。

    示例:
        ui = A2UI("my-surface")
        ui.text("title", "Hello World", "h1")
        ui.button("btn", "Click Me", "on_click")
        ui.column("main", ["title", "btn"])
        print(ui.build("main"))
    """

    def __init__(self, surface_id: str):
        self.surface_id = surface_id
        self.components: List[A2UIComponent] = []
        self.data: Dict[str, Any] = {}

    # ========== 基础组件 ==========

    def text(self, id: str, content: str, hint: str = "body") -> 'A2UI':
        """
        添加文本组件

        Args:
            id: 组件唯一标识
            content: 文本内容
            hint: 用途提示 (h1, h2, h3, body, caption)
        """
        self.components.append(A2UIComponent(
            id=id,
            type="Text",
            props={
                "text": {"literalString": content},
                "usageHint": hint
            }
        ))
        return self

    def text_binding(self, id: str, path: str, hint: str = "body") -> 'A2UI':
        """添加数据绑定的文本"""
        self.components.append(A2UIComponent(
            id=id,
            type="Text",
            props={
                "text": {"path": path},
                "usageHint": hint
            }
        ))
        return self

    def button(self, id: str, label: str, action: str, style: str = "filled") -> 'A2UI':
        """
        添加按钮组件

        Args:
            id: 组件唯一标识
            label: 按钮文字
            action: 点击时触发的动作名
            style: 按钮样式 (filled, outlined, text)
        """
        label_id = f"{id}__label"
        self.text(label_id, label)
        self.components.append(A2UIComponent(
            id=id,
            type="Button",
            props={
                "child": label_id,
                "action": {"name": action},
                "style": style
            }
        ))
        return self

    def text_field(self, id: str, path: str, label: str = "",
                   placeholder: str = "", multiline: bool = False) -> 'A2UI':
        """
        添加文本输入框

        Args:
            id: 组件唯一标识
            path: 数据绑定路径 (如 /user/name)
            label: 标签文字
            placeholder: 占位符
            multiline: 是否多行
        """
        props = {"value": {"path": path}}
        if label:
            props["labelText"] = {"literalString": label}
        if placeholder:
            props["hintText"] = {"literalString": placeholder}
        if multiline:
            props["maxLines"] = 5

        self.components.append(A2UIComponent(id=id, type="TextField", props=props))
        return self

    def checkbox(self, id: str, path: str, label: str) -> 'A2UI':
        """添加复选框"""
        label_id = f"{id}__label"
        self.text(label_id, label)
        self.components.append(A2UIComponent(
            id=id,
            type="Checkbox",
            props={
                "value": {"path": path},
                "label": label_id
            }
        ))
        return self

    def image(self, id: str, url: str, alt: str = "") -> 'A2UI':
        """添加图片"""
        props = {"source": {"literalString": url}}
        if alt:
            props["altText"] = {"literalString": alt}
        self.components.append(A2UIComponent(id=id, type="Image", props=props))
        return self

    def divider(self, id: str) -> 'A2UI':
        """添加分隔线"""
        self.components.append(A2UIComponent(id=id, type="Divider", props={}))
        return self

    def spacer(self, id: str, size: int = 16) -> 'A2UI':
        """添加间距"""
        self.components.append(A2UIComponent(
            id=id,
            type="Spacer",
            props={"size": size}
        ))
        return self

    # ========== 布局组件 ==========

    def column(self, id: str, children: List[str],
               align: str = "start", gap: int = 8) -> 'A2UI':
        """
        垂直布局容器

        Args:
            id: 组件唯一标识
            children: 子组件 ID 列表
            align: 对齐方式 (start, center, end, stretch)
            gap: 子组件间距
        """
        self.components.append(A2UIComponent(
            id=id,
            type="Column",
            props={
                "children": children,
                "mainAxisAlignment": align,
                "spacing": gap
            }
        ))
        return self

    def row(self, id: str, children: List[str],
            align: str = "start", gap: int = 8) -> 'A2UI':
        """水平布局容器"""
        self.components.append(A2UIComponent(
            id=id,
            type="Row",
            props={
                "children": children,
                "mainAxisAlignment": align,
                "spacing": gap
            }
        ))
        return self

    def card(self, id: str, child: str, elevation: int = 1) -> 'A2UI':
        """卡片容器"""
        self.components.append(A2UIComponent(
            id=id,
            type="Card",
            props={
                "child": child,
                "elevation": elevation
            }
        ))
        return self

    def container(self, id: str, child: str,
                  padding: int = 16,
                  background: str = None) -> 'A2UI':
        """通用容器"""
        props = {
            "child": child,
            "padding": padding
        }
        if background:
            props["backgroundColor"] = background
        self.components.append(A2UIComponent(id=id, type="Container", props=props))
        return self

    # ========== 数据 ==========

    def set_data(self, path: str, value: Any) -> 'A2UI':
        """
        设置数据模型

        Args:
            path: 数据路径 (如 "user" 或 "user.name")
            value: 数据值 (字符串、数字或字典)
        """
        self.data[path] = value
        return self

    # ========== 生成 ==========

    def build(self, root_id: str) -> str:
        """
        生成 A2UI JSONL

        Args:
            root_id: 根组件 ID

        Returns:
            JSONL 格式的字符串，每行一个 JSON 对象
        """
        lines = []

        # 1. surfaceUpdate
        lines.append(json.dumps({
            "surfaceUpdate": {
                "surfaceId": self.surface_id,
                "components": [c.to_dict() for c in self.components]
            }
        }, ensure_ascii=False))

        # 2. dataModelUpdate (可选)
        if self.data:
            contents = []
            for key, value in self.data.items():
                if isinstance(value, dict):
                    contents.append({
                        "key": key,
                        "valueMap": [
                            {"key": k, "valueString": str(v)}
                            for k, v in value.items()
                        ]
                    })
                else:
                    contents.append({"key": key, "valueString": str(value)})

            lines.append(json.dumps({
                "dataModelUpdate": {
                    "surfaceId": self.surface_id,
                    "contents": contents
                }
            }, ensure_ascii=False))

        # 3. beginRendering
        lines.append(json.dumps({
            "beginRendering": {
                "surfaceId": self.surface_id,
                "root": root_id
            }
        }, ensure_ascii=False))

        return "\n".join(lines)

    def to_json(self, root_id: str) -> Dict:
        """返回结构化的 JSON 对象（用于 API 响应）"""
        return {
            "surface_id": self.surface_id,
            "components": [c.to_dict() for c in self.components],
            "data": self.data,
            "root": root_id
        }


# ========== 便捷工厂函数 ==========

def create_login_form() -> A2UI:
    """创建登录表单"""
    return (A2UI("login")
        .text("title", "用户登录", "h1")
        .text_field("username", "/user/username", "用户名", "请输入用户名")
        .text_field("password", "/user/password", "密码", "请输入密码")
        .button("submit", "登录", "submit_login")
        .column("form", ["title", "username", "password", "submit"], gap=16)
        .card("card", "form"))


def create_restaurant_list(restaurants: List[Dict]) -> A2UI:
    """创建餐厅列表"""
    ui = A2UI("restaurants")
    ui.text("title", "🍱 附近的餐厅", "h1")

    cards = []
    for i, r in enumerate(restaurants):
        prefix = f"r{i}"
        ui.text(f"{prefix}-name", r.get("name", ""), "h2")
        ui.text(f"{prefix}-info", f"¥{r.get('price', 0)} · ★{r.get('rating', 0)} · {r.get('distance', '')}")
        ui.button(f"{prefix}-view", "查看", f"view_{i}", "outlined")
        ui.button(f"{prefix}-book", "预订", f"book_{i}", "filled")
        ui.row(f"{prefix}-actions", [f"{prefix}-view", f"{prefix}-book"], gap=8)
        ui.column(f"{prefix}-content", [f"{prefix}-name", f"{prefix}-info", f"{prefix}-actions"], gap=8)
        ui.card(f"{prefix}-card", f"{prefix}-content")
        cards.append(f"{prefix}-card")

    ui.column("list", cards, gap=16)
    ui.column("main", ["title", "list"], gap=24)
    return ui


def create_weather_card(city: str, temp: int, condition: str, humidity: int) -> A2UI:
    """创建天气卡片"""
    return (A2UI("weather")
        .text("title", f"🌤️ {city}天气", "h1")
        .text("temp", f"{temp}°C", "h2")
        .text("condition", condition)
        .text("humidity", f"湿度 {humidity}%")
        .button("refresh", "刷新", "refresh_weather", "outlined")
        .column("info", ["title", "temp", "condition", "humidity", "refresh"], gap=12)
        .card("card", "info"))


# ========== 测试 ==========

if __name__ == "__main__":
    # 测试餐厅列表
    restaurants = [
        {"name": "意大利花园", "price": 180, "rating": 4.8, "distance": "500m"},
        {"name": "牛排工坊", "price": 280, "rating": 4.5, "distance": "800m"},
        {"name": "巴黎小馆", "price": 150, "rating": 4.9, "distance": "1.2km"},
    ]

    ui = create_restaurant_list(restaurants)
    print("=== A2UI JSONL ===")
    print(ui.build("main"))
