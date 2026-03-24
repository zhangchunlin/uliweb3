# 技能结构指南

## 标准目录结构
```
技能名称/
├── SKILL.md              # 核心提示和说明
├── scripts/              # 可执行的 Python/Bash 脚本
├── references/           # 加载到上下文中的文档
└── assets/               # 模板和二进制文件
```

## SKILL.md 结构
1. Frontmatter (YAML 格式)
2. 简要目的说明
3. 概述
4. 先决条件
5. 指导说明
6. 输出格式
7. 错误处理
8. 示例
9. 资源

## 资源目录用途

### scripts/
- 包含可执行的 Python/Bash 脚本
- 用于复杂操作或多步骤任务
- Claude 通过 Bash 工具执行这些脚本

### references/
- 包含 Claude 可以读取到上下文中的文档
- 详细文档、检查清单或 API 模式
- 避免在 SKILL.md 中嵌入过多内容

### assets/
- 包含模板和二进制文件
- Claude 通过路径引用但不加载到上下文
- HTML 模板、CSS 文件、配置模板等
