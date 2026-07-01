"""
OptiBot - Build local vector store từ 402 file .md
Stack: ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
Hoàn toàn free, không cần API key
"""

import os
import pathlib
import time
from chromadb.utils import embedding_functions
import chromadb
from dotenv import load_dotenv

load_dotenv()

ARTICLES_DIR = os.getenv("ARTICLES_DIR", "../ingestor-service/articles")
CHROMA_DIR   = "./chroma_db"
COLLECTION   = "optisigns_docs"
CHUNK_SIZE   = 800   # ký tự mỗi chunk
CHUNK_OVERLAP= 100

# ── Khởi tạo ChromaDB ─────────────────────────────────────────────────────────
print("── Khởi tạo ChromaDB ──")
client = chromadb.PersistentClient(path=CHROMA_DIR)

# Dùng sentence-transformers/all-MiniLM-L6-v2 (download tự động ~80MB)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = client.get_or_create_collection(
    name=COLLECTION,
    embedding_function=ef,
    metadata={"hnsw:space": "cosine"}
)

# ── Đọc file .md ──────────────────────────────────────────────────────────────
articles_path = pathlib.Path(ARTICLES_DIR)
md_files = sorted(articles_path.glob("*.md"))
print(f"Tìm thấy {len(md_files)} file .md")

# ── Chunking ──────────────────────────────────────────────────────────────────
def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks

# ── Index từng file ───────────────────────────────────────────────────────────
print(f"\n── Bắt đầu embed & index ──")
total_chunks = 0
failed = 0

for i, md_file in enumerate(md_files, 1):
    try:
        content = md_file.read_text(encoding="utf-8")

        # Lấy source_url từ frontmatter
        source_url = ""
        for line in content.splitlines():
            if line.startswith("source_url:"):
                source_url = line.split("source_url:")[-1].strip()
                break

        # Chia chunk
        chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)

        # Thêm vào ChromaDB
        collection.upsert(
            ids=[f"{md_file.stem}_chunk_{j}" for j in range(len(chunks))],
            documents=chunks,
            metadatas=[{
                "source_url": source_url,
                "filename": md_file.name,
                "chunk_index": j
            } for j in range(len(chunks))]
        )

        total_chunks += len(chunks)
        print(f"[{i:3d}/{len(md_files)}] ✓ {md_file.name} → {len(chunks)} chunks")

    except Exception as e:
        print(f"[{i:3d}/{len(md_files)}] ✗ FAILED {md_file.name}: {e}")
        failed += 1

# ── Kết quả ───────────────────────────────────────────────────────────────────
print(f"""
{'═'*50}
── Kết quả ──
  Tổng file         : {len(md_files)}
  File thất bại     : {failed}
  Tổng chunks       : {total_chunks}
  Vector store path : {CHROMA_DIR}
── Chunking strategy ──
  Chunk size        : {CHUNK_SIZE} ký tự
  Chunk overlap     : {CHUNK_OVERLAP} ký tự
  Lý do             : Giữ context heading/paragraph,
                      overlap tránh mất thông tin ở biên chunk
{'═'*50}
""")