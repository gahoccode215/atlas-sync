"""
main.py — Daily sync pipeline
  1. Chạy Java ingestor JAR để scrape Zendesk → .md files
  2. Upload delta lên OpenAI Vector Store

Dùng trong Docker:
  docker run -e OPENAI_API_KEY=sk-... ghcr.io/<you>/<repo>:latest
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from upload_to_vector_store import get_or_create_vector_store, upload

# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

ARTICLES_DIR = Path(os.getenv("ARTICLES_DIR", "/app/articles"))
JAR_PATH     = Path(os.getenv("JAR_PATH", "/app/ingestor.jar"))


# ---------------------------------------------------------------------------
# Step 1 – Java scraper
# ---------------------------------------------------------------------------

def run_scraper():
    log.info("━━━ STEP 1: Scraping Zendesk articles ━━━")
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "java",
        # Override Spring Boot property so JAR writes to the shared dir
        f"-Dingestor.output.dir={ARTICLES_DIR}",
        "-jar", str(JAR_PATH),
    ]
    log.info("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, text=True, timeout=3600)

    if result.returncode != 0:
        log.error("Scraper exited with code %d — aborting.", result.returncode)
        sys.exit(1)

    md_count = len(list(ARTICLES_DIR.glob("*.md")))
    log.info("Scraper done. Articles on disk: %d", md_count)


# ---------------------------------------------------------------------------
# Step 2 – Upload delta
# ---------------------------------------------------------------------------

def run_uploader():
    log.info("━━━ STEP 2: Uploading delta to Vector Store ━━━")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.error("OPENAI_API_KEY not set.")
        sys.exit(1)

    vs_name = os.getenv("VECTOR_STORE_NAME", "optibot-knowledge-base")
    client  = OpenAI(api_key=api_key)
    vs      = get_or_create_vector_store(client, vs_name)
    result  = upload(client, vs.id, ARTICLES_DIR)

    # upload() returns (manifest, skipped) or (manifest, skipped, completed, chunks)
    if len(result) == 2:
        manifest, skipped = result
        completed = chunks_est = 0
    else:
        manifest, skipped, completed, chunks_est = result

    # ── Final summary (đề bài yêu cầu log added/updated/skipped) ──
    print()
    print("=" * 55)
    print("  DAILY SYNC COMPLETE")
    print("-" * 55)
    print(f"  Articles on disk   : {len(list(ARTICLES_DIR.glob('*.md')))}")
    print(f"  Uploaded (delta)   : {completed}")
    print(f"  Skipped (no change): {skipped}")
    print(f"  Total tracked      : {len(manifest)}")
    print(f"  Est. chunks embed  : {chunks_est}")
    print(f"  Vector Store       : {vs.id}")
    print("=" * 55)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    load_dotenv()
    run_scraper()
    run_uploader()