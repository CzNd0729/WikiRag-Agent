import json
from langchain_core.messages import (
    SystemMessage, 
    HumanMessage, 
    trim_messages
)
from core.llm_provider import get_chat_model
from core.tools import tools
from agents.prompts import (
    COORDINATOR_PROMPT, 
    REFLECTOR_PROMPT, 
    SUMMARIZER_PROMPT,
    FINAL_GENERATOR_PROMPT
)
from agents.schemas import AgentAction, ReflectorAnalysis, AgentState

# 模型初始化
llm = get_chat_model("AGENT_LLM")
# 绑定工具用于 coordinator
llm_with_tools = llm.bind_tools(tools)

async def tools_node(state: AgentState):
    """自定义工具调用节点。执行工具并直接将结果写入 context。仅 Wiki 检索结果带序号。"""
    last_message = state["messages"][-1]
    
    # 获取 llm 建议的工具调用
    tool_calls = getattr(last_message, "tool_calls", [])
    if not tool_calls:
        return {"next_node": "final_generator"}
    
    new_contexts = []
    # 建立工具映射
    tool_map = {tool.name: tool for tool in tools}
    
    # 获取当前已有的最大 WIKI 序号
    current_max_idx = -1
    for ctx in state.get("context", []):
        if ctx.startswith("[WIKI_"):
            try:
                idx = int(ctx.split("_")[1].split("]")[0])
                current_max_idx = max(current_max_idx, idx)
            except:
                pass
    
    wiki_idx_counter = current_max_idx + 1
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name in tool_map:
            result = await tool_map[tool_name].ainvoke(tool_args)
            
            if tool_name == "search_wiki":
                # 解析 Wiki 检索结果列表
                try:
                    wiki_docs = json.loads(result)
                    for doc in wiki_docs:
                        # 为每个 Wiki 片段分配独立序号 [WIKI_N]
                        fmt_ctx = f"[WIKI_{wiki_idx_counter}] (Source: {doc['source']})\n{doc['content']}"
                        new_contexts.append(fmt_ctx)
                        wiki_idx_counter += 1
                except:
                    new_contexts.append(f"Error parsing Wiki results: {result}")
            else:
                # 实时状态或其他工具结果，不带序号，作为直采信息
                new_contexts.append(f"Tool [{tool_name}] output:\n{result}")
        else:
            new_contexts.append(f"Error: Tool {tool_name} not found.")
            
    return {
        "context": new_contexts,
        "next_node": "reflector"
    }

async def coordinator(state: AgentState):
    """任务分发与协调。"""
    messages = state["messages"]
    summary = state.get("summary", "")
    
    prompt = COORDINATOR_PROMPT
    if summary:
        prompt += f"\n\nContext Summary: {summary}"
        
    # 构建请求消息列表
    req_messages = [SystemMessage(content=prompt)]
    # 如果有 context，注入作为短期记忆参考
    if state.get("context"):
        context_str = "\n".join(state["context"])
        req_messages.append(SystemMessage(content=f"已收集的信息:\n{context_str}"))
    
    req_messages.extend(messages)
        
    response = await llm_with_tools.ainvoke(req_messages)
    
    if response.tool_calls:
        # 模型决定调用工具
        return {
            "next_node": "tools",
            "messages": [response],
            "context": [f"Action: 调用工具 {tc['name']} 参数 {tc['args']}" for tc in response.tool_calls]
        }
    
    # 无需工具，直接生成最终回答
    return {"next_node": "final_generator", "messages": [response]}

async def reflector(state: AgentState):
    """结果反思与质检。仅对带 [WIKI_N] 序号的 Wiki 检索结果进行采信筛选。"""
    context_str = "\n".join(state["context"])
    
    response = await llm.ainvoke([
        SystemMessage(content=REFLECTOR_PROMPT),
        HumanMessage(content=f"Collected Content (Wiki results have [WIKI_N] IDs):\n{context_str}\n\nUser Question: {state['messages'][-1].content}")
    ])
    
    try:
        # 去除可能存在的 markdown 格式
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        
        data = json.loads(content)
        analysis = ReflectorAnalysis(**data)
        
        if analysis.next_step == "continue" and state["reflection_count"] < 3:
            return {
                "next_node": "coordinator", 
                "reflection_count": state["reflection_count"] + 1,
                "context": [f"Reflect: {analysis.critique}"]
            }
        
        # 将筛选出的序号存入 context 标记中，格式为 SELECTED_WIKI_INDICES: 1,2,3
        indices_str = ",".join(map(str, analysis.relevant_indices))
        refined_marker = f"SELECTED_WIKI_INDICES: {indices_str}"
        return {
            "next_node": "final_generator",
            "context": [refined_marker]
        }
    except Exception as e:
        print(f"Reflector error: {e}")
        return {"next_node": "final_generator"}

async def final_generator(state: AgentState):
    """最终回答生成。组合筛选后的 Wiki 片段与全部实时环境数据。"""
    # 查找是否有筛选出的 Wiki 序号 (SELECTED_WIKI_INDICES)
    selected_indices = []
    for item in reversed(state["context"]):
        if item.startswith("SELECTED_WIKI_INDICES: "):
            indices_str = item.replace("SELECTED_WIKI_INDICES: ", "", 1)
            if indices_str:
                try:
                    selected_indices = [int(idx.strip()) for idx in indices_str.split(",")]
                except:
                    pass
            break
            
    # 提取：(1) 采信的 Wiki 片段 + (2) 非 Wiki 工具的实时数据
    refined_parts = []
    for ctx in state["context"]:
        if ctx.startswith("[WIKI_"):
            # 检查是否在采信列表中
            try:
                idx = int(ctx.split("_")[1].split("]")[0])
                if idx in selected_indices:
                    refined_parts.append(ctx)
            except:
                pass
        elif not ctx.startswith("SELECTED_WIKI_INDICES: ") and not ctx.startswith("Reflect: "):
            # 实时状态数据等直接加入
            refined_parts.append(ctx)
            
    context_to_use = "\n".join(refined_parts)
    
    prompt = [
        SystemMessage(content=FINAL_GENERATOR_PROMPT + "\n\n请直接输出回答内容，不要包含 JSON 格式包裹。"),
        HumanMessage(content=f"已收集的背景知识与环境状态:\n{context_to_use}\n\n当前用户问题:\n{state['messages'][-1].content}")
    ]
    
    response = await llm.ainvoke(prompt)
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
    
    if len(state["messages"]) < 10:
        return {"messages": []}

    response = await llm.ainvoke([
        SystemMessage(content=SUMMARIZER_PROMPT),
        HumanMessage(content=str(trimmed_messages))
    ])
    
    return {
        "summary": response.content
    }
