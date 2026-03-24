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
            
            # 提取引用源 (Source/URL)
            if tool_name in ["search_wiki", "read_full_wiki"]:
                try:
                    data = json.loads(result)
                    if isinstance(data, list):
                        # search_wiki 返回列表
                        for doc in data:
                            if "source" in doc:
                                new_documents.append(doc["source"])
                    elif isinstance(data, dict) and "source" in data:
                        # read_full_wiki 可能返回单个对象
                        new_documents.append(data["source"])
                except:
                    pass
            
            # 完整记录到消息列表（作为思维链）
            new_messages.append(ToolMessage(
                content=str(result),
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
    """记忆检索节点：在对话开始前获取长期记忆。"""
    last_query = state["messages"][-1].content
    conv_id = state.get("conversation_id", "default")
    
    ltm = await memory_manager.retrieve_long_term_memory(last_query, conv_id)
    
    # 这里我们返回的是对 state 的增量更新
    # 如果 retrieve_long_term_memory 返回的是字符串，我们将其放入列表
    ltm_list = [ltm] if ltm else []
    
    return {
        "long_term_memory": ltm_list
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
    """基于完整思维链（messages）和文档引用（documents）生成最终回答。"""
    # 构造包含完整历史的消息列表
    prompt_messages = [
        SystemMessage(content=FINAL_GENERATOR_PROMPT),
    ]
    # 注入历史（包含 ToolMessages，已具备所有事实）
    prompt_messages.extend(state["messages"])
    
    # 注入引用源信息
    if state.get("documents"):
        unique_docs = list(set(state["documents"]))
        prompt_messages.append(SystemMessage(content=f"参考来源列表：\n" + "\n".join(unique_docs)))
    
    response = await llm.ainvoke(prompt_messages)
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
    """记忆固化节点：从对话中提取并优化长期记忆。"""
    messages = state["messages"]
    current_ltm = state.get("long_term_memory", [])
    conv_id = state.get("conversation_id", "default")
    
    # 提取新事实
    new_facts = await memory_manager.extract_memorable_facts(messages, state.get("summary", ""))
    
    if new_facts:
        # 合并并优化长期记忆
        refine_prompt = MEMORY_REFINE_PROMPT + f"\n\nCurrent Memories:\n{current_ltm}\n\nNew Facts:\n{new_facts}"
        response = await llm.ainvoke([SystemMessage(content=refine_prompt)])
        
        # 简单处理输出，假设模型返回按行分隔的事实
        refined_ltm = [line.strip("- ").strip() for line in response.content.split("\n") if line.strip()]
        
        # 持久化
        memory_manager.persist_memory(refined_ltm, conv_id)
        
        return {"long_term_memory": refined_ltm}
        
    return {}
