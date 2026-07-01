"""
OptiBot Daily Job - Orchestrator
1. Chạy Java scraper (Spring Boot jar)
2. Detect delta (hash comparison)
3. Upload only new/updated lên ChromaDB
Log: added, updated, skipped, failed
"""

import os
import sys
import json
import hashlib
import pathlib
import subprocess
import time
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
ARTICLES_DIR  = pathlib.Path(os.getenv("ARTICLES_DIR", "./articles"))
STATE_FILE    = pathlib.Path(os.getenv("STATE_FILE", "./state.json"))
CHROMA_DIR    = os.getenv("CHROMA_DIR", "./chroma_db")
COLLECTION    = "optisigns_docs"
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100
JAR_PATH      = pathlib.Path(os.getenv("JAR_PATH", "./ingestor-service.jar"))

def log(msg): print(msg, flush=True)

# ── Bước 1: Chạy Java scraper ─────────────────────────────────────────────────
def run_java_scraper():
    log("\n── Step 1: Running Java scraper ──")
    cmd = [
        "java", "-jar", str(JAR_PATH),
        f"--ingestor.output.dir={ARTICLES_DIR}"
    ]
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        log(f"❌ Java scraper failed (exit {result.returncode})")
        sys.exit(1)
    md_files = list(ARTICLES_DIR.glob("*.md"))
    log(f"✓ Scraper done: {len(md_files)} files in {ARTICLES_DIR}")
    return md_files

# ── Bước 2: Delta detection ───────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

# ── Bước 3: Chunking + upload ─────────────────────────────────────────────────
def chunk_text(text: str) -> list[str]:
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def get_source_url(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("source_url:"):
            return line.split("source_url:", 1)[-1].strip()
    return ""

def upload_delta(md_files: list[pathlib.Path], state: dict, collection) -> dict:
    log(f"\n── Step 2: Delta detection & upload ──")

    added = updated = skipped = failed = 0

    for md_file in md_files:
        try:
            content      = md_file.read_text(encoding="utf-8")
            file_hash    = md5(content)
            file_id      = md_file.stem   # slug-articleid
            prev         = state.get(file_id, {})

            if prev.get("hash") == file_hash:
                skipped += 1
                continue

            is_new    = file_id not in state
            source_url = get_source_url(content)
            chunks    = chunk_text(content)

            collection.upsert(
                ids=[f"{file_id}_chunk_{j}" for j in range(len(chunks))],
                documents=chunks,
                metadatas=[{
                    "source_url": source_url,
                    "filename":   md_file.name,
                    "chunk_index": j
                } for j in range(len(chunks))]
            )

            state[file_id] = {"hash": file_hash}

            if is_new:
                added += 1
                log(f"  [ADD] {md_file.name}")
            else:
                updated += 1
                log(f"  [UPD] {md_file.name}")

        except Exception as e:
            log(f"  [ERR] {md_file.name}: {e}")
            failed += 1

    return {"added": added, "updated": updated,
            "skipped": skipped, "failed": failed}

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    start_time = time.time()
    log("═"*50)
    log("OptiBot Daily Job starting...")
    log("═"*50)

    # Step 1: Scrape
    md_files = run_java_scraper()

    # Step 2 & 3: Delta + upload
    state = load_state()

    chroma = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = chroma.get_or_create_collection(
        name=COLLECTION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    counts = upload_delta(md_files, state, collection)
    save_state(state)

    elapsed = time.time() - start_time
    log(f"""
{'═'*50}
── Daily job complete ({elapsed:.1f}s) ──
  added   : {counts['added']}
  updated : {counts['updated']}
  skipped : {counts['skipped']}
  failed  : {counts['failed']}
  total   : {len(md_files)}
{'═'*50}""")

if __name__ == "__main__":
    main()