from openai import OpenAI
import os
from flask import Blueprint, request, render_template
from smart_librarian.models.book_model import load_summaries, build_vectorstore

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

main_bp = Blueprint("main", __name__)

summaries = load_summaries()
vectorstore = build_vectorstore(summaries)

from smart_librarian.models.cache import load_cache, save_cache

# Load on app init
cache = load_cache()

def generate_gpt_reply(user_query, book_results):
    if user_query in cache:
        print("✅ Using cached GPT response")
        return cache[user_query]  # return from cache

    # Otherwise: generate with GPT
    summary_text = "\n\n".join([
        f"Title: {b['title']}\nSummary: {b['summary']}" for b in book_results
    ])

    system_message = {
        "role": "system",
        "content": "You are a friendly book recommendation assistant. Use a warm, conversational tone."
    }

    user_message = {
        "role": "user",
        "content": f"The user asked: {user_query}\n\nHere are some candidate books:\n\n{summary_text}\n\nRecommend one or more of them conversationally."
    }

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[system_message, user_message]
    )

    reply = response.choices[0].message.content

    # Store in cache
    cache[user_query] = reply
    save_cache(cache)

    return reply


@main_bp.route("/", methods=["GET", "POST"])
def home():
    results = []
    query = ""
    gpt_reply = ""

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

        gpt_reply = generate_gpt_reply(query, results)

    return render_template("index.html", query=query, results=results, gpt_reply=gpt_reply)
