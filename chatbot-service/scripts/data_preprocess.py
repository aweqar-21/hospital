"""知识库文档清洗与向量化脚本。"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def preprocess_csv(csv_path: str) -> None:
    """读取 QA pairs CSV 并写入向量库。"""
    from knowledge.knowledge_retriever import KnowledgeRetriever

    if not os.path.exists(csv_path):
        print(f"文件不存在: {csv_path}")
        return

    retriever = KnowledgeRetriever()
    contents: list[str] = []
    metadatas: list[dict] = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = row.get("question", "")
            answer = row.get("answer", "")
            category = row.get("category", "")
            if question and answer:
                content = f"Q: {question}\nA: {answer}"
                contents.append(content)
                metadatas.append({"source": csv_path, "category": category, "type": "qa_pair"})

    if contents:
        print(f"向量化 {len(contents)} 条问答对...")
        await retriever.add_knowledge(contents, metadatas)
        print(f"✓ 完成，已写入向量库。")
    else:
        print("未找到有效的问答对。")


async def preprocess_text_dir(dir_path: str) -> None:
    """读取目录下所有 txt/md 文件并写入向量库。"""
    from knowledge.knowledge_retriever import KnowledgeRetriever

    if not os.path.isdir(dir_path):
        print(f"目录不存在: {dir_path}")
        return

    retriever = KnowledgeRetriever()
    count = 0

    for root, _, files in os.walk(dir_path):
        for filename in files:
            if filename.endswith((".txt", ".md")):
                path = os.path.join(root, filename)
                try:
                    with open(path, encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    print(f"⚠ 读取失败: {path} ({e})")
                    continue

                if content.strip():
                    # 按段落切分（简单分块）
                    chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 50]
                    if not chunks:
                        chunks = [content]
                    metadatas = [{"source": path, "filename": filename}] * len(chunks)
                    await retriever.add_knowledge(chunks, metadatas)
                    count += len(chunks)
                    print(f"  处理: {filename} ({len(chunks)} 块)")

    print(f"✓ 共处理 {count} 个文本块。")


def main() -> None:
    import asyncio

    print("=" * 50)
    print("知识库数据预处理脚本")
    print("=" * 50)

    # 默认处理 knowledge/documents/ 目录下的文件
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "knowledge", "documents")

    print(f"\n[1] 处理 CSV 文件...")
    csv_path = os.path.join(docs_dir, "qa_pairs.csv")
    asyncio.run(preprocess_csv(csv_path))

    print(f"\n[2] 处理文本文件...")
    asyncio.run(preprocess_text_dir(docs_dir))

    print("\n预处理完成。")


if __name__ == "__main__":
    main()
