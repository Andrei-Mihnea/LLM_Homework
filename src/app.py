# === app.py ===
from flask import Flask, request, render_template
from rag_chain import load_summaries, build_vectorstore, query_books

app = Flask(__name__, template_folder='../templates')

# Initialize RAG system
summaries = load_summaries()
vectorstore = build_vectorstore(summaries)

@app.route("/", methods=["GET", "POST"])
def home():
    results = []
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "")
        rag_results = vectorstore.similarity_search_with_relevance_scores(query, k=3)
        results = [
            {
                "title": doc.metadata['title'],
                "score": f"{score:.2f}",
                "summary": doc.page_content
            }
            for doc, score in rag_results
        ]
    return render_template("index.html", query=query, results=results)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
