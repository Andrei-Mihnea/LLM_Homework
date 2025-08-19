import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter
from pathlib import Path
from src.file_paths import SUMMARY_FILE, CHROMA_DIR

book_summaries_dict = {}
titles = []
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
                book_summaries_dict[current_title] = current_summary
                titles.append(current_title)
            current_title = line.replace("## Title: ", "")
            current_summary = []
        elif line:
            current_summary.append(line)

    if current_title and current_summary:
        # print(f"titlu curent:{current_title}\n rezumat:{current_summary}")
        book_summaries_dict[current_title] = current_summary
        titles.append(current_title)
        summaries.append(Document(
            page_content=" ".join(current_summary),
            metadata={"title": current_title}
        ))
    # print("aici apare book summaries")
    # print(book_summaries_dict)
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

def get_summary_by_title(title: str) -> str:
    summary = book_summaries_dict.get(title, [])
    if isinstance(summary, list):
        return " ".join(summary)
    return summary or ""







