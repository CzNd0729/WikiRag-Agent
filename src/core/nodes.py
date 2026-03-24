import json
from langchain_core.messages import (
    SystemMessage, 
    HumanMessage, 
    ToolMessage,
    trim_messages
)
from core.llm_provider import get_chat_model
from core.tools import tools
from agents.prompts import (
    COORDINATOR_PROMPT, 
    REFLECTOR_PROMPT, 
    SUMMARIZER_PROMPT,
    FINAL_GENERATOR_PROMPT,
    MEMORY_REFINE_PROMPT
)
from agents.schemas import AgentAction, ReflectorAnalysis, AgentState
from core.memory import MemoryManager

# 初始化记忆管理器
memory_manager = MemoryManager()

# 模型初始化
llm = get_chat_model("AGENT_LLM")
# 绑定工具用于 coordinator
llm_with_tools = llm.bind_tools(tools)

async def tools_node(state: AgentState):
    """
    执行工具。
    1. 结果作为 ToolMessage 存入 messages（思维链）。
    2. 检索到的 Source/URL 存入 documents（仅引用，不入对话历史）。
    """
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    
    if not tool_calls:
        return {"next_node": "final_generator"}
    
    new_messages = []
    new_documents = []
    tool_map = {tool.name: tool for tool in tools}
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name in tool_map:
            result = await tool_map[tool_name].ainvoke(tool_args)
            
            final_content = str(result)
            
            # 特殊处理 search_wiki: 提取 URL 并精简 ToolMessage 内容
            if tool_name == "search_wiki":
                try:
                    data = json.loads(result)
                    if isinstance(data, list):
                        content_list = []
                        for doc in data:
                            if "url" in doc and doc["url"]:
                                new_documents.append(doc["url"])
                            # 即使没有 url，也将 source 存入 documents 作为兜底引用
                            elif "source" in doc:
                                new_documents.append(doc["source"])
                            
                            # 提取正文用于 ToolMessage
                            content_list.append(doc.get("content", ""))
                        
                        # ToolMessage 仅保留正文内容，减少 token 占用并保持纯净
                        final_content = "\n\n---\n\n".join(content_list)
                except:
                    pass
            elif tool_name == "read_full_wiki":
                # read_full_wiki 的结果通常是纯文本，尝试将其 path 存入 documents
                if "source_path" in tool_args:
                    new_documents.append(tool_args["source_path"])
            
            # 完整记录到消息列表（作为思维链）
            new_messages.append(ToolMessage(
                content=final_content,
                tool_call_id=tool_call["id"]
            ))
        else:
            new_messages.append(ToolMessage(
                content=f"Error: Tool {tool_name} not found.",
                tool_call_id=tool_call["id"]
            ))
            
    return {
        "messages": new_messages,
        "documents": new_documents,
        "next_node": "reflector"
    }

async def memory_retriever(state: AgentState):
    """
    记忆检索节点：在对话开始前获取用户画像。
    从 PostgreSQL 获取该用户的持久化画像 (User Profile)。
    """
    user_id = state.get("user_id", "default_user")
    
    # 1. 获取持久化的用户画像
    user_profile = await memory_manager.get_user_profile(user_id)
    
    # 注入上下文
    combined_memories = []
    if user_profile:
        combined_memories.append("### User Profile (Facts & Preferences):")
        combined_memories.extend([f"- {f}" for f in user_profile])
    
    return {
        "long_term_memory": combined_memories
    }

async def coordinator(state: AgentState):
    """任务分发与协调。"""
    messages = state["messages"]
    summary = state.get("summary", "")
    ltm = state.get("long_term_memory", [])
    
    prompt = COORDINATOR_PROMPT
    if summary:
        prompt += f"\n\nContext Summary: {summary}"
    
    if ltm:
        ltm_str = "\n".join(ltm)
        prompt += f"\n\nUser Long-term Memory (Preferences/Facts):\n{ltm_str}"
        
    # 构建请求消息列表
    req_messages = [SystemMessage(content=prompt)]
    req_messages.extend(messages)
        
    response = await llm_with_tools.ainvoke(req_messages)
    
    if response.tool_calls:
        # 模型决定调用工具
        return {
            "next_node": "tools",
            "messages": [response]
        }
    
    # 无需工具，直接生成最终回答
    return {"next_node": "final_generator", "messages": [response]}

async def reflector(state: AgentState):
    """结果反思。仅做判断，不执行消息裁剪。"""
    # 从消息历史中提取最新的工具执行结果作为参考
    tool_outputs = [m.content for m in state["messages"] if isinstance(m, ToolMessage)]
    context_str = "\n".join(tool_outputs)
    
    response = await llm.ainvoke([
        SystemMessage(content=REFLECTOR_PROMPT),
        HumanMessage(content=f"Collected Content:\n{context_str}\n\nUser Question: {state['messages'][0].content}") # 参考最初的问题
    ])
    
    try:
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        
        data = json.loads(content)
        analysis = ReflectorAnalysis(**data)
        
        if analysis.next_step == "continue" and state["reflection_count"] < 3:
            return {
                "next_node": "coordinator", 
                "reflection_count": state["reflection_count"] + 1
            }
            
        return {"next_node": "final_generator"}
    except Exception as e:
        print(f"Reflector error: {e}")
        return {"next_node": "final_generator"}

async def final_generator(state: AgentState):
    """基于完整思维链（messages）生成回答，并程序化填充文档引用（documents）。"""
    # 构造包含完整历史的消息列表，不再将 documents 显式发给 AI
    prompt_messages = [
        SystemMessage(content=FINAL_GENERATOR_PROMPT),
    ]
    # 注入历史（包含 ToolMessages，已具备所有事实）
    prompt_messages.extend(state["messages"])
    
    response = await llm.ainvoke(prompt_messages)
    
    # 程序化处理输出：将 state["documents"] 注入到 response 的 metadata 或 content 中
    try:
        content = response.content.strip()
        # 去除可能存在的 markdown 格式
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content.strip("`").strip()
            
        ai_data = json.loads(content)
        
        # 构建最终输出 JSON，强制包含程序化的 sources
        final_data = {
            "answer": ai_data.get("answer", ""),
            "sources": list(set(state.get("documents", []))),
            "actionable_tips": ai_data.get("actionable_tips", [])
        }
            
        # 写回 response content
        response.content = json.dumps(final_data, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Final generator post-processing error: {e}")
        # 如果解析失败，尝试构建一个兜底结构
        if state.get("documents"):
             fallback = {
                 "answer": response.content,
                 "sources": list(set(state["documents"])),
                 "actionable_tips": []
             }
             response.content = json.dumps(fallback, ensure_ascii=False)
        
    return {"messages": [response]}

async def summarizer(state: AgentState):
    """会话管理：自动裁剪过长历史并生成摘要。"""
    trimmed_messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=len, # 粗略计数
        max_tokens=4000,
        start_on="human",
        include_system=True
    )
    
    summary_update = {}
    if len(state["messages"]) >= 6: # 降低摘要阈值以更频繁地捕捉状态
        response = await llm.ainvoke([
            SystemMessage(content=SUMMARIZER_PROMPT),
            HumanMessage(content=str(trimmed_messages))
        ])
        summary_update["summary"] = response.content

    return {**summary_update}

async def memory_refiner(state: AgentState):
    """
    记忆固化节点：从对话中提取并优化记忆。
    1. 提取新事实并更新 PostgreSQL 中的用户画像。
    2. 将关键对话片段存入 ChromaDB，按 user_id 隔离。
    """
    messages = state["messages"]
    user_id = state.get("user_id", "default_user")
    conv_id = state.get("conversation_id", "default_conv")
    
    # 提取新事实
    new_facts = await memory_manager.extract_memorable_facts(messages, state.get("summary", ""))
    
    if new_facts:
        # 1. 更新用户画像 (PostgreSQL)
        current_profile = await memory_manager.get_user_profile(user_id)
        refine_prompt = MEMORY_REFINE_PROMPT + f"\n\nCurrent Profile:\n{current_profile}\n\nNew Facts:\n{new_facts}"
        response = await llm.ainvoke([SystemMessage(content=refine_prompt)])
        
        # 假设模型返回按行分隔的事实
        refined_profile = [line.strip("- ").strip() for line in response.content.split("\n") if line.strip()]
        memory_manager.update_user_profile(user_id, refined_profile)
        
        # 2. 持久化对话历史 (ChromaDB) - 暂时不需要
        # memory_manager.persist_chat_history(new_facts, user_id, conv_id)
        
        return {"long_term_memory": refined_profile}
        
    return {}
