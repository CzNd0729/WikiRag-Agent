# 🎮 Project: Sentinel-Wiki (Universal General-Aware RAG Agent)

**Sentinel-Wiki** 是一个基于 **LangGraph** 和 **MCP (Model Context Protocol)** 构建的高性能通用百科智能管家。

---

## 🏗 第三阶段：多智能体工作流编排 (已完成)

项目已通过 LangGraph 实现了一个具备**意图识别、自动化检索、自我反思与长会话摘要**能力的通用 Agent 框架。

### 核心特性
- **通用百科适配**: 提示词和逻辑均已脱离特定游戏，可应用于任何 Markdown 知识库。
- **高可靠闭环**: 引入 Reflector 节点对回答质量进行实时质检，不合格则自动触发重新检索。
- **多模型配置**: 支持在 `.env` 中为不同节点（RAG 改写、Agent 决策、Embedding）配置不同的 Provider（DeepSeek, Qwen, SiliconFlow 等）。
- **JSON 强制输出**: 修复了 OpenAI 400 报错，通过 Prompt 约束和模型参数确保结构化输出的稳定性。

---

## 📂 项目结构 (Project Structure)

本项目的目录组织遵循**业务逻辑优先**原则，确保模块的高内聚与低耦合。

```bash
├── src/
│   ├── core/                # 核心通用引擎
│   │   ├── agent_graph.py    # LangGraph 状态机编排逻辑
│   │   ├── rag_engine.py     # 集成改写与重排的通用检索引擎
│   │   └── llm_provider.py   # 多模型与多 Provider 适配层
│   ├── agents/              # 业务 Agent 定义
│   │   ├── reasoning_engine.py # 对外交互入口与测试脚本
│   │   ├── prompts.py        # 通用百科 System Prompts (JSON 格式)
│   │   └── schemas.py        # Pydantic 消息契约与状态定义
│   ├── mcp_servers/         # 实时数据环境接入 (MCP 协议)
│   │   ├── stardew_mcp.py    # 存档接入示例
│   │   └── parser_utils.py   # 结构化解析工具
│   └── vectorstore/         # 数据持久化层
│       └── query_rag.py      # 基础向量库操作
└── tests/                   # 自动化评测
```

---

## 🛠 快速开始

1. **配置环境变量**: 复制 `.env.example` 为 `.env` 并填入相应的 API Key。
2. **启动 Agent**: 运行 `python src/agents/reasoning_engine.py` 进行交互式测试。
