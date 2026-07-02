"""
upload_to_vector_store.py

Syncs local Markdown articles to an OpenAI Vector Store.
Only uploads new or changed files (delta sync via SHA-256 manifest).

Chunking: static, 800 tokens / 400 overlap.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

MANIFEST_FILE    = Path(__file__).parent / ".manifest.json"
BATCH_SIZE       = 20
TOKENS_PER_WORD  = 1.3
MAX_CHUNK_TOKENS = 800
OVERLAP_TOKENS   = 400


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def save_manifest(data: dict):
    MANIFEST_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def estimate_chunks(path: Path) -> int:
    words = len(path.read_text(encoding="utf-8", errors="ignore").split())
    total_tokens = int(words * TOKENS_PER_WORD)
    if total_tokens <= MAX_CHUNK_TOKENS:
        return 1
    return math.ceil((total_tokens - OVERLAP_TOKENS) / (MAX_CHUNK_TOKENS - OVERLAP_TOKENS))


def get_or_create_vector_store(client: OpenAI, name: str):
    for vs in client.vector_stores.list(limit=100).data:
        if vs.name == name:
            log.info("Reusing vector store '%s' (%s)", name, vs.id)
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
    log.info("Created vector store '%s' (%s)", name, vs.id)
    return vs


def upload_batch(client: OpenAI, vs_id: str, paths: list[Path]) -> int:
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
        log.warning("  %d file(s) failed", batch.file_counts.failed)

    return batch.file_counts.completed

def upload(client: OpenAI, vs_id: str, markdown_dir: Path):
    md_files = sorted(markdown_dir.glob("*.md"))
    if not md_files:
        log.error("No .md files found in: %s", markdown_dir.resolve())
        sys.exit(1)

    log.info("Found %d .md files", len(md_files))

    manifest = load_manifest()

    to_upload: list[Path] = []
    skipped = 0
    for path in md_files:
        if manifest.get(path.name) == sha256_of(path):
            skipped += 1
        else:
            to_upload.append(path)

    log.info("To upload: %d  |  Skipped: %d", len(to_upload), skipped)

    if not to_upload:
        log.info("Nothing to upload – all files up to date.")
        return manifest, skipped

    total_completed = 0
    total_chunks    = 0
    num_batches     = math.ceil(len(to_upload) / BATCH_SIZE)

    for i in range(0, len(to_upload), BATCH_SIZE):
        batch_paths = to_upload[i : i + BATCH_SIZE]
        batch_num   = i // BATCH_SIZE + 1
        log.info("Batch %d/%d (%d files)...", batch_num, num_batches, len(batch_paths))

        completed = upload_batch(client, vs_id, batch_paths)
        total_completed += completed

        for path in batch_paths:
            manifest[path.name] = sha256_of(path)
            total_chunks += estimate_chunks(path)

        log.info("  Done: %d/%d completed", completed, len(batch_paths))

    save_manifest(manifest)

    return manifest, skipped, total_completed, total_chunks


def main():
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.error("OPENAI_API_KEY is not set.")
        sys.exit(1)

    markdown_dir = Path(os.getenv("MARKDOWN_DIR", "../ingestor-service/articles"))
    if not markdown_dir.exists():
        log.error("MARKDOWN_DIR not found: %s", markdown_dir.resolve())
        sys.exit(1)

    vs_name = os.getenv("VECTOR_STORE_NAME", "optibot-knowledge-base")
    client  = OpenAI(api_key=api_key)
    vs      = get_or_create_vector_store(client, vs_name)
    result  = upload(client, vs.id, markdown_dir)

    if len(result) == 2:
        manifest, skipped = result
        completed = chunks_est = 0
    else:
        manifest, skipped, completed, chunks_est = result

    print()
    print("=" * 55)
    print(f"  Vector Store  : {vs.id}")
    print("-" * 55)
    print(f"  Uploaded      : {completed}")
    print(f"  Skipped       : {skipped}")
    print(f"  Total tracked : {len(manifest)}")
    print(f"  Chunks (est.) : {chunks_est}")
    print(f"  Chunk size    : {MAX_CHUNK_TOKENS} tokens / {OVERLAP_TOKENS} overlap")
    print("=" * 55)


if __name__ == "__main__":
    main()