import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter
from pathlib import Path
from src.file_paths import SUMMARY_FILE, CHROMA_DIR


# === Load summaries ===
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
                summaries.append(Document(
                    page_content=" ".join(current_summary),
                    metadata={"title": current_title}
                ))
            current_title = line.replace("## Title: ", "")
            current_summary = []
        elif line:
            current_summary.append(line)

    if current_title and current_summary:
        summaries.append(Document(
            page_content=" ".join(current_summary),
            metadata={"title": current_title}
        ))

    return summaries

# === Embed and store in Chroma using LangChain ===
def build_vectorstore(docs):
    if Path(CHROMA_DIR).exists():
        print("🔁 Reusing existing ChromaDB")
        return Chroma(persist_directory=CHROMA_DIR, embedding_function=OpenAIEmbeddings())

    print("🔨 Building new Chroma vectorstore")
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=OpenAIEmbeddings(),
        persist_directory=CHROMA_DIR
    )
    vectorstore.persist()
    return vectorstore

# === Query the vectorstore ===
# def query_books(vectorstore, query, top_k=3):
#     results = vectorstore.similarity_search_with_relevance_scores(query, k=top_k)
#     for i, (doc, score) in enumerate(results):
#         print(f"{i+1}. {doc.metadata['title']} (score: {score:.2f})")
#         print(f"   ➤ {doc.page_content}\n")

# # === CLI Driver ===
# if __name__ == "__main__":
#     print("📚 Loading book summaries...")
#     docs = load_summaries()
    
#     print("🔗 Initializing vector store with LangChain...")
#     vectorstore = build_vectorstore(docs)

#     print("\n🤖 Ready to chat with RAG!")
#     while True:
#         query = input("\nEnter a theme or interest (or 'exit'): ")
#         if query.strip().lower() in ["exit", "quit"]:
#             break
#         query_books(vectorstore, query)


