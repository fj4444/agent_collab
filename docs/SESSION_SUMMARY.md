# Agent Collab 实现经验总结

> 本文档记录 2026-02-05 session 的设计讨论、实现决策和经验总结，供后续 session 参考。

## 项目背景

### 动机

用户在软件工程项目中发现了一个有价值的工作流：让 Codex 和 Claude Code 协作，一个负责规划和执行，另一个负责审阅。但手动在两个 agent 之间切换、复制粘贴上下文非常繁琐。

**核心痛点**：
- 手动切换 agent 窗口
- 重复复制 plan/comments 内容
- 难以追踪迭代状态
- 中断后难以恢复

### 目标

构建一个自动化工具，让用户专注于目标和决策，而非繁琐的操作。

## 设计讨论过程

### Brainstorming 阶段

我们通过一系列问题逐步明确需求：

| 问题 | 用户选择 | 原因 |
|-----|---------|------|
| 运行形式 | TUI 服务 | 比 CLI 脚本更直观，可实时查看状态 |
| Agent 调用方式 | 通过 CLI | 利用现有工具的 session 管理能力 |
| 技术栈 | Python + Textual | AI 生态丰富，复用性好 |
| 交互模式 | 手动为主 | 用户希望了解每一步发生什么 |
| 持久化策略 | 完全持久化 | 支持中断恢复，session ID + 降级方案 |
| 项目管理 | 单项目 | MVP 简化，以后可扩展 |

### 角色抽象

一个关键设计决策是将角色与具体工具分离：

```
┌─────────────────────┐     ┌─────────────────────┐
│ Planner & Executor  │     │      Reviewer       │
│       (角色)         │     │       (角色)        │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
    ┌──────▼──────┐             ┌──────▼──────┐
    │   Adapter   │             │   Adapter   │
    └──────┬──────┘             └──────┬──────┘
           │                           │
   ┌───────▼───────┐           ┌───────▼───────┐
   │ Codex (默认)   │           │ Claude (默认) │
   └───────────────┘           └───────────────┘
```

**为什么这样设计**：
- 用户可能想交换角色（Claude 写 plan，Codex 审阅）
- 未来可能支持其他模型（GPT-4、Gemini、本地模型）
- 解耦使测试更容易

### Plan-Review 循环

审阅意见如何判定"达成一致"是一个关键问题。我们选择了**结构化标记**：

```
comments.md 首行必须是：
- [APPROVED] — 通过
- [CHANGES_REQUIRED] — 需要修改
```

**为什么不用启发式判断**（如"同意性语句"）：
- LLM 输出不可控，容易误判
- 明确标记让逻辑简单可靠
- 降低实现复杂度

### MVP 精简

第一版设计过于复杂（~1020 行），经过 Reviewer 审阅后精简为 MVP：

**保留**：
- 完全持久化（用户强调）
- config.toml 配置（用户强调）
- 手动模式
- 3 Tab TUI

**删除**：
- 自动模式（agent 自动轮次）
- 安全策略（危险命令检测）
- 文件锁
- YAML front-matter
- 日志轮转
- 历史归档

**经验**：MVP 应该只包含验证核心价值的最小功能集。

## 实现细节

### 架构分层

```
src/agent_collab/
├── adapters/        # CLI 调用层
│   ├── base.py      # 抽象基类
│   ├── codex.py     # Codex 适配器
│   ├── claude.py    # Claude 适配器
│   └── factory.py   # 工厂函数
├── engine/          # 业务逻辑层
│   ├── state_machine.py  # 状态机
│   ├── prompt_loader.py  # 模板加载
│   └── workflow.py       # 工作流控制器
├── persistence/     # 持久化层
│   └── state.py     # 状态存取
├── tui/             # 界面层
│   └── app.py       # Textual 应用
├── config.py        # 配置加载
└── main.py          # 入口
```

### 关键实现点

#### 1. Agent 适配器

```python
class AgentAdapter(ABC):
    @abstractmethod
    async def send(self, prompt: str) -> AsyncIterator[str]: ...
    @abstractmethod
    async def resume_session(self, session_id: str) -> bool: ...
```

- 使用 `asyncio.subprocess` 调用 CLI
- 流式输出（yield chunks）
- Session 恢复：Codex 用 `--session`，Claude 用 `--resume`

#### 2. 状态机

```python
class Phase(Enum):
    INIT = "init"
    REFINE_GOAL = "refine_goal"
    WRITE_PLAN = "write_plan"
    REVIEW = "review"
    RESPOND = "respond"
    APPROVED = "approved"
    EXECUTE = "execute"
    DONE = "done"
```

状态转换规则定义在 `TRANSITIONS` 字典中，`can_transition()` 函数验证转换合法性。

#### 3. 原子写入

```python
def save_state(state, path):
    fd, tmp_path = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "w") as f:
        json.dump(state.to_dict(), f)
    os.rename(tmp_path, path)  # 原子操作
```

**为什么**：防止写入过程中断导致状态文件损坏。

#### 4. Prompt 模板

使用 `{{variable}}` 语法，简单正则替换：

```python
def substitute_variables(template, **variables):
    def replace(match):
        var_name = match.group(1).strip()
        return variables.get(var_name, match.group(0))
    return re.sub(r"\{\{(\w+)\}\}", replace, template)
```

#### 5. 恢复流程

```
启动 → 检测 state.json
       ↓ 存在且 phase ≠ DONE
       提示"是否恢复？"
       ↓ 是
       尝试用 session ID 恢复
       ↓ 失败
       读取 plan/comments，注入 prompt（降级恢复）
```

### 测试策略

- 每个模块都有对应的测试文件
- 主要测试初始化、边界条件、状态转换
- TUI 测试不涉及实际渲染，只测试组件初始化和方法
- 总计 66 个测试，全部通过

### 遇到的问题

1. **pyproject.toml 需要 README.md**：hatchling 构建时检查 readme 字段
2. **变量替换正则不支持空格**：`{{ name }}` 不匹配，MVP 决定不支持（简化）
3. **TUI 测试复杂**：Textual 组件需要挂载才能 query，MVP 只测初始化

## 工作流文件约定

```
<project-root>/          ← Agent 执行目录（cwd）
└── .agent-collab/       ← 工作流产物目录
    ├── state.json       # {"phase": "...", "iteration": N, "planner_session": "...", ...}
    ├── plan.md          # Planner 写的计划
    ├── comments.md      # Reviewer 的审阅意见，首行 [APPROVED] 或 [CHANGES_REQUIRED]
    └── log.md           # 执行日志
```

**重要**：`workdir` 只存产物，Agent 的 cwd 是项目根目录。

## 未完成 / 计划实现

### 短期（下一个 session 可做）

1. **自动模式**
   - 用户开启后，agent 自动轮次迭代直到 [APPROVED] 或达到上限
   - 需要添加 `[P]` 暂停、`[S]` 停止快捷键

2. **执行阶段完善**
   - 目前只是状态转换，没有实际执行步骤
   - 需要解析 plan.md 中的步骤，逐步执行
   - 每步执行前需用户 Enter 确认

3. **测试执行**
   - 自动检测测试框架（pytest/npm test）
   - 执行测试并显示结果

4. **Git 集成**
   - 每步完成后自动 commit
   - Commit message 格式：`[Step N] <简述>`

### 中期

5. **安全策略**
   - 检测危险命令（rm -rf 等）
   - 需确认的命令列表（git push 等）

6. **文件监控**
   - 使用 watchfiles 监控 plan/comments 变化
   - 自动刷新 TUI 内容

7. **多项目支持**
   - 支持切换/管理多个项目
   - 每个项目独立的 .agent-collab/

### 长期

8. **Web UI**
   - 用 FastAPI + WebSocket 替代 TUI
   - 更好的用户体验

9. **更多 Agent 支持**
   - GPT-4、Gemini 适配器
   - 本地模型支持

10. **作为 Claude Code Skill**
    - 将工具打包为 skill
    - 直接在 Claude Code 中调用

## 关键文件速查

| 文件 | 作用 |
|-----|------|
| `src/agent_collab/engine/workflow.py` | 工作流控制器，核心业务逻辑 |
| `src/agent_collab/engine/state_machine.py` | 状态机定义 |
| `src/agent_collab/adapters/base.py` | Agent 适配器抽象基类 |
| `src/agent_collab/tui/app.py` | TUI 应用，用户交互 |
| `src/agent_collab/persistence/state.py` | 状态持久化 |
| `prompts/*.md` | Prompt 模板 |
| `config.toml` | 默认配置 |
| `docs/plans/2026-02-05-agent-collab-design.md` | MVP 设计文档 |

## 经验总结

1. **先讨论再编码**：通过 brainstorming 明确需求，避免返工
2. **MVP 优先**：第一版设计太复杂时，果断精简
3. **测试保驾护航**：66 个测试让重构有信心
4. **增量提交**：每个 Step 一个 commit，便于追踪和回滚
5. **分层架构**：adapters/engine/tui/persistence 职责清晰，易于扩展
6. **不做强假设**：LLM 输出不可控，用明确标记而非启发式判断

---

*最后更新：2026-02-05*
