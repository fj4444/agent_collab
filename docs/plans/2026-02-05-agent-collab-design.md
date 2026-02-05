# Agent Collab：双 Agent 协作工作流自动化工具

## 动机

在软件工程项目中，利用 Codex 和 Claude Code 协作可以产生更高质量的代码：一个负责规划和执行，另一个负责审阅。但手动在两个 agent 之间来回切换、复制粘贴上下文、协调工作流非常繁琐。

本项目旨在自动化这个协作流程，让用户专注于目标和决策，而非繁琐的操作。

## 工作流概述

```
用户 ──► 选择 Agent 细化目标 ──► Planner 写 plan.md
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
- **技术栈**：Python + Textual（AI 生态丰富，复用性好）

### 2. Agent 调用
- 通过 CLI 调用 `claude` 和 `codex` 命令
- 利用它们的 session 管理能力实现上下文延续

### 3. 角色抽象
| 角色 | 职责 | 默认实现 |
|-----|------|---------|
| Planner & Executor | 与用户细化目标、写 plan、执行代码 | Codex |
| Reviewer | 审阅 plan、提出 comments | Claude Code |

角色与具体工具解耦，通过 Adapter 模式支持替换。

### 4. 交互审批模式
- **手动模式（默认）**：每轮 agent 交互需用户审阅放行
- **自动模式**：agent 自动轮次交互，直到达成一致
- **控制机制**：
  - `[P]` 暂停自动模式，切回手动
  - `[S]` 停止当前阶段，回到目标细化
  - `[Ctrl+C]` 安全退出，保存状态

### 5. 达成一致的判定

**结构化标记规范**（写在 comments.md 首行）：
- `[APPROVED]` — 审阅通过，可进入执行阶段
- `[CHANGES_REQUIRED]` — 需要修改，继续迭代
- 无标记或其他内容 — 视为 `[CHANGES_REQUIRED]`

**迭代上限**：默认 5 轮，达到后弹出用户裁决对话框：
- 选项：强制通过 / 继续迭代 N 轮 / 手动介入编辑 / 取消任务

### 6. 持久化策略
- **优先完全持久化**：保存 state.json（阶段、session ID、迭代轮次）
- **降级机制**：session 恢复失败时，通过 prompt 注入 plan/comments 内容
- **原子写入**：先写 `.tmp` 文件再 rename，防止写入中断导致损坏

### 7. TUI 布局
- **主要 Tab**：对话、Plan、Comments
- **收起 Tab**：Log、Status（按需展开）
- **刷新机制**：文件监控（watchfiles）+ 状态变更事件驱动

### 8. Prompt 管理
- `prompts/` 目录，每阶段一个 `.md` 模板文件
- 支持变量替换（如 `{{plan_content}}`）

### 9. 测试执行
- **默认策略**：若项目根目录有 `pytest.ini`/`pyproject.toml` 则用 pytest，有 `package.json` 则用 npm test
- **Agent 可覆盖**：Planner 可自主决定其他测试方式
- **用户确认**：Agent 需要确认时，问题路由给用户

### 10. 执行阶段安全策略

**默认禁止的命令**（可在 config.toml 中调整）：
- `rm -rf`、`sudo`、`chmod 777`、`> /dev/sda` 等破坏性命令
- 检测到时暂停执行，请求用户确认

**Git commit 规则**：
- 无变更时跳过 commit
- Commit message 格式：`[Step N] <简述变更>`
- Commit 失败时记录错误，询问用户是否继续

## 目录与文件约定

所有工作流文件位于项目根目录的 `.agent-collab/` 下：

```
<project-root>/
├── .agent-collab/
│   ├── state.json        # 工作流状态
│   ├── plan.md           # 当前计划
│   ├── comments.md       # 审阅意见
│   ├── log.md            # 执行日志（增量）
│   ├── debug.log         # 调试日志（轮转，最大 10MB）
│   └── history/          # 历史存档（可选）
│       └── 2026-02-05-task-name/
└── ...
```

**并发编辑处理**：
- Agent 写入前获取文件锁（`fcntl.flock`）
- 检测到外部修改时提示用户：覆盖 / 合并 / 放弃

## 文件格式规范

### plan.md
```markdown
---
version: 1
status: draft | reviewing | approved
iteration: 2
author: planner
updated: 2026-02-05T10:30:00Z
---

# 任务：<标题>

## 目标
...

## 步骤
1. [ ] 步骤一
2. [ ] 步骤二
...
```

### comments.md
```markdown
---
status: APPROVED | CHANGES_REQUIRED
iteration: 2
author: reviewer
updated: 2026-02-05T10:35:00Z
---

[APPROVED]

或

[CHANGES_REQUIRED]

## 意见
1. ...
2. ...
```

## CLI 适配器兼容规范

### 最小接口要求
| 能力 | Codex | Claude Code |
|-----|-------|-------------|
| 启动命令 | `codex` | `claude` |
| 指定工作目录 | `--cwd <path>` | 在目录下运行 |
| Session 恢复 | `--session <id>` | `--resume` |
| 非交互输入 | stdin pipe | `--print` + stdin |
| 输出格式 | 流式文本 | 流式文本 |

### 输出解析
- 不做强格式假设
- 保留原始输出到 debug.log
- 提问检测：启发式（`?` 结尾、"请问"/"是否"/"which"/"should" 等）

## 状态机定义

```
        ┌─────────────────────────────────────────┐
        │                                         │
        ▼                                         │
     [INIT] ──► [REFINE_GOAL] ──► [WRITE_PLAN]   │
                     ▲                  │         │
                     │                  ▼         │
                     │            [REVIEW] ◄──────┤
                     │                  │         │
                     │                  ▼         │
                     │            [RESPOND] ──────┘
                     │                  │
                     │         (达成一致)│
                     │                  ▼
                     │            [APPROVED] ──► [EXECUTE] ──► [DONE]
                     │                  │              │
                     │                  │              │
                     └──────────────────┴──────────────┘
                            (用户取消/回退)

     额外状态：[CANCELLED] — 用户主动取消，清理资源
```

## 恢复流程

### 正常恢复（完全持久化）
1. 读取 `state.json`
2. 尝试用 session ID 恢复 agent 会话
3. 成功 → 继续上次中断的操作

### 降级恢复（session 失效）
1. Session 恢复失败
2. 读取 plan.md 和 comments.md 内容
3. 构造恢复 prompt：
   ```
   [系统] 这是之前的工作上下文，请继续。

   === plan.md ===
   {{plan_content}}

   === comments.md ===
   {{comments_content}}

   当前阶段：{{phase}}
   请从这里继续。
   ```
4. 以新 session 继续

### 异常退出恢复
1. 启动时检测 `state.json` 存在且 phase ≠ DONE
2. 提示用户："检测到未完成的会话，是否继续？[Y/n]"
3. 选择继续 → 执行恢复流程
4. 选择放弃 → 归档到 history/，重新开始

## 核心模块划分

```
agent-collab/
├── src/
│   ├── main.py              # 入口
│   ├── tui/                  # TUI 界面层
│   │   ├── app.py           # Textual App
│   │   ├── tabs/            # 各 Tab 组件
│   │   └── dialogs.py       # 确认/裁决对话框
│   ├── engine/              # 工作流引擎
│   │   ├── state_machine.py # 状态机
│   │   ├── approval.py      # 审批控制器
│   │   ├── safety.py        # 安全检查
│   │   └── prompt_loader.py # 模板加载
│   ├── adapters/            # Agent 适配层
│   │   ├── base.py          # 抽象基类
│   │   ├── codex.py         # Codex 适配器
│   │   └── claude.py        # Claude Code 适配器
│   └── persistence/         # 持久化
│       ├── state.py         # 状态存取
│       └── file_lock.py     # 文件锁
├── prompts/                  # Prompt 模板
│   ├── 01_refine_goal.md
│   ├── 02_write_plan.md
│   ├── 03_review_plan.md
│   ├── 04_respond_comments.md
│   ├── 05_execute_step.md
│   └── 06_recover_context.md
├── config.toml               # 用户配置
└── docs/plans/
```

## 配置文件

```toml
# config.toml

[roles]
planner = "codex"      # "codex" | "claude" | 自定义适配器
reviewer = "claude"

[workflow]
max_iterations = 5
auto_approve = false
confirm_enter = false  # Enter 放行是否需要二次确认

[safety]
blocked_commands = ["rm -rf", "sudo", "chmod 777", "> /dev/"]
require_confirm_for = ["git push", "npm publish"]

[paths]
workdir = ".agent-collab"
plan = "plan.md"
comments = "comments.md"
log = "log.md"
debug_log = "debug.log"
debug_log_max_size = "10MB"

[test]
default_command = "auto"  # "auto" | "pytest" | "npm test" | 自定义
fallback_to_agent = true  # 检测失败时让 agent 决定
```

## 实现计划

### Phase 1：核心骨架

**Step 1.1：项目初始化**
- pyproject.toml + 依赖（textual, watchfiles, tomli）
- 目录结构

**Step 1.2：Agent 适配器**
- 抽象基类 + Codex/Claude 实现
- Session 管理、输出流解析

**Step 1.3：状态机 + 持久化**
- Phase enum + 转换规则
- state.json 读写 + 原子写入

**Step 1.4：Prompt 加载器**
- 模板读取 + 变量替换

### Phase 2：TUI 界面

**Step 2.1：基础框架**
- Textual App + TabbedContent
- 文件监控刷新

**Step 2.2：交互控制**
- 快捷键绑定
- 状态栏

**Step 2.3：对话框**
- 用户裁决对话框
- 确认对话框

### Phase 3：完整工作流

**Step 3.1：目标细化 → 写 Plan**
**Step 3.2：Plan-Review 循环**
**Step 3.3：执行阶段 + 测试 + Git**

### Phase 4：健壮性

**Step 4.1：恢复流程（完全 + 降级）**
**Step 4.2：安全检查**
**Step 4.3：日志轮转**

## 代码量估算

| 模块 | 估算行数 |
|-----|---------|
| adapters/ | ~250 |
| engine/ | ~200 |
| persistence/ | ~100 |
| tui/ | ~350 |
| prompts/ | ~120 |
| **总计** | **~1020** |

## 风险与缓解

| 风险 | 缓解措施 |
|-----|---------|
| CLI 输出格式变化 | 容错解析 + 保留原始输出 |
| Session 恢复不可靠 | 降级机制 |
| 并发编辑冲突 | 文件锁 + 提示 |
| 长时间运行内存泄漏 | 限制历史长度 + 日志轮转 |
| 破坏性命令执行 | 黑名单 + 确认机制 |

## 下一步

1. 初始化项目结构和依赖
2. 实现 Phase 1 核心骨架
3. 编写基础测试
4. 迭代完善
