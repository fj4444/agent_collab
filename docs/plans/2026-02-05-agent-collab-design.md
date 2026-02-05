# Agent Collab：双 Agent 协作工作流自动化工具（MVP）

## 动机

在软件工程项目中，利用 Codex 和 Claude Code 协作可以产生更高质量的代码：一个负责规划和执行，另一个负责审阅。但手动在两个 agent 之间来回切换、复制粘贴上下文、协调工作流非常繁琐。

本项目旨在自动化这个协作流程，让用户专注于目标和决策，而非繁琐的操作。

## 工作流概述

```
用户 ──► 与 Planner 细化目标 ──► Planner 写 plan.md
                                      │
         ┌────────────────────────────┘
         ▼
    Reviewer 审阅 ──► 写 comments.md
         │
         ▼
    Planner 响应 ──► 更新 plan.md 或回复 comments.md
         │
         ▼
    [循环直到 [APPROVED] 或达到迭代上限]
         │
         ▼
    用户批准 ──► Planner 逐步执行
         │
         ▼
    每步：代码修改 → 测试 → git commit → 更新 log.md
```

## 设计决策

### 1. 运行形式
- **TUI 服务**：后台服务 + Textual TUI 界面
- **技术栈**：Python + Textual

### 2. Agent 调用
- 通过 CLI 调用 `claude` 和 `codex` 命令
- 利用 session 管理实现上下文延续

### 3. 角色抽象
| 角色 | 职责 | 默认实现 |
|-----|------|---------|
| Planner & Executor | 细化目标、写 plan、执行代码 | Codex |
| Reviewer | 审阅 plan、提出 comments | Claude Code |

通过 Adapter 模式支持替换。

### 4. 交互模式
- **MVP 只做手动模式**：每轮 agent 交互需用户 `[Enter]` 放行
- 快捷键：`[Enter]` 放行、`[Q]` 退出

### 5. 达成一致的判定
- comments.md 首行写 `[APPROVED]` → 进入执行阶段
- 其他情况（含 `[CHANGES_REQUIRED]}` 或无标记）→ 继续迭代
- 迭代达到上限 → 提示用户选择：继续 / 停止

### 6. 持久化策略
- **完全持久化**：保存 state.json（阶段、session ID、迭代轮次）
- **降级机制**：session 恢复失败时，通过 prompt 注入 plan/comments 内容继续

### 7. TUI 布局
- **3 个 Tab**：对话、Plan、Comments
- 底部状态栏显示当前阶段
- 文件变化时自动刷新（watchfiles）

### 8. 测试执行
- 完全由 Planner agent 自主决定
- Agent 需要确认时，问题路由给用户

## 目录与文件约定

```
<project-root>/
└── .agent-collab/
    ├── state.json        # 工作流状态
    ├── plan.md           # 当前计划
    ├── comments.md       # 审阅意见
    └── log.md            # 执行日志（增量）
```

## 一致性判定标记

comments.md 首行必须是以下之一：
- `[APPROVED]` — 审阅通过
- `[CHANGES_REQUIRED]` — 需要修改

## 状态机

```
[INIT] → [REFINE_GOAL] → [WRITE_PLAN] → [REVIEW] ⇄ [RESPOND] → [APPROVED] → [EXECUTE] → [DONE]
```

- REVIEW ⇄ RESPOND 循环直到 `[APPROVED]` 或达到迭代上限
- 任何阶段可退出，状态保存以便下次恢复

## 恢复流程

1. 启动时检测 `state.json`
2. 若存在且 phase ≠ DONE，提示"检测到未完成会话，是否继续？[Y/n]"
3. 继续 → 尝试用 session ID 恢复 agent 会话
4. Session 恢复失败 → 读取 plan/comments 内容，注入 prompt 继续
5. 放弃 → 删除 state.json，重新开始

## 配置文件

```toml
# config.toml

[roles]
planner = "codex"      # "codex" | "claude"
reviewer = "claude"

[workflow]
max_iterations = 5

[paths]
workdir = ".agent-collab"
plan = "plan.md"
comments = "comments.md"
log = "log.md"
```

## 核心模块划分

```
agent-collab/
├── src/
│   ├── main.py              # 入口
│   ├── tui/
│   │   ├── app.py           # Textual App
│   │   └── tabs.py          # Tab 组件
│   ├── engine/
│   │   ├── state_machine.py # 状态机
│   │   └── prompt_loader.py # 模板加载
│   ├── adapters/
│   │   ├── base.py          # 抽象基类
│   │   ├── codex.py         # Codex 适配器
│   │   └── claude.py        # Claude 适配器
│   └── persistence/
│       └── state.py         # 状态存取
├── prompts/
│   ├── 01_refine_goal.md
│   ├── 02_write_plan.md
│   ├── 03_review_plan.md
│   ├── 04_respond_comments.md
│   ├── 05_execute_step.md
│   └── 06_recover_context.md
├── config.toml
└── pyproject.toml
```

## 实现计划

### Phase 1：核心骨架

**Step 1.1：项目初始化**
- 创建 pyproject.toml，依赖：textual, watchfiles, tomli
- 创建目录结构

**Step 1.2：配置加载**
- 读取 config.toml
- 提供默认值

**Step 1.3：Agent 适配器**
- 抽象基类：send(), resume_session(), get_session_id()
- CodexAdapter：调用 `codex` CLI
- ClaudeAdapter：调用 `claude` CLI

**Step 1.4：状态机 + 持久化**
- Phase enum
- state.json 读写（原子写入）
- 恢复逻辑

**Step 1.5：Prompt 加载器**
- 读取 prompts/*.md
- `{{variable}}` 替换

### Phase 2：TUI 界面

**Step 2.1：基础框架**
- Textual App + TabbedContent（3 Tab）
- 文件监控刷新

**Step 2.2：交互控制**
- Enter 放行
- Q 退出
- 状态栏

### Phase 3：完整工作流

**Step 3.1：目标细化 → 写 Plan**
- 用户与 Planner 对话
- 用户发送 `/plan` 进入写 plan 阶段

**Step 3.2：Plan-Review 循环**
- Planner 写 plan.md
- Reviewer 读 plan，写 comments.md
- 检测 `[APPROVED]` 标记
- 每轮等待用户 Enter

**Step 3.3：执行阶段**
- 逐步执行 plan
- 每步完成后：测试 → git commit → 更新 log.md

## 代码量估算

| 模块 | 估算行数 |
|-----|---------|
| adapters/ | ~150 |
| engine/ | ~100 |
| persistence/ | ~60 |
| tui/ | ~200 |
| **总计** | **~510** |

## MVP 不做的功能（留待后续）

- 自动模式（agent 自动轮次交互）
- 安全策略（危险命令检测）
- 文件锁 / 并发编辑处理
- YAML front-matter 元数据
- 日志轮转
- 历史归档
- 复杂裁决对话框

## 下一步

1. 初始化项目结构和依赖
2. 实现 Phase 1
3. 实现 Phase 2
4. 实现 Phase 3
5. 端到端测试
