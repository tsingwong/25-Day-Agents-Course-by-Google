# Claude Code Skills 学习示例

本目录包含 Claude Code **Skills（技能）** 功能的学习示例。

## 什么是 Skills？

Skills 是 Claude Code 的扩展功能，它们是**模块化的能力包**，可以为 Claude 注入特定领域的知识和指令。

### 核心特点

| 特性 | 说明 |
|------|------|
| **自动触发** | Claude 会根据上下文自动识别并使用相关 Skill |
| **领域知识** | 为特定任务提供专业指导 |
| **可复用** | 团队共享，版本控制 |
| **轻量级** | 本质是 Markdown 文件，不是可执行代码 |

### Skills vs 其他 Claude Code 功能

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code 扩展功能                      │
├──────────────┬──────────────┬───────────────────────────────┤
│    Skills    │ Slash Cmds   │        Hooks                  │
├──────────────┼──────────────┼───────────────────────────────┤
│  自动触发    │  手动 /xxx   │   事件触发                    │
│  注入知识    │  执行工作流  │   自动化处理                  │
│  .md 文件    │  .md 文件    │   shell 脚本                  │
└──────────────┴──────────────┴───────────────────────────────┘
```

### Skills vs Agents/Agentic 开发

**这是完全不同层次的概念！**

| 维度 | Skills | Agents/Agentic |
|------|--------|----------------|
| **本质** | 提示词模板（Markdown 文件） | 自主决策的 AI 系统 |
| **执行** | 不执行代码，只注入知识 | 能调用工具、执行动作、做决策 |
| **复杂度** | 简单，几十行 Markdown | 复杂，涉及循环、工具调用、状态管理 |
| **自主性** | 无，只是增强 Claude 的知识 | 有，能自主规划和执行任务 |
| **学习成本** | 5 分钟上手 | 需要系统学习 |

#### 形象比喻

```
Skills = 给厨师一本菜谱（知识增强）
Agents = 雇一个会自己买菜、做饭、上菜的机器人厨师（自主执行）
```

#### 代码对比

**Skills（只是文本指令）**
```markdown
# SKILL.md
---
name: git-commit-helper
description: 帮助写 commit message
---
遵循 Conventional Commits 规范...
```

**Agentic 开发（自主行动的代码）**
```python
from google.adk import Agent

agent = Agent(
    model="gemini-2.0-flash",
    tools=[search_tool, code_tool, file_tool],
)

# Agent 会自主决定：搜索 → 分析 → 写代码 → 测试 → 完成
response = agent.run("帮我重构这个项目")
```

#### AI 应用开发全景图

```
┌─────────────────────────────────────────────────────┐
│                   AI 应用开发                        │
├─────────────────┬───────────────────────────────────┤
│   知识增强层     │          能力执行层               │
├─────────────────┼───────────────────────────────────┤
│    Skills       │     Agents / Agentic Systems      │
│    CLAUDE.md    │     - Tool Use (工具调用)         │
│    RAG          │     - Agentic Loop (自主循环)     │
│                 │     - Multi-Agent (多智能体)      │
│                 │     - ReAct / Planning (规划)     │
├─────────────────┴───────────────────────────────────┤
│              底层: LLM (Claude, Gemini, GPT...)     │
└─────────────────────────────────────────────────────┘
```

**总结：Skills 是 Claude Code 的小功能，Agentic 是整个 AI 开发范式。**

## 目录结构

```
skills-example/
├── README.md                          # 本文件
└── .claude/
    └── skills/                        # Skills 根目录
        ├── git-commit-helper/         # Skill 1: Git 提交助手
        │   └── SKILL.md
        ├── python-code-reviewer/      # Skill 2: Python 代码审查
        │   └── SKILL.md
        └── api-designer/              # Skill 3: API 设计助手
            └── SKILL.md
```

## SKILL.md 文件格式

每个 Skill 是一个目录，必须包含 `SKILL.md` 文件：

```markdown
---
name: skill-name              # 必需：Skill 名称
description: 简短描述         # 必需：功能描述
---

# Skill 标题

这里是 Skill 的具体指令和知识内容...
```

### 必需字段

- `name`: Skill 的唯一标识符
- `description`: 简短描述，Claude 用它来判断何时激活此 Skill

## 示例 Skills 说明

### 1. git-commit-helper

**用途**: 帮助生成符合 Conventional Commits 规范的提交信息

**触发场景**:
- "帮我写个 commit message"
- "提交这些更改"
- "生成提交信息"

### 2. python-code-reviewer

**用途**: 审查 Python 代码质量

**触发场景**:
- "审查这段代码"
- "这段 Python 代码有什么问题"
- "帮我改进代码"

### 3. api-designer

**用途**: 设计 RESTful API

**触发场景**:
- "设计一个用户 API"
- "这个 API 设计合理吗"
- "帮我规划接口"

## 如何使用

### 方法 1: 项目级 Skills

将 `.claude/skills/` 目录放在项目根目录，Skills 会对该项目生效：

```bash
your-project/
├── .claude/
│   └── skills/
│       └── your-skill/
│           └── SKILL.md
├── src/
└── ...
```

### 方法 2: 全局 Skills

放在用户目录下，对所有项目生效：

```bash
~/.claude/skills/
└── your-skill/
    └── SKILL.md
```

## 最佳实践

1. **保持 SKILL.md 简洁** - 建议不超过 500 行
2. **描述要精确** - 帮助 Claude 正确识别何时使用
3. **使用示例** - 在 Skill 中包含具体示例
4. **模块化** - 每个 Skill 专注一个领域
5. **版本控制** - 将 Skills 提交到 Git

## 进阶：多文件 Skill

对于复杂的 Skill，可以拆分为多个文件：

```
my-complex-skill/
├── SKILL.md           # 主文件，包含链接到其他文件
├── examples/          # 示例目录
│   ├── basic.md
│   └── advanced.md
├── templates/         # 模板目录
│   └── template.md
└── scripts/           # 辅助脚本
    └── helper.sh
```

在 `SKILL.md` 中通过链接引用其他文件，Claude 会按需加载。

## 参考资源

- [Agent Skills 官方文档](https://code.claude.com/docs/en/skills)
- [Claude Code 最佳实践](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Skills 深度解析](https://mikhail.io/2025/10/claude-code-skills/)
