import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
from dotenv import load_dotenv

# 确保 src 目录在路径中
sys.path.append(os.path.dirname(__file__))

# 加载环境变量
load_dotenv()

from core.graph import graph

app = FastAPI(
    title="WikiRag-Agent API",
    version="1.0",
    description="Universal General-Aware RAG Agent API powered by LangGraph & LangServe",
)

# 设置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 添加路由
# 注意：LangGraph 对象可以直接作为 Runnable 传入
add_routes(
    app,
    graph,
    path="/agent",
    playground_type="chat", # 针对对话场景使用 chat 类型的 Playground
)

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    # 默认监听 0.0.0.0 以支持容器化部署
    uvicorn.run(app, host="0.0.0.0", port=port)
