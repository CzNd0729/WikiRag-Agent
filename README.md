# Project: WikiRag-Agent

**WikiRag-Agent** 是一个基于 **LangGraph** 和 **MCP (Model Context Protocol)** 构建的高性能通用百科智能管家。

---

## 🏗 第四阶段：全链路评测与部署 (已完成)

项目已完成全链路监控、自动化评测以及单文件部署封装。

### 核心特性
- **全链路追踪**: 集成 Langfuse，通过 `.env` 即可开启推理过程的深度监控与耗时分析。
- **自动化评测**: 建立 `tests/eval_suite.py` 评测工程，支持基于关键词匹配与工具调用准确率的自动评分。
- **统一入口**: 封装 `main.py` 命令行工具，支持 `chat` (对话) 与 `eval` (评测) 双模式切换。
- **健壮性优化**: 在 LLM 调用层引入自动重试与超时控制，提升在复杂网络环境下的稳定性。

---

## 📂 项目结构 (Project Structure)

本项目的目录组织遵循**业务逻辑优先**原则，确保模块的高内聚与低耦合。

```bash
├── main.py                  # 统一程序入口 (对话/评测)
├── src/
│   ├── server.py            # LangServe 部署入口
│   ├── core/                # 核心通用引擎
│   │   ├── graph.py         # LangGraph 状态机编排逻辑
│   │   ├── memory.py        # 记忆管理模块 (PostgreSQL 用户画像 + Chroma 对话隔离)
│   │   ├── nodes.py          # LangGraph 节点函数定义
│   │   ├── tools.py          # Agent 业务工具集定义
│   │   ├── rag_engine.py     # 集成改写与重排的通用检索引擎
│   │   └── llm_provider.py   # 多模型与多 Provider 适配层
│   ├── agents/              # 业务 Agent 定义
│   │   ├── reasoning_engine.py # 对外交互入口逻辑
│   │   ├── prompts.py        # 通用百科 System Prompts (JSON 格式)
│   │   └── schemas.py        # Pydantic 消息契约与状态定义
│   ├── mcp_servers/         # 实时数据环境接入 (MCP 协议)
│   │   ├── stardew_mcp.py    # 存档接入示例
│   │   └── parser_utils.py   # 结构化解析工具
│   └── vectorstore/         # 数据持久化层
│       └── query_rag.py      # 基础向量库操作
├── tests/                   # 自动化评测
│   └── eval_suite.py        # 自动化评测套件
└── .env.example             # 环境变量配置模板
```

---

## 🛠 快速开始

1. **配置环境变量**: 复制 `.env.example` 为 `.env` 并填入相应的 API Key。
   - 务必配置 `LANGFUSE_SECRET_KEY` 和 `LANGFUSE_PUBLIC_KEY` 以开启 Langfuse 追踪。
   - 可选配置 `JUDGE_LLM` 来指定评测用的 Judge 模型。

---

## 🚀 Langfuse 部署说明

您可以选择以下两种方式部署 Langfuse：

### 1. 使用 Langfuse Cloud (最简单)
- 访问 [Langfuse 官网](https://cloud.langfuse.com/) 注册账号。
- 创建新项目并获取 `Secret Key` 和 `Public Key`。
- 在 `.env` 中设置 `LANGFUSE_HOST=https://cloud.langfuse.com`。

### 2. 本地私有化部署 (Docker)
如果您希望数据保留在本地，可以使用 Docker Compose 快速部署：

```bash
# 下载官方 docker-compose.yml
curl -O https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml

# 启动服务
docker-compose up -d
```

- 部署完成后，访问 `http://localhost:3000` 进行初始化设置。
- 在 `.env` 中设置 `LANGFUSE_HOST=http://localhost:3000`。
- 获取对应的 Key 并填入 `.env`。

---
>>>>+++ REPLACE

2. **启动 Agent**: 运行 `python main.py chat` 进入交互式对话。
3. **运行评测**: 运行 `python main.py eval` 执行自动化性能评估。
   - 评测完成后，可前往 Langfuse 云端查看详细的 LLM as a Judge 评分与推理 Trace。
4. **Chainlit UI 启动**:
   - 运行 `chainlit run src/app.py -w` 启动 Web UI。
   - 访问 `http://localhost:8000` 即可与 Agent 进行流式对话。
5. **LangServe 部署**:
   - 运行 `python src/server.py` 启动 API 服务。
   - 访问 `http://localhost:8000/agent/playground/` 进行可视化交互。
