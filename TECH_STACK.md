# WikiRag-Agent 技术栈库说明文档 (TECH_STACK.md)

本项目的核心理念是 **“Wiki 提供全局知识，存档提供玩家现状，Agent 负责逻辑对齐”**。以下是实现该目标所选用的关键库及其具体作用说明。

## ⚙️ 核心协议层 (Core Protocol Layer)

### [mcp (Model Context Protocol Python SDK)](https://github.com/modelcontextprotocol/python-sdk)
*   **作用**: 实现 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 标准协议。
*   **在本项目中的用途**:
    *   **标准化通信**: 为 Agent 提供一套标准的、安全的访问本地数据的接口。
    *   **Tool 定义**: 定义符合 MCP 规范的工具（如 `get_inventory`），使 LLM (如 Claude 3.5 Sonnet) 能够直接、原生理解并调用本地功能。

## 🧠 逻辑编排层 (Orchestration Layer)

### [LangChain](https://python.langchain.com/)
*   **作用**: 大模型应用开发的端到端框架。
*   **在本项目中的用途**:
    *   **Reasoning Engine (推理引擎)**: 管理 Agent 的 ReAct (Reasoning and Acting) 思考路径，决定何时检索 Wiki，何时调用 MCP 工具。
    *   **Memory Management**: 维护玩家在对话过程中的上下文，例如询问“我该种什么”时，Agent 能记住前文关于季节的讨论。

## 📂 本地感知与存档解析 (Local Perception Layer)

### [xml.etree.ElementTree](https://docs.python.org/3/library/xml.etree.elementtree.html) / [lxml](https://lxml.de/)
*   **作用**: Python 标准/扩展 XML 解析库。
*   **在本项目中的用途**:
    *   **存档解析**: 《星露谷物语》的存档文件采用高度嵌套的 XML 结构。该库用于高效地从中提取玩家的金钱、背包物品、NPC 好感度及农作物生长状态。

## 📚 知识检索层 (RAG Layer)

### [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) / [requests](https://requests.readthedocs.io/)
*   **作用**: HTML 网页解析与 HTTP 请求库。
*   **在本项目中的用途**:
    *   **Wiki 爬虫**: 针对 Stardew Valley Wiki (MediaWiki 平台) 进行结构化网页抓取，提取作物周期、NPC 喜好表等高价值信息。

### [Qdrant](https://qdrant.tech/) 或 [ChromaDB](https://www.trychroma.com/)
*   **作用**: 向量数据库。
*   **在本项目中的用途**:
    *   **知识检索存储**: 存储经 Embedding 处理后的 Wiki 知识向量，支持快速的高维语义搜索。

### [OpenAI Python SDK](https://github.com/openai/openai-python)
*   **作用**: 连接 OpenAI 模型接口。
*   **在本项目中的用途**:
    *   **Embedding**: 调用 `text-embedding-3-small` 模型将 Wiki 文本转换为向量，用于 RAG 检索。
