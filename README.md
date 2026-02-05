# Agent Collab

双 Agent 协作工作流自动化工具 —— 让 Codex 和 Claude Code 协同工作。

## 概述

Agent Collab 自动化 Planner（规划执行）和 Reviewer（审阅）两个角色之间的协作：

```
用户描述目标 → Planner 写计划 → Reviewer 审阅 → 迭代修改 → 用户批准 → 执行
```

## 安装

```bash
# 克隆项目
cd agent-collab

# 使用 uv 创建环境并安装
uv venv
uv pip install -e .
```

## 使用

### 启动

在你的项目目录下运行：

```bash
agent-collab
```

### TUI 界面

启动后会看到三个 Tab：
- **Conversation**：与 Agent 对话
- **Plan**：显示 plan.md 内容
- **Comments**：显示 comments.md（审阅意见）

### 工作流

1. **描述目标**：在输入框中描述你想实现的功能
2. **细化目标**：Planner 会提问来帮你明确需求
3. **生成计划**：输入 `/plan` 让 Planner 写计划
4. **审阅循环**：Reviewer 自动审阅，提出修改建议
5. **批准计划**：看到 `[APPROVED]` 或输入 `/approve` 强制批准
6. **执行**：输入 `/execute` 开始执行

### 命令

| 命令 | 说明 |
|------|------|
| `/plan` | 让 Planner 根据对话写计划 |
| `/approve` | 强制批准当前计划（跳过审阅） |
| `/execute` | 开始执行已批准的计划 |

### 快捷键

| 键 | 说明 |
|----|------|
| `R` | 刷新 Plan/Comments 内容 |
| `Q` | 退出 |

## 配置

项目目录下的 `config.toml`：

```toml
[roles]
planner = "codex"    # 或 "claude"
reviewer = "claude"   # 或 "codex"

[workflow]
max_iterations = 5    # Plan-Review 最大迭代次数

[paths]
workdir = ".agent-collab"
plan = "plan.md"
comments = "comments.md"
log = "log.md"
```

## 工作目录

Agent Collab 在项目根目录创建 `.agent-collab/` 存放工作流文件：

```
.agent-collab/
├── state.json    # 工作流状态（自动保存/恢复）
├── plan.md       # 当前计划
├── comments.md   # 审阅意见
└── log.md        # 执行日志
```

## 会话恢复

如果中途退出，下次启动会自动检测并恢复之前的会话。

## 前置要求

- Python 3.11+
- `codex` CLI（如果使用 Codex 作为 agent）
- `claude` CLI（如果使用 Claude Code 作为 agent）

## 开发

```bash
# 运行测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_workflow.py -v
```

## License

MIT
