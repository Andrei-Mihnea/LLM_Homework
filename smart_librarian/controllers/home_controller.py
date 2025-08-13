from flask import render_template, request, redirect
from smart_librarian.utils.auth_guard import current_user
from smart_librarian.models.book_model import load_summaries, build_vectorstore
from smart_librarian.models.cache import load_cache, save_cache
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
cache = load_cache()

def require_login_redirect():
    user = current_user()
    if not user:
        return None, redirect("/auth/index")
    return user, None

class HomeController:
    def __init__(self):
        self.summaries = load_summaries()
        self.vectorstore = build_vectorstore(self.summaries)

    def index(self):
        user, redirect_resp = require_login_redirect()
        if redirect_resp:  # not logged in
            return redirect_resp
        return render_template("index.html", query="", results=[], gpt_reply="")

    def search(self):
        user, redirect_resp = require_login_redirect()
        if redirect_resp:
            return redirect_resp

        query = request.form.get("query", "")
        results = []
        gpt_reply = ""

        if query:
            rag_results = self.vectorstore.similarity_search_with_relevance_scores(query, k=3)
            results = [
                {
                    "title": doc.metadata.get("title", "Untitled"),
                    "score": f"{score:.2f}",
                    "summary": doc.page_content
                }
                for doc, score in rag_results
            ]

            if query in cache:
                gpt_reply = cache[query]
            else:
                summary_text = "\n\n".join([
                    f"Title: {b['title']}\nSummary: {b['summary']}" for b in results
                ])
                messages = [
                    {"role": "system", "content": "You are a friendly book recommendation assistant."},
                    {"role": "user", "content": f"The user asked: {query}\n\n{summary_text}\n\nGive a recommendation."}
                ]
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                gpt_reply = response.choices[0].message.content
                cache[query] = gpt_reply
                save_cache(cache)

        return render_template("index.html", query=query, results=results, gpt_reply=gpt_reply)
