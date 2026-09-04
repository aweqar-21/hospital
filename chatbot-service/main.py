"""一键启动入口 —— python main.py 或双击运行。"""
import os
import sys

# 确保工作目录为项目根目录（无论从哪里执行）
project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.routes:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=8000,
        reload=False,
        access_log=False,
    )
