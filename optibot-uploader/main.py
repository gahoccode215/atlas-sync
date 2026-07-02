"""
main.py — Daily sync pipeline: scrape Zendesk → upload delta to OpenAI Vector Store.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from upload_to_vector_store import get_or_create_vector_store, upload

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ARTICLES_DIR = Path(os.getenv("ARTICLES_DIR", "/app/articles"))
JAR_PATH     = Path(os.getenv("JAR_PATH",     "/app/ingestor.jar"))


def run_scraper():
    log.info("STEP 1: Scraping Zendesk articles")
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    if not JAR_PATH.exists():
        log.error("JAR not found: %s", JAR_PATH)
        sys.exit(1)

    result = subprocess.run(
        ["java", f"-Dingestor.output.dir={ARTICLES_DIR}", "-jar", str(JAR_PATH)],
        text=True,
        timeout=3600,
    )

    if result.returncode != 0:
        log.error("Scraper failed with code %d", result.returncode)
        sys.exit(1)

    log.info("Articles on disk: %d", len(list(ARTICLES_DIR.glob("*.md"))))


def run_uploader():
    log.info("STEP 2: Uploading delta to Vector Store")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.error("OPENAI_API_KEY not set.")
        sys.exit(1)

    client  = OpenAI(api_key=api_key)
    vs      = get_or_create_vector_store(client, os.getenv("VECTOR_STORE_NAME", "optibot-knowledge-base"))
    result  = upload(client, vs.id, ARTICLES_DIR)

    if len(result) == 2:
        manifest, skipped = result
        completed = chunks_est = 0
    else:
        manifest, skipped, completed, chunks_est = result

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


if __name__ == "__main__":
    load_dotenv()
    run_scraper()
    run_uploader()