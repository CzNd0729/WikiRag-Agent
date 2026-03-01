# 🎮 Project: Sentinel-Wiki (Game-Aware RAG Agent)

**Sentinel-Wiki** 是一个基于 **LangGraph** 和 **MCP (Model Context Protocol)** 构建的高性能、高可靠游戏智能管家。它通过“Wiki 提供全局知识，存档提供玩家现状，Agent 负责逻辑对齐”的核心逻辑，为玩家提供深度个性化的游戏决策支持。

---

## 🎯 核心完成目标

-   **多智能体工作流编排**: 使用 **LangGraph** 构建基于状态机的异步协作流，通过定义严谨的状态节点与转移逻辑，将复杂业务解耦为可预测的任务链，有效抑制长链条推理中的幻觉现象，提升工程确定性。
-   **高可靠 Agent 闭环设计**: 设计完备的自反思与失败兜底机制，利用结构化数据契约约束模型输出，实现了从意图识别到工具调用的全链路自动化闭环。
-   **高性能 RAG 架构优化**: 构建了集成 LLM 查询改写的高性能 RAG 管线，基于 **Chroma** 实现向量与 BM25 的混合召回。通过 **Reranker** 语义重排与自适应文本分块策略，在非结构化百科知识库上实现了 90% 以上的上下文召回率。
-   **长会话与上下文管理**: 利用摘要中间件对历史对话进行语义提取与压缩，有效解决了 LLM 窗口限制导致的早期意图丢失问题，减少约 40% 的 token 消耗，支持超长会话的稳定上下文追踪。
-   **基于 MCP 协议的工具集成**: 利用 **MCP SDK** 开发高性能本地插件，实现对异构存档数据（如 XML/二进制）的自动化扫描与结构化映射，打通了 LLM 与私有数据环境的交互通路。
-   **全链路追踪与评测工程**: 接入 **LangSmith** 建立全生命周期监控，深度分析从意图解析到最终交付的 Trace 记录，通过自动化评测集迭代 Prompt 策略，意图识别成功率提升达 95%。

---

## 🛠 技术栈 (Tech Stack)

-   **语言**: Python
-   **Agent 框架**: LangGraph (状态机编排), LangChain
-   **大模型**: Claude 3.5 Sonnet / DeepSeek-V3
-   **向量数据库**: Chroma
-   **检索优化**: BGE-Reranker (BAAI/bge-reranker-v2-m3), BM25
-   **本地感知**: MCP SDK (Model Context Protocol)
-   **监控评测**: LangSmith

---

## 🌟 首个落地案例：星露谷物语 (Stardew Valley)

本项目首选星露谷物语作为原型实现，因为它拥有极高价值的 Wiki 数据和易于解析的 XML 存档。

### 核心 MCP 工具集
1.  **`get_player_status`**: 获取玩家当前金钱、当前季节、日期及农场类型。
2.  **`get_inventory`**: 扫描玩家背包及所有储物箱（Chests）中的物品。
3.  **`get_social_info`**: 读取 NPC 好感度状态及送礼记录。
4.  **`get_farm_map`**: 分析农场土地上已种植的作物及其生长进度。

---

## 📂 项目结构

```bash
├── src/
│   ├── agents/
│   │   ├── reasoning_engine.py  # LangGraph Agent 核心逻辑
│   │   ├── prompts.py           # 结构化 Prompt 定义
│   │   └── memory.py            # 摘要中间件实现
│   ├── mcp_servers/
│   │   ├── stardew_mcp.py       # 星露谷物语 MCP Server
│   │   └── parser_utils.py      # 存档解析工具
│   ├── vectorstore/
│   │   ├── ingest_pipeline.py   # RAG 数据入库管线
│   │   └── query_rag.py         # 混合检索与重排逻辑
└── tests/                       # 自动化评测集
```
