import os
import openai
from chromadb import PersistentClient


#Set API key
openai.api_key = os.getenv("OPENAI_API_KEY")

#Path to book_summaries
SUMMARY_FILE = "data/book_summaries.txt"

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

# Embed a single text using OpenAI
def get_embedding(text):
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response["data"][0]["embedding"]

# Store into ChromaDB
def store_in_chroma(summaries):
    chroma_client = PersistentClient(path="embeddings/chroma_book_summaries")

    collection = chroma_client.get_or_create_collection(name="books")

    for i, summary in enumerate(summaries):
        collection.add(
            documents=[summary["content"]],
            metadatas=[{"title": summary["title"]}],
            ids=[f"book_{i}"]
        )

    print(f"✅ Stored {len(summaries)} book summaries in ChromaDB.")

# Entry point
if __name__ == "__main__":
    summaries = load_summaries()
    store_in_chroma(summaries)