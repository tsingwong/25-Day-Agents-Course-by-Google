"""
A2UI Web Server - 完整的 A2UI 演示服务器

功能:
1. 提供 Web 界面，实时渲染 A2UI
2. 支持 Gemini 动态生成 UI
3. 处理用户交互事件

运行:
    cd day-15
    uv run python server.py

访问:
    http://localhost:8002
"""

import os
import sys
import json
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv("../.env")

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from a2ui import A2UI, create_login_form, create_restaurant_list, create_weather_card


# ============================================================
# Gemini 集成
# ============================================================

A2UI_SCHEMA = '''你是一个 UI 生成助手，使用 A2UI 协议输出界面。

## 输出格式
输出 JSON 对象（注意：不是 JSONL，是单个 JSON），包含以下字段：
{
  "surface_id": "界面ID",
  "components": [...],
  "root": "根组件ID"
}

## 可用组件

Text: {"id": "x", "component": {"Text": {"text": {"literalString": "内容"}, "usageHint": "h1|h2|body"}}}
Button: {"id": "x", "component": {"Button": {"child": "文本ID", "action": {"name": "动作名"}, "style": "filled|outlined"}}}
TextField: {"id": "x", "component": {"TextField": {"value": {"path": "/路径"}, "labelText": {"literalString": "标签"}}}}
Column: {"id": "x", "component": {"Column": {"children": ["id1", "id2"], "spacing": 16}}}
Row: {"id": "x", "component": {"Row": {"children": ["id1", "id2"], "spacing": 8}}}
Card: {"id": "x", "component": {"Card": {"child": "内容ID", "elevation": 1}}}
Image: {"id": "x", "component": {"Image": {"source": {"literalString": "URL"}}}}
Divider: {"id": "x", "component": {"Divider": {}}}

## 规则
1. 组件 ID 唯一
2. 被引用的组件必须先定义
3. 返回有效的 JSON
'''

gemini_model = None

def init_gemini():
    global gemini_model
    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                system_instruction=A2UI_SCHEMA
            )
            print("✅ Gemini API 已配置")
        else:
            print("⚠️ 未找到 GOOGLE_API_KEY")
    except ImportError:
        print("⚠️ google-generativeai 未安装")


async def generate_ui_with_gemini(prompt: str) -> dict:
    """使用 Gemini 生成 A2UI"""
    if gemini_model is None:
        return generate_fallback_ui(prompt)

    system_prompt = """你是一个 A2UI JSON 生成器。根据用户请求生成界面描述 JSON。

规则：
1. 必须使用中文内容，不要用日语或英语
2. 必须使用 literalString 直接填充真实数据，不要用 path 数据绑定
3. 生成的内容要有真实感，比如餐厅要有具体名字、价格、评分

A2UI JSON 格式示例：
{
  "surface_id": "example",
  "components": [
    {"id": "title", "component": {"Text": {"text": {"literalString": "标题"}, "usageHint": "h1"}}},
    {"id": "btn", "component": {"Button": {"child": "btn_label", "action": {"name": "click"}, "style": "filled"}}},
    {"id": "input", "component": {"TextField": {"value": {"path": "/user/name"}, "labelText": {"literalString": "用户名"}}}},
    {"id": "col", "component": {"Column": {"children": ["title", "btn"], "spacing": 16}}},
    {"id": "card", "component": {"Card": {"child": "col", "elevation": 1}}}
  ],
  "root": "card"
}

组件类型：Text, Button, TextField, Column, Row, Card, Image, Divider, Checkbox
只返回 JSON，不要其他解释。"""

    try:
        response = await gemini_model.generate_content_async(
            f"{system_prompt}\n\n用户请求: {prompt}"
        )
        text = response.text.strip()
        # 提取 JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception as e:
        print(f"Gemini 错误: {e}")
        return generate_fallback_ui(prompt)


def generate_fallback_ui(prompt: str) -> dict:
    """降级：使用预定义模板"""
    prompt_lower = prompt.lower()

    if "登录" in prompt or "login" in prompt_lower:
        ui = create_login_form()
        return ui.to_json("card")

    elif "天气" in prompt or "weather" in prompt_lower:
        ui = create_weather_card("北京", 25, "晴天 ☀️", 45)
        return ui.to_json("card")

    elif "餐厅" in prompt or "restaurant" in prompt_lower or "美食" in prompt:
        restaurants = [
            {"name": "🍕 意大利花园", "price": 180, "rating": 4.8, "distance": "500m"},
            {"name": "🥩 牛排工坊", "price": 280, "rating": 4.5, "distance": "800m"},
            {"name": "🍝 巴黎小馆", "price": 150, "rating": 4.9, "distance": "1.2km"},
        ]
        ui = create_restaurant_list(restaurants)
        return ui.to_json("main")

    else:
        # 通用响应
        ui = (A2UI("response")
            .text("title", "🤖 AI 助手", "h1")
            .text("msg", f"收到请求: {prompt}")
            .text("hint", "试试: 登录表单、天气、餐厅推荐")
            .column("content", ["title", "msg", "hint"], gap=16)
            .card("card", "content"))
        return ui.to_json("card")


# ============================================================
# FastAPI 应用
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_gemini()
    yield

app = FastAPI(title="A2UI Demo", lifespan=lifespan)


# HTML 页面（包含 A2UI 渲染器）
HTML_PAGE = '''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>A2UI Demo - Day 15</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        header p {
            opacity: 0.9;
        }

        .input-section {
            background: white;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }

        .input-row {
            display: flex;
            gap: 10px;
        }

        #prompt-input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }

        #prompt-input:focus {
            border-color: #667eea;
        }

        #generate-btn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        #generate-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        #generate-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .quick-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }

        .quick-btn {
            padding: 8px 16px;
            background: #f5f5f5;
            border: none;
            border-radius: 20px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .quick-btn:hover {
            background: #e0e0e0;
        }

        .panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        @media (max-width: 768px) {
            .panels { grid-template-columns: 1fr; }
        }

        .panel {
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }

        .panel-header {
            background: #f8f9fa;
            padding: 15px 20px;
            font-weight: 600;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .panel-body {
            padding: 20px;
            min-height: 300px;
        }

        #json-output {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            overflow: auto;
            max-height: 400px;
            white-space: pre-wrap;
        }

        /* A2UI 组件样式 */
        .a2ui-root {
            font-family: inherit;
        }

        .a2ui-text { margin: 4px 0; }
        .a2ui-text.h1 { font-size: 1.8em; font-weight: 700; color: #1a1a1a; }
        .a2ui-text.h2 { font-size: 1.4em; font-weight: 600; color: #333; }
        .a2ui-text.h3 { font-size: 1.1em; font-weight: 600; color: #444; }
        .a2ui-text.body { font-size: 1em; color: #666; }
        .a2ui-text.caption { font-size: 0.85em; color: #888; }

        .a2ui-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            border: none;
        }

        .a2ui-button.filled {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .a2ui-button.filled:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .a2ui-button.outlined {
            background: transparent;
            border: 2px solid #667eea;
            color: #667eea;
        }

        .a2ui-button.outlined:hover {
            background: rgba(102, 126, 234, 0.1);
        }

        .a2ui-button.text {
            background: transparent;
            color: #667eea;
        }

        .a2ui-textfield {
            width: 100%;
            margin: 8px 0;
        }

        .a2ui-textfield label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #555;
            margin-bottom: 6px;
        }

        .a2ui-textfield input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.2s;
        }

        .a2ui-textfield input:focus {
            border-color: #667eea;
        }

        .a2ui-column {
            display: flex;
            flex-direction: column;
        }

        .a2ui-row {
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
        }

        .a2ui-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #eee;
        }

        .a2ui-card.elevation-2 {
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }

        .a2ui-image {
            max-width: 100%;
            border-radius: 8px;
        }

        .a2ui-divider {
            height: 1px;
            background: #e0e0e0;
            margin: 16px 0;
        }

        .a2ui-spacer {
            flex-shrink: 0;
        }

        .a2ui-container {
            border-radius: 8px;
        }

        .a2ui-checkbox {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }

        .a2ui-checkbox input {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        /* 事件日志 */
        .event-log {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            color: #0f0;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            max-width: 300px;
            max-height: 200px;
            overflow: auto;
            z-index: 1000;
        }

        .event-log h4 {
            color: white;
            margin-bottom: 10px;
        }

        .event-item {
            margin: 5px 0;
            padding: 5px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }

        .loading::after {
            content: '';
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #667eea;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
            vertical-align: middle;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎨 A2UI Demo</h1>
            <p>Day 15: Agent-to-User Interface - 让 Agent 生成动态界面</p>
        </header>

        <div class="input-section">
            <div class="input-row">
                <input type="text" id="prompt-input" placeholder="描述你想要的界面，如：登录表单、餐厅推荐、天气卡片...">
                <button id="generate-btn" onclick="generateUI()">生成 UI</button>
            </div>
            <div class="quick-actions">
                <button class="quick-btn" onclick="quickGenerate('生成一个登录表单')">🔐 登录表单</button>
                <button class="quick-btn" onclick="quickGenerate('显示附近的餐厅推荐')">🍱 餐厅推荐</button>
                <button class="quick-btn" onclick="quickGenerate('显示北京今天的天气')">🌤️ 天气卡片</button>
                <button class="quick-btn" onclick="quickGenerate('创建一个用户注册表单')">📝 注册表单</button>
                <button class="quick-btn" onclick="quickGenerate('显示一个待办事项列表')">✅ 待办列表</button>
            </div>
        </div>

        <div class="panels">
            <div class="panel">
                <div class="panel-header">
                    <span>📱</span> UI 渲染结果
                </div>
                <div class="panel-body" id="ui-output">
                    <div class="loading" style="display:none" id="loading">生成中...</div>
                    <div id="rendered-ui" class="a2ui-root">
                        <p style="color:#888; text-align:center; padding:40px;">
                            输入描述或点击快捷按钮生成 UI
                        </p>
                    </div>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <span>📦</span> A2UI JSON
                </div>
                <div class="panel-body">
                    <pre id="json-output">// A2UI JSON 将显示在这里</pre>
                </div>
            </div>
        </div>
    </div>

    <div class="event-log" id="event-log">
        <h4>📡 事件日志</h4>
        <div id="events"></div>
    </div>

    <script>
        // ============================================================
        // A2UI JavaScript 渲染器
        // ============================================================

        class A2UIRenderer {
            constructor(container) {
                this.container = container;
                this.components = {};
                this.dataModel = {};
            }

            render(uiData) {
                this.components = {};
                this.dataModel = uiData.data || {};

                // 解析组件
                for (const comp of uiData.components) {
                    this.components[comp.id] = comp.component;
                }

                // 渲染根组件
                this.container.innerHTML = '';
                const rootElement = this.renderComponent(uiData.root);
                if (rootElement) {
                    this.container.appendChild(rootElement);
                }
            }

            renderComponent(id) {
                const comp = this.components[id];
                if (!comp) return null;

                const type = Object.keys(comp)[0];
                const props = comp[type];

                switch (type) {
                    case 'Text': return this.renderText(id, props);
                    case 'Button': return this.renderButton(id, props);
                    case 'TextField': return this.renderTextField(id, props);
                    case 'Column': return this.renderColumn(id, props);
                    case 'Row': return this.renderRow(id, props);
                    case 'Card': return this.renderCard(id, props);
                    case 'Image': return this.renderImage(id, props);
                    case 'Divider': return this.renderDivider(id, props);
                    case 'Spacer': return this.renderSpacer(id, props);
                    case 'Container': return this.renderContainer(id, props);
                    case 'Checkbox': return this.renderCheckbox(id, props);
                    default:
                        console.warn(`Unknown component type: ${type}`);
                        return null;
                }
            }

            getText(textProp) {
                if (!textProp) return '';
                if (textProp.literalString) return textProp.literalString;
                if (textProp.path) {
                    // 从数据模型获取
                    const path = textProp.path.replace(/^\//, '').split('/');
                    let value = this.dataModel;
                    for (const key of path) {
                        value = value?.[key];
                    }
                    return value || `[${textProp.path}]`;
                }
                return '';
            }

            renderText(id, props) {
                const el = document.createElement('div');
                el.className = `a2ui-text ${props.usageHint || 'body'}`;
                el.textContent = this.getText(props.text);
                el.dataset.id = id;
                return el;
            }

            renderButton(id, props) {
                const btn = document.createElement('button');
                btn.className = `a2ui-button ${props.style || 'filled'}`;
                btn.dataset.id = id;

                // 获取按钮文字
                if (props.child && this.components[props.child]) {
                    const childComp = this.components[props.child];
                    if (childComp.Text) {
                        btn.textContent = this.getText(childComp.Text.text);
                    }
                }

                // 绑定事件
                btn.onclick = () => {
                    const action = props.action?.name || 'unknown';
                    this.logEvent(`Button clicked: ${action}`);
                    this.handleAction(action);
                };

                return btn;
            }

            renderTextField(id, props) {
                const wrapper = document.createElement('div');
                wrapper.className = 'a2ui-textfield';
                wrapper.dataset.id = id;

                if (props.labelText) {
                    const label = document.createElement('label');
                    label.textContent = this.getText(props.labelText);
                    wrapper.appendChild(label);
                }

                const input = document.createElement('input');
                input.type = props.value?.path?.includes('password') ? 'password' : 'text';
                input.placeholder = this.getText(props.hintText) || '';

                // 数据绑定
                if (props.value?.path) {
                    const path = props.value.path;
                    input.oninput = (e) => {
                        this.logEvent(`Input: ${path} = ${e.target.value}`);
                    };
                }

                wrapper.appendChild(input);
                return wrapper;
            }

            renderColumn(id, props) {
                const el = document.createElement('div');
                el.className = 'a2ui-column';
                el.dataset.id = id;
                el.style.gap = `${props.spacing || 8}px`;

                for (const childId of (props.children || [])) {
                    const child = this.renderComponent(childId);
                    if (child) el.appendChild(child);
                }

                return el;
            }

            renderRow(id, props) {
                const el = document.createElement('div');
                el.className = 'a2ui-row';
                el.dataset.id = id;
                el.style.gap = `${props.spacing || 8}px`;

                for (const childId of (props.children || [])) {
                    const child = this.renderComponent(childId);
                    if (child) el.appendChild(child);
                }

                return el;
            }

            renderCard(id, props) {
                const el = document.createElement('div');
                el.className = `a2ui-card elevation-${props.elevation || 1}`;
                el.dataset.id = id;

                if (props.child) {
                    const child = this.renderComponent(props.child);
                    if (child) el.appendChild(child);
                }

                return el;
            }

            renderImage(id, props) {
                const img = document.createElement('img');
                img.className = 'a2ui-image';
                img.src = this.getText(props.source);
                img.alt = this.getText(props.altText) || '';
                img.dataset.id = id;
                return img;
            }

            renderDivider(id, props) {
                const el = document.createElement('div');
                el.className = 'a2ui-divider';
                el.dataset.id = id;
                return el;
            }

            renderSpacer(id, props) {
                const el = document.createElement('div');
                el.className = 'a2ui-spacer';
                el.style.height = `${props.size || 16}px`;
                el.dataset.id = id;
                return el;
            }

            renderContainer(id, props) {
                const el = document.createElement('div');
                el.className = 'a2ui-container';
                el.dataset.id = id;
                el.style.padding = `${props.padding || 16}px`;
                if (props.backgroundColor) {
                    el.style.backgroundColor = props.backgroundColor;
                }

                if (props.child) {
                    const child = this.renderComponent(props.child);
                    if (child) el.appendChild(child);
                }

                return el;
            }

            renderCheckbox(id, props) {
                const wrapper = document.createElement('label');
                wrapper.className = 'a2ui-checkbox';
                wrapper.dataset.id = id;

                const input = document.createElement('input');
                input.type = 'checkbox';

                const labelComp = props.label && this.components[props.label];
                const labelText = labelComp?.Text ? this.getText(labelComp.Text.text) : '';

                wrapper.appendChild(input);
                wrapper.appendChild(document.createTextNode(labelText));

                input.onchange = (e) => {
                    this.logEvent(`Checkbox: ${props.value?.path} = ${e.target.checked}`);
                };

                return wrapper;
            }

            handleAction(action) {
                // 发送事件到服务器
                fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
            }

            logEvent(message) {
                const events = document.getElementById('events');
                const item = document.createElement('div');
                item.className = 'event-item';
                item.textContent = message;
                events.insertBefore(item, events.firstChild);

                // 保留最近10条
                while (events.children.length > 10) {
                    events.removeChild(events.lastChild);
                }
            }
        }

        // ============================================================
        // 页面逻辑
        // ============================================================

        const renderer = new A2UIRenderer(document.getElementById('rendered-ui'));

        async function generateUI() {
            const input = document.getElementById('prompt-input');
            const btn = document.getElementById('generate-btn');
            const loading = document.getElementById('loading');
            const output = document.getElementById('rendered-ui');
            const jsonOutput = document.getElementById('json-output');

            const prompt = input.value.trim();
            if (!prompt) return;

            btn.disabled = true;
            loading.style.display = 'block';
            output.innerHTML = '';
            output.appendChild(loading);

            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });

                const data = await response.json();

                // 显示 JSON
                jsonOutput.textContent = JSON.stringify(data, null, 2);

                // 渲染 UI
                loading.style.display = 'none';
                renderer.render(data);
                renderer.logEvent(`Generated UI: ${data.surface_id}`);

            } catch (error) {
                loading.style.display = 'none';
                output.innerHTML = `<p style="color:red;">Error: ${error.message}</p>`;
            } finally {
                btn.disabled = false;
            }
        }

        function quickGenerate(prompt) {
            document.getElementById('prompt-input').value = prompt;
            generateUI();
        }

        // 回车生成
        document.getElementById('prompt-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') generateUI();
        });
    </script>
</body>
</html>
'''


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/api/generate")
async def generate_ui(request: Request):
    """生成 A2UI"""
    data = await request.json()
    prompt = data.get("prompt", "")

    ui_data = await generate_ui_with_gemini(prompt)
    return JSONResponse(ui_data)


@app.post("/api/action")
async def handle_action(request: Request):
    """处理用户交互"""
    data = await request.json()
    action = data.get("action", "")
    print(f"📡 Action received: {action}")
    return {"status": "ok", "action": action}


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 15: A2UI Demo Server")
    print("=" * 60)
    print()
    print("🌐 访问: http://localhost:8002")
    print()
    print("功能:")
    print("  - 输入自然语言描述，生成动态 UI")
    print("  - 实时渲染 A2UI 组件")
    print("  - 查看生成的 JSON 结构")
    print()
    print("=" * 60)

    uvicorn.run(app, host="localhost", port=8002)
