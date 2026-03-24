import os
import sys
import json
import urllib.parse
import chainlit as cl
from langchain_core.messages import HumanMessage, BaseMessage
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from core.graph import graph

@cl.on_chat_start
async def on_chat_start():
    """对话开始时的初始化逻辑。"""
    cl.user_session.set("thread_id", f"cl_chat_{os.urandom(4).hex()}")
    await cl.Message(content="你好！我是 WikiRag-Agent，你的百科智能管家。请问有什么可以帮您的？").send()

@cl.on_message
async def on_message(message: cl.Message):
    """处理用户发送的消息。"""
    thread_id = cl.user_session.get("thread_id")
    config = {"configurable": {"thread_id": thread_id}}
    
    # 构造 LangGraph 输入
    inputs = {
        "messages": [HumanMessage(content=message.content)],
        "reflection_count": 0,
        "context": [],
        "documents": []
    }
    
    # 准备一个变量记录累积的内容
    full_content = ""
    msg = cl.Message(content="")
    
    # 用于存储最终状态
    final_state = None
    
    # 使用 astream 运行图逻辑
    async for mode, chunk in graph.astream(
        inputs, 
        config=config, 
        stream_mode=["messages", "values"]
    ):
        if mode == "messages":
            msg_chunk, metadata = chunk
            if metadata.get("langgraph_node") == "final_generator":
                if hasattr(msg_chunk, "content"):
                    token = msg_chunk.content
                    full_content += token
                    # 直接流式输出
                    await msg.stream_token(token)
        
        elif mode == "values":
            final_state = chunk

    # 处理 UI 元素
    elements = []
    
    # 处理参考来源 (Documents) - 渲染为可点击链接并解码
    if final_state and "documents" in final_state and final_state["documents"]:
        unique_sources = list(set(final_state["documents"]))
        links = []
        for i, url in enumerate(unique_sources):
            # 对 URL 进行解码，处理中文文件名
            decoded_url = urllib.parse.unquote(url)
            # 提取文件名
            name = decoded_url.replace("\\", "/").split("/")[-1] or f"Source {i+1}"
            if name.endswith(".md"):
                name = name[:-3]
            links.append(f"[{name}]({url})")
        
        doc_content = " | ".join(links)
        elements.append(
            cl.Text(name="📚参考", content=doc_content, display="inline")
        )

    # 发送最终消息
    msg.content = full_content
    msg.elements = elements
    await msg.send()

if __name__ == "__main__":
    # 提示用户如何运行
    print("请使用以下命令启动 Chainlit UI:")
    print("chainlit run src/app.py -w")
