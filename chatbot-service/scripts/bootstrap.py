"""首次启动初始化脚本 —— 下载模型、初始化向量库、创建必要目录。"""
import os
import sys

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings


def init_directories() -> None:
    """创建必要的数据目录。"""
    dirs = [
        "./data",
        "./data/vector_store",
        "./logs",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"✓ 目录已就绪: {d}")


def init_vector_store() -> None:
    """初始化向量数据库。"""
    settings = get_settings()
    print(f"初始化向量数据库 (type={settings.VECTOR_DB_TYPE})...")
    try:
        from knowledge.vector_store import VectorStore
        store = VectorStore()
        print(f"✓ 向量数据库已初始化，当前文档数: {store.count()}")
    except Exception as e:  # noqa: BLE001 - bootstrap reports any optional backend failure
        print(f"⚠ 向量数据库初始化失败: {e}")


def check_environment() -> None:
    """检查必要的环境变量。"""
    settings = get_settings()
    checks = [
        ("LLM_API_KEY", settings.LLM_API_KEY, "用于调用大语言模型"),
        ("REDIS_HOST", settings.REDIS_HOST, "用于会话缓存"),
    ]
    all_ok = True
    for name, value, description in checks:
        status = "✓" if value else "⚠ 未配置"
        print(f"  {status} {name}: {description}")
        if not value and name == "LLM_API_KEY":
            all_ok = False
    if not all_ok:
        print("\n⚠ 请在 .env 文件中配置必要的环境变量后重新运行。")
    else:
        print("\n✓ 环境变量检查通过。")


def main() -> None:
    print("=" * 50)
    print("Chatbot 初始化脚本")
    print("=" * 50)

    print("\n[1/3] 创建目录...")
    init_directories()

    print("\n[2/3] 检查环境变量...")
    check_environment()

    print("\n[3/3] 初始化向量数据库...")
    init_vector_store()

    print("\n" + "=" * 50)
    print("初始化完成！运行以下命令启动服务：")
    print("  uvicorn api.routes:app --host 127.0.0.1 --port 8000 --no-access-log")
    print("=" * 50)


if __name__ == "__main__":
    main()
