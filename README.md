# 🎮 Project: Sentinel-Wiki (Game-Aware RAG Agent)

**Sentinel-Wiki** 是一个基于 **LangChain** 和 **MCP (Model Context Protocol)** 构建的通用型智能游戏管家。它的核心逻辑是：**“Wiki 提供全局知识，存档提供玩家现状，Agent 负责逻辑对齐。”**

该系统不仅能通过 RAG 检索百科知识，还能通过本地运行的 MCP Server 实时读取并分析你的游戏存档，提供传统搜索引擎无法实现的“个性化深度攻略”。

---

## 🛠 技术栈 (Tech Stack)

### 1. Agent 逻辑编排
* **[LangChain](https://python.langchain.com/):** 负责 Agent 的 ReAct 思考循环、多步推理以及与 LLM 的通信。
* **Claude 3.5 Sonnet:** (推荐模型) 具有极强的逻辑推理能力和对 MCP 协议的原生支持。

### 2. 知识检索 (RAG Layer)
* **Vector DB (Qdrant / Chroma):** 存储 Wiki 文本向量。
* **Embedding Model:** `text-embedding-3-small` (OpenAI) 或本地 HuggingFace 模型。
* **Data Ingestion:** 基于 `BeautifulSoup` 和 `MediaWiki API` 的结构化爬虫。

### 3. 本地感知层 (MCP Server)
* **[MCP SDK](https://modelcontextprotocol.io/):** 实现本地数据与云端 LLM 的标准化安全通信。
* **Stardew Valley Save Parser:** 使用 Python 解析星露谷物语的 XML 存档文件。

---

## 🌟 首个落地案例：星露谷物语 (Stardew Valley)

本项目首选**星露谷物语**作为原型实现，因为它拥有极高价值的 Wiki 数据和易于解析的 XML 存档。

### 核心 MCP 工具集
1. **`get_player_status`**: 获取玩家当前金钱、当前季节、日期及农场类型。
2. **`get_inventory`**: 扫描玩家背包及所有储物箱（Chests）中的物品。
3. **`get_social_info`**: 读取 NPC 好感度状态及送礼记录。
4. **`get_farm_map`**: 分析农场土地上已种植的作物及其生长进度。

### 典型应用场景
* **精准种植建议**：“Agent，我包里有 50 个甜瓜种子，现在是夏季第 12 天，我种下去能赶在入秋前收割吗？”
* **动态礼物管家**：“今天是谁的生日？根据我的仓库库存，送什么性价比最高？”

---

## 🧩 系统可扩展性设计

本系统采用**解耦架构**，具有极强的通用性，通过更换组件即可支持新游戏：

| 组件 | 扩展方式 |
| :--- | :--- |
| **MCP Server** | 更换存档解析库（如从 Stardew 换成 Elden Ring 的 `.sav` 解析）。 |
| **Vector DB** | 切换或新增不同的向量集合（Collection），存储新游戏的 Wiki。 |
| **Prompt** | 微调 System Prompt，改变 Agent 的语言风格和建议逻辑。 |

---

## 📂 项目结构预设

```bash
├── agents/
│   ├── reasoning_engine.py  # LangChain Agent 核心逻辑
│   └── prompts.py           # 针对不同游戏的 System Prompts
├── mcp_servers/
│   ├── stardew_mcp.py       # 星露谷物语专用 MCP Server (当前重点)
│   └── parser_utils.py      # XML/二进制解析工具函数
├── vectorstore/
│   ├── ingest_wiki.py       # Wiki 爬取与向量化脚本
│   └── query_rag.py         # RAG 检索接口
└── config/                  # 游戏存档路径及 API 密钥配置