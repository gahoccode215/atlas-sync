"""
OptiBot - Sanity check: ChromaDB (local) + DeepSeek API
Dùng openai SDK với base_url DeepSeek — không cần cài thêm package
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "./chroma_db"
COLLECTION  = "optisigns_docs"

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
- Tone: helpful, factual, concise.
- Only answer using the uploaded docs.
- Max 5 bullet points; else link to the doc.
- Cite up to 3 "Article URL:" lines per reply."""

# ── Load ChromaDB ─────────────────────────────────────────────────────────────
print("── Loading vector store ──")
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = chroma_client.get_collection(name=COLLECTION, embedding_function=ef)
print(f"✓ {collection.count()} chunks loaded")

# ── Query ChromaDB ────────────────────────────────────────────────────────────
QUESTION = "How do I add a YouTube video?"
print(f"\n── Query: '{QUESTION}' ──")

results = collection.query(
    query_texts=[QUESTION],
    n_results=5,
    include=["documents", "metadatas"]
)

chunks = results["documents"][0]
metas  = results["metadatas"][0]
urls   = list(dict.fromkeys(
    m["source_url"] for m in metas if m.get("source_url")
))

context   = "\n\n---\n\n".join(chunks)
url_block = "\n".join(f"Article URL: {u}" for u in urls[:3])

print(f"✓ {len(chunks)} chunks retrieved")
for u in urls[:3]:
    print(f"  → {u}")

# ── Gọi DeepSeek API ─────────────────────────────────────────────────────────
print("\n── Calling DeepSeek API ──")
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Context from OptiSigns docs:

{context}

{url_block}

Question: {QUESTION}"""}
    ],
    temperature=0.1,
    max_tokens=512
)

# ── In kết quả ───────────────────────────────────────────────────────────────
answer = response.choices[0].message.content

print("\n" + "═"*60)
print(f"Q: {QUESTION}")
print("─"*60)
print(answer)
print("═"*60)
print(f"\nTokens used: {response.usage.total_tokens}")
print("\n✅ Sanity check hoàn thành! Chụp screenshot màn hình này.")