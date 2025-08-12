# === embedder.py (revised for latest OpenAI + ChromaDB + optional caching + reuse in retrieval) ===
import os
import json
import openai
from chromadb import PersistentClient
from tqdm import tqdm

openai.api_key = os.getenv("OPENAI_API_KEY")

SUMMARY_FILE = "data/book_summaries.txt"
CACHE_FILE = "embeddings/cache.json"
CHROMA_PATH = "embeddings/chroma_book_summaries"
COLLECTION_NAME = "books"

# Load summaries

def load_summaries(file_path=SUMMARY_FILE):
    summaries = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_title = None
    current_summary = []
    for line in lines:
        line = line.strip()
        if line.startswith("## Title: "):
            if current_title and current_summary:
                summaries.append({
                    "title": current_title,
                    "content": " ".join(current_summary)
                })
            current_title = line.replace("## Title: ", "")
            current_summary = []
        elif line:
            current_summary.append(line)

    if current_title and current_summary:
        summaries.append({
            "title": current_title,
            "content": " ".join(current_summary)
        })
    return summaries

# Load or initialize cache

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# Embed using OpenAI (with external access for reuse)

def get_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Embedding with cache (used by retriever too)

def get_embedding_with_cache(text, key, cache):
    if key in cache:
        return cache[key]
    embedding = get_embedding(text)
    cache[key] = embedding
    save_cache(cache)
    return embedding

# Store in ChromaDB

def store_in_chroma(summaries):
    cache = load_cache()
    chroma_client = PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    new_count = 0

    for i, summary in enumerate(tqdm(summaries, desc="Embedding summaries")):
        title = summary["title"]
        content = summary["content"]

        if title in cache:
            embedding = cache[title]
        else:
            embedding = get_embedding(content)
            cache[title] = embedding
            new_count += 1

        collection.add(
            documents=[content],
            metadatas=[{"title": title}],
            ids=[f"book_{i}"]
        )

    save_cache(cache)
    print(f"✅ Stored {len(summaries)} book summaries in ChromaDB.")
    print(f"🧠 Used {len(cache)} cached, {new_count} new embeddings.")

# Entry point
if __name__ == "__main__":
    summaries = load_summaries()
    store_in_chroma(summaries)
