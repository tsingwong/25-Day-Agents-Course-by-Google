---
name: git-commit-helper
description: 帮助生成规范的 Git 提交信息，遵循 Conventional Commits 规范
---

# Git Commit Helper Skill

当用户请求帮助写 commit message 或提交代码时，请遵循以下规范：

## Conventional Commits 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

## 允许的 Type

- **feat**: 新功能
- **fix**: Bug 修复
- **docs**: 文档变更
- **style**: 代码格式（不影响代码运行的变动）
- **refactor**: 重构（既不是新增功能，也不是修改 bug）
- **perf**: 性能优化
- **test**: 增加测试
- **chore**: 构建过程或辅助工具的变动
- **ci**: CI 配置变更

## 规则

1. **subject** 不超过 50 个字符
2. **subject** 使用祈使句，首字母小写，结尾不加句号
3. **body** 解释「为什么」而不是「做了什么」
4. 如果有 Breaking Change，在 footer 中注明

## 示例

```
feat(auth): add OAuth2 login support

Implement Google OAuth2 authentication to provide users
with a faster login experience.

BREAKING CHANGE: remove legacy session-based auth
```
