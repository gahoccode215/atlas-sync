"""
upload_to_vector_store.py
Upload Markdown articles lên OpenAI Vector Store.

Chunking strategy
-----------------
Dùng static chunking: max_chunk_size_tokens=800, chunk_overlap_tokens=400.
Lý do: bài viết support có cấu trúc rõ (heading + đoạn ngắn), 800 tokens
vừa đủ giữ nguyên một ý hoàn chỉnh, overlap 400 giúp retrieval không bị
đứt giữa câu khi chunk bị cắt tại ranh giới.

Cách chạy
---------
  cp .env.sample .env        # điền OPENAI_API_KEY và MARKDOWN_DIR
  pip install -r requirements.txt
  python upload_to_vector_store.py
"""

import hashlib
import json
import logging
import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

MANIFEST_FILE = Path(__file__).parent / ".manifest.json"
BATCH_SIZE = 20          # số file upload song song trong một lần gọi API
TOKENS_PER_WORD = 1.3    # ước lượng token/từ để tính số chunk
MAX_CHUNK_TOKENS = 800
OVERLAP_TOKENS = 400


# ---------------------------------------------------------------------------
# Manifest – ghi nhớ hash để chỉ upload file mới/thay đổi (delta sync)
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def save_manifest(data: dict):
    MANIFEST_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Ước lượng số chunk (OpenAI không trả về chunk count qua API)
# ---------------------------------------------------------------------------

def estimate_chunks(path: Path) -> int:
    words = len(path.read_text(encoding="utf-8", errors="ignore").split())
    total_tokens = int(words * TOKENS_PER_WORD)
    if total_tokens <= MAX_CHUNK_TOKENS:
        return 1
    step = MAX_CHUNK_TOKENS - OVERLAP_TOKENS   # 400 token step
    return math.ceil((total_tokens - OVERLAP_TOKENS) / step)


# ---------------------------------------------------------------------------
# Vector Store helpers
# ---------------------------------------------------------------------------

def get_or_create_vector_store(client: OpenAI, name: str):
    """Tìm vector store theo tên; tạo mới nếu chưa tồn tại."""
    page = client.vector_stores.list(limit=100)
    for vs in page.data:
        if vs.name == name:
            log.info("Found existing vector store '%s' (id=%s)", name, vs.id)
            return vs

    vs = client.vector_stores.create(
        name=name,
        chunking_strategy={
            "type": "static",
            "static": {
                "max_chunk_size_tokens": MAX_CHUNK_TOKENS,
                "chunk_overlap_tokens": OVERLAP_TOKENS,
            },
        },
    )
    log.info("Created vector store '%s' (id=%s)", name, vs.id)
    return vs


def upload_batch(client: OpenAI, vs_id: str, paths: list[Path]) -> int:
    """
    Upload một batch file lên vector store.
    Trả về số file đã completed thành công.
    """
    file_handles = [open(p, "rb") for p in paths]
    try:
        batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vs_id,
            files=file_handles,
        )
    finally:
        for fh in file_handles:
            fh.close()

    if batch.file_counts.failed > 0:
        log.warning("  %d file(s) failed in this batch", batch.file_counts.failed)

    return batch.file_counts.completed


# ---------------------------------------------------------------------------
# Main upload logic
# ---------------------------------------------------------------------------

def upload(client: OpenAI, vs_id: str, markdown_dir: Path):
    md_files = sorted(markdown_dir.glob("*.md"))
    if not md_files:
        log.error("No .md files found in: %s", markdown_dir.resolve())
        sys.exit(1)

    log.info("Found %d .md files in %s", len(md_files), markdown_dir.resolve())

    manifest = load_manifest()

    # Phân loại: mới, thay đổi, không đổi
    to_upload: list[Path] = []
    skipped = 0
    for path in md_files:
        current_hash = sha256_of(path)
        if manifest.get(path.name) == current_hash:
            skipped += 1
        else:
            to_upload.append(path)

    log.info("To upload: %d  |  Skipped (unchanged): %d", len(to_upload), skipped)

    if not to_upload:
        log.info("Nothing to upload – all files already up to date.")
        return manifest, skipped

    # Upload theo batch
    total_completed = 0
    total_chunks_est = 0
    num_batches = math.ceil(len(to_upload) / BATCH_SIZE)

    for i in range(0, len(to_upload), BATCH_SIZE):
        batch_paths = to_upload[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        log.info("Uploading batch %d/%d (%d files)...", batch_num, num_batches, len(batch_paths))

        completed = upload_batch(client, vs_id, batch_paths)
        total_completed += completed

        for path in batch_paths:
            manifest[path.name] = sha256_of(path)
            total_chunks_est += estimate_chunks(path)

        log.info("  Batch %d done: %d/%d files completed", batch_num, completed, len(batch_paths))

    save_manifest(manifest)
    log.info("Manifest saved to %s", MANIFEST_FILE)

    return manifest, skipped, total_completed, total_chunks_est


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.error("OPENAI_API_KEY chưa được set. Tạo file .env từ .env.sample.")
        sys.exit(1)

    markdown_dir = Path(os.getenv("MARKDOWN_DIR", "../ingestor-service/articles"))
    if not markdown_dir.exists():
        log.error("MARKDOWN_DIR không tồn tại: %s", markdown_dir.resolve())
        sys.exit(1)

    vs_name = os.getenv("VECTOR_STORE_NAME", "optibot-knowledge-base")

    client = OpenAI(api_key=api_key)

    vs = get_or_create_vector_store(client, vs_name)

    result = upload(client, vs.id, markdown_dir)

    # result có thể là (manifest, skipped) hoặc (manifest, skipped, completed, chunks)
    if len(result) == 2:
        manifest, skipped = result
        completed = 0
        chunks_est = 0
    else:
        manifest, skipped, completed, chunks_est = result

    # -----------------------------------------------------------------------
    # Summary log – đây là phần đề bài yêu cầu "log how many files/chunks"
    # -----------------------------------------------------------------------
    print()
    print("=" * 55)
    print(f"  Vector Store  : {vs.id}")
    print(f"  Store name    : {vs.name}")
    print("-" * 55)
    print(f"  Files uploaded (this run)  : {completed}")
    print(f"  Files skipped (no change)  : {skipped}")
    print(f"  Total files tracked        : {len(manifest)}")
    print(f"  Estimated chunks embedded  : {chunks_est}")
    print(f"  Chunk size / overlap       : {MAX_CHUNK_TOKENS} / {OVERLAP_TOKENS} tokens")
    print("=" * 55)
    print()
    print("Next step: gắn Vector Store này vào Assistant trong Playground:")
    print(f"  https://platform.openai.com/playground/assistants")
    print(f"  Vector Store ID: {vs.id}")


if __name__ == "__main__":
    main()