# Sentinel-Wiki 项目开发任务清单 (TODO.md)

## 🏗 第一阶段：基础设施与 MCP 协议集成 (已完成)
- [x] **MCP 基础架构搭建**: 初始化 Python 环境并配置 MCP SDK 依赖。
- [x] **存档解析逻辑实现 (`src/mcp_servers/parser_utils.py`)**: 针对 `SaveGame` XML 结构的稳健解析。
- [x] **标准 MCP Tools 定义 (`src/mcp_servers/stardew_mcp.py`)**: 实现 `get_player_status`, `get_inventory`, `get_social_info`, `get_farm_map`。
- [x] **安全性与只读访问**: 确保存档数据完整性。

## 🚀 第二阶段：高性能 RAG 架构优化 (已完成)
- [x] **基础 RAG 构建**: 基于 Chroma 的向量存储与 BM25 混合检索。
- [x] **集成 LLM 查询改写**: **[优化]** 已迁移至协调员 Agent 层进行全局上下文改写，而非 RAG 引擎内部。
- [x] **Reranker 语义重排**: 接入 BGE-Reranker v2-m3 对初步检索结果进行精准排序。
- [x] **自适应文本分块**: 优化 Markdown 切分策略，并支持“全文深度阅读”作为长文档补充。

## 🧠 第三阶段：多智能体工作流编排 (核心重点 - 已完成)
- [x] **LangGraph 状态机重构**:
    - [x] 定义严谨的 Node（协调器、反思者、最终生成器、摘要器）。
    - [x] 实现基于消息的状态转移逻辑，通过循环检索抑制幻觉。
- [x] **高可靠闭环设计**:
    - [x] 引入结构化数据契约 (Pydantic) 约束所有 Agent 输出格式。
    - [x] 增加反思逻辑与最大重试次数限制，防止死循环。
- [x] **长会话上下文管理**:
    - [x] 实现基于摘要与 `trim_messages` 裁剪的消息管理中间件。
    - [x] 优化长对话中的跨轮次记忆追踪。

## 📊 第四阶段：全链路评测与部署 (闭环 - 已完成)
- [x] **接入 LangSmith**: 配置 Trace 追踪，支持在 `.env` 中开启 `LANGCHAIN_TRACING_V2`。
- [x] **评测工程**:
    - [x] 构建自动化评测集 `tests/eval_suite.py`。
    - [x] 引入基于关键词与工具调用的多维评分机制。
- [x] **部署与通用化**:
    - [x] 封装统一入口 `main.py`，支持 `chat` 和 `eval` 模式。
    - [x] 优化 `llm_provider.py`，增加 `max_retries` 与 `timeout` 容错机制。
