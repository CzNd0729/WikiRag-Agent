# Sentinel-Wiki 项目开发任务清单 (TODO.md)

## 📅 第一阶段：MCP 服务器开发 (核心优先级)
> **目标**: 构建符合 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 标准规范的本地感知层，实现对《星露谷物语》存档的安全、标准化访问。

- [x] **MCP 基础架构搭建**
    - [x] 初始化符合 MCP 标准的 Python 开发环境。
    - [x] 配置 `mcp` 核心 SDK 依赖。
- [x] **存档解析逻辑实现 (`mcp_servers/parser_utils.py`)**
    - [x] 实现针对 `SaveGame` XML 结构的稳健解析器。
    - [x] 封装基础数据提取函数（金钱、日期、农场类型等）。
- [x] **定义标准 MCP Tools (`mcp_servers/stardew_mcp.py`)**
    - [x] `get_player_status`: 返回玩家基础属性（符合 MCP Tool 定义规范）。
    - [x] `get_inventory`: 递归扫描背包与储物箱数据。
    - [x] `get_social_info`: 提取 NPC 好感度及送礼历史。
    - [x] `get_farm_map`: 解析农作物生长状态。
- [x] **安全性与性能优化**
    - [x] 实现只读访问控制，确保不修改用户原始存档。
    - [x] 增加错误处理机制，处理 XML 解析异常。

## 📅 第二阶段：知识检索层 (RAG Layer)
- [x] **Wiki 数据采集**
    - [x] 编写基于 BeautifulSoup/MediaWiki API 的爬虫。
    - [x] 结构化处理《星露谷物语》Wiki 页面。
- [x] **向量化与存储**
    - [x] 集成 Qdrant 或 Chroma 向量数据库。
    - [x] 实现文本分块（Chunking）与向量嵌入（Embedding）脚本。
- [x] **检索优化**
    - [x] 实现混合检索（BM25 + 向量检索）。

## 📅 第三阶段：Agent 逻辑编排
- [ ] **LangChain 核心构建**
    - [ ] 定义 ReAct 思考循环模板。
    - [ ] 集成 MCP 工具集到 LangChain Toolbelt。
- [ ] **Prompt 工程**
    - [ ] 编写针对游戏场景的 System Prompts。
- [ ] **端到端测试**
    - [ ] 验证 "Wiki 知识 + 存档现状" 的联合推理逻辑。

## 📅 第四阶段：通用化扩展
- [ ] **多游戏支持框架**
    - [ ] 抽象 MCP Server 基类。
    - [ ] 文档化扩展流程。
