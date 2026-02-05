# Agent Collab 开发日志

## Step 1.1：项目初始化

**日期**：2026-02-05

**完成内容**：
- 创建项目目录结构：`src/agent_collab/{tui,engine,adapters,persistence}`、`tests/`、`prompts/`
- 创建 `pyproject.toml`，配置依赖（textual, watchfiles, tomli）和 CLI 入口
- 创建 `config.toml` 默认配置文件
- 创建 `main.py` 入口模块
- 使用 uv 创建虚拟环境并安装依赖
- 创建基础测试验证项目结构

**主要文件变更**：
- `pyproject.toml`：新建，定义项目元数据和依赖
- `config.toml`：新建，定义默认配置
- `src/agent_collab/main.py`：新建，CLI 入口点
- `tests/test_init.py`：新建，项目初始化测试

**测试结果**：2/2 通过

---

## Step 1.2：配置加载

**日期**：2026-02-05

**完成内容**：
- 创建 `config.py` 模块，定义配置数据类（RolesConfig, WorkflowConfig, PathsConfig, Config）
- 实现 `load_config()` 函数，支持从 TOML 文件加载配置
- 支持部分配置（未指定的字段使用默认值）
- 添加路径辅助方法（get_workdir, get_plan_path 等）

**主要文件变更**：
- `src/agent_collab/config.py`：新建，配置加载逻辑
- `tests/test_config.py`：新建，配置加载测试

**测试结果**：6/6 通过

---

## Step 1.3：Agent 适配器

**日期**：2026-02-05

**完成内容**：
- 创建 `AgentAdapter` 抽象基类，定义 send/resume_session/check_available 等接口
- 实现 `CodexAdapter`：调用 codex CLI，支持 --cwd 和 --session 参数
- 实现 `ClaudeAdapter`：调用 claude CLI，支持 --print 和 --resume 参数
- 创建 `create_adapter()` 工厂函数，根据类型创建适配器

**主要文件变更**：
- `src/agent_collab/adapters/base.py`：新建，AgentAdapter 抽象基类
- `src/agent_collab/adapters/codex.py`：新建，Codex CLI 适配器
- `src/agent_collab/adapters/claude.py`：新建，Claude CLI 适配器
- `src/agent_collab/adapters/factory.py`：新建，适配器工厂
- `src/agent_collab/adapters/__init__.py`：更新，导出所有适配器
- `tests/test_adapters.py`：新建，适配器测试

**测试结果**：12/12 通过

---

## Step 1.4：状态机 + 持久化

**日期**：2026-02-05

**完成内容**：
- 创建 `Phase` 枚举，定义工作流所有阶段
- 定义状态转换规则 `TRANSITIONS`，实现 `can_transition()` 和 `get_next_phases()`
- 创建 `WorkflowState` 数据类，支持 to_dict/from_dict 序列化
- 实现 `save_state()`：原子写入（先写临时文件再 rename）
- 实现 `load_state()`、`delete_state()`、`state_exists()`

**主要文件变更**：
- `src/agent_collab/engine/state_machine.py`：新建，Phase 枚举和状态转换
- `src/agent_collab/engine/__init__.py`：更新，导出状态机组件
- `src/agent_collab/persistence/state.py`：新建，WorkflowState 和持久化函数
- `src/agent_collab/persistence/__init__.py`：更新，导出持久化组件
- `tests/test_state_machine.py`：新建，11 个状态机测试
- `tests/test_persistence.py`：新建，9 个持久化测试

**测试结果**：20/20 通过

---

## Step 1.5：Prompt 加载器

**日期**：2026-02-05

**完成内容**：
- 创建 `prompt_loader.py`，实现 `load_prompt()`、`substitute_variables()`、`list_prompts()`
- 变量替换使用 `{{variable}}` 语法
- 创建 6 个 prompt 模板文件（refine_goal, write_plan, review_plan, respond_comments, execute_step, recover_context）

**主要文件变更**：
- `src/agent_collab/engine/prompt_loader.py`：新建，模板加载和变量替换
- `src/agent_collab/engine/__init__.py`：更新，导出 prompt_loader 函数
- `prompts/01_refine_goal.md` - `prompts/06_recover_context.md`：新建，6 个 prompt 模板
- `tests/test_prompt_loader.py`：新建，11 个 prompt 加载测试

**测试结果**：11/11 通过
