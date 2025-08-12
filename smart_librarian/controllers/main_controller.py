# app/controllers/main_controller.py
from flask import Blueprint, request, render_template
from smart_librarian.models.book_model import load_summaries, build_vectorstore

main_bp = Blueprint("main", __name__)

summaries = load_summaries()
vectorstore = build_vectorstore(summaries)

@main_bp.route("/", methods=["GET", "POST"])
def home():
    results = []
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "")
        rag_results = vectorstore.similarity_search_with_relevance_scores(query, k=3)
        results = [
            {
                "title": doc.metadata.get("title", "Untitled"),
                "score": f"{score:.2f}",
                "summary": doc.page_content
            }
            for doc, score in rag_results
        ]
    return render_template("index.html", query=query, results=results)
