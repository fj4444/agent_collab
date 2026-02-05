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
    [循环直到达成一致或达到迭代上限]
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

### 5. 达成一致的判定（混合策略）
1. Reviewer 在 comments.md 中写入 `[APPROVED]` 标记
2. comments.md 为空或仅含同意性语句
3. 迭代达到上限（默认 5 轮）→ 请求用户裁决

### 6. 持久化策略
- **优先完全持久化**：保存 state.json（阶段、session ID、迭代轮次）
- **降级机制**：session 恢复失败时，让 agent 重新读取 plan/comments 获取上下文

### 7. TUI 布局
- **主要 Tab**：对话、Plan、Comments
- **收起 Tab**：Log、Status（按需展开）

### 8. Prompt 管理
- `prompts/` 目录，每阶段一个 `.md` 模板文件
- 支持变量替换（如 `{{plan_content}}`）

### 9. 测试执行
- 由 Planner agent 自主决定测试方式
- 若 agent 需要确认，允许向用户发问

## 核心模块划分

```
agent-collab/
├── src/
│   ├── main.py              # 入口
│   ├── tui/                  # TUI 界面层
│   │   ├── app.py           # Textual App
│   │   └── tabs/            # 各 Tab 组件
│   ├── engine/              # 工作流引擎
│   │   ├── state_machine.py # 状态机
│   │   ├── approval.py      # 审批控制器
│   │   └── prompt_loader.py # 模板加载
│   ├── adapters/            # Agent 适配层
│   │   ├── base.py          # 抽象基类
│   │   ├── codex.py         # Codex 适配器
│   │   └── claude.py        # Claude Code 适配器
│   └── persistence/         # 持久化
│       └── state.py         # 状态存取
├── prompts/                  # Prompt 模板
│   ├── 01_refine_goal.md
│   ├── 02_write_plan.md
│   ├── 03_review_plan.md
│   ├── 04_respond_comments.md
│   └── 05_execute_step.md
├── config.toml               # 用户配置
└── docs/
    └── plans/
```

## 实现计划

### Phase 1：核心骨架（最小可用）

**目标**：能跑通一次完整的 plan → review → approve → execute 流程

**Step 1.1：Agent 适配器**
```python
# adapters/base.py
class AgentAdapter(ABC):
    @abstractmethod
    async def send(self, prompt: str) -> AsyncIterator[str]: ...
    @abstractmethod
    async def resume_session(self, session_id: str) -> bool: ...
    @abstractmethod
    def get_session_id(self) -> str: ...
```

- 实现 `CodexAdapter` 和 `ClaudeAdapter`
- 使用 `asyncio.subprocess` 调用 CLI
- 解析输出流，检测是否包含用户提问

**Corner cases**:
- CLI 不存在或未登录 → 启动时检查，给出明确错误
- Session 恢复失败 → 返回 False，由上层降级处理
- 输出解析异常 → 记录原始输出到 debug log

**Step 1.2：状态机**
```python
# engine/state_machine.py
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

- 定义状态转换规则
- 每次转换持久化到 state.json

**Step 1.3：持久化**
```python
# persistence/state.py
@dataclass
class WorkflowState:
    phase: Phase
    iteration: int
    planner_session: str | None
    reviewer_session: str | None
    auto_approve: bool
```

- 使用 `dataclasses` + JSON 序列化
- 原子写入（先写临时文件再 rename）

**Step 1.4：Prompt 加载器**
- 读取 `prompts/*.md`
- 简单的 `{{variable}}` 替换

### Phase 2：TUI 界面

**Step 2.1：基础框架**
- Textual App + TabbedContent
- 三个主 Tab：Conversation、Plan、Comments

**Step 2.2：实时输出**
- Agent 输出流式显示在 Conversation Tab
- Plan/Comments Tab 显示文件内容，文件变化时刷新

**Step 2.3：交互控制**
- 底部状态栏显示当前阶段
- 快捷键：`[Enter]` 放行、`[A]` 切换自动模式、`[Q]` 退出

**Corner cases**:
- 终端尺寸过小 → 显示最小尺寸提示
- 长输出 → 自动滚动，保留滚动历史

### Phase 3：完整工作流

**Step 3.1：目标细化阶段**
- 用户与 Planner 对话
- 用户输入 `/plan` 命令进入写 plan 阶段

**Step 3.2：Plan-Review 循环**
- Planner 写 plan.md
- Reviewer 读 plan，写 comments.md
- 检测一致性标记或迭代次数
- 手动模式下每轮等待用户 `[Enter]`

**Step 3.3：执行阶段**
- 逐步执行 plan 中的步骤
- 每步完成后：运行测试 → git commit → 更新 log.md

**Corner cases**:
- Plan 格式不规范 → 让 Planner 自行解析，不做强假设
- 测试失败 → 显示失败信息，让 Planner 决定是否修复
- Git 操作失败 → 记录错误，询问用户是否继续

### Phase 4：健壮性 & 体验优化

**Step 4.1：Session 恢复降级**
- 完全恢复失败时，构造包含 plan/comments 内容的 prompt
- 告知 agent "这是之前的上下文，请继续"

**Step 4.2：Agent 提问检测**
- 简单启发式：输出以 `?` 结尾或包含 "请问"/"是否" 等关键词
- 检测到时路由给用户回答

**Step 4.3：配置文件**
```toml
# config.toml
[roles]
planner = "codex"  # or "claude"
reviewer = "claude"

[workflow]
max_iterations = 5
auto_approve = false

[paths]
plan = "plan.md"
comments = "comments.md"
log = "log.md"
```

## 代码量估算

| 模块 | 估算行数 | 说明 |
|-----|---------|------|
| adapters/ | ~200 | 两个适配器 + 基类 |
| engine/ | ~150 | 状态机 + 审批 + prompt 加载 |
| persistence/ | ~80 | 状态存取 |
| tui/ | ~300 | Textual 界面 |
| prompts/ | ~100 | 5 个模板文件 |
| **总计** | **~830** | 不含测试 |

## 风险与缓解

| 风险 | 缓解措施 |
|-----|---------|
| CLI 输出格式变化导致解析失败 | 适配器做好容错，保留原始输出 |
| Agent 产出不符合预期格式 | 不做强假设，让 agent 自行处理 |
| Session 恢复不可靠 | 实现降级机制，重新喂上下文 |
| 长时间运行内存泄漏 | TUI 组件及时清理，限制历史长度 |

## 下一步

1. 初始化项目结构和依赖（`pyproject.toml`）
2. 实现 Phase 1 核心骨架
3. 编写基础测试
4. 迭代完善
