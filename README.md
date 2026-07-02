# OptiBot

AI support chatbot for OptiSigns, built with a Java Zendesk scraper and OpenAI Vector Store.

## Setup

```bash
git clone https://github.com/gahoccode215/atlas-sync
cd atlas-sync
cp optibot-uploader/.env.sample optibot-uploader/.env
# Replace your OPENAI_API_KEY
```

## How to Run Locally

**1. Scrape articles (Java):**
```bash
cd ingestor-service
mvn clean package -DskipTests
java -jar target/*.jar
# → saves 402 .md files to ingestor-service/articles/
```

**2. Upload to Vector Store (Python):**
```bash
cd optibot-uploader
pip install -r requirements.txt
python upload_to_vector_store.py
# → logs: Added X | Updated X | Skipped X | Chunks ~749
```

**3. Run full pipeline via Docker:**
```bash
docker build -t optibot-sync .
docker run -e OPENAI_API_KEY=sk-... optibot-sync
```

**Chunking strategy:** Static chunking — 800 tokens/chunk, 400 overlap. Delta detection via SHA-256 manifest: only new/changed articles are uploaded.

## Daily Job Logs

Runs every day at 02:00 UTC via GitHub Actions.

🔗 **https://github.com/gahoccode215/atlas-sync/actions**

## Assistant — Sample Answer

> **Q: How do I add a YouTube video?**

![Source code and test script](https://github.com/gahoccode215/atlas-sync/blob/main/screenshots/quick-sanity.png)