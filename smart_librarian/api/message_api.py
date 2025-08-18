
from flask import jsonify, request,Blueprint
from smart_librarian.utils.auth_guard import current_user
from smart_librarian.models.chat_db import Conversation
from smart_librarian.models.book_model import load_summaries, build_vectorstore
from openai import OpenAI
import os

COOKIE_CONV = "current_conv_id"
api_bp = Blueprint("api",__name__, url_prefix="/api")
# build RAG once
_VECTORSTORE = build_vectorstore(load_summaries())
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@api_bp.route("/send", methods=["POST"])  # <-- leading slash + matches your JS
def api_send():
    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "empty_message"}), 400

    conv_id = data.get("conv_id") or request.cookies.get(COOKIE_CONV)
    if not conv_id:
        conv_id = Conversation.create_conversation(user, "New chat")
    conv_id = int(conv_id)

    conv = Conversation.get_conversation(user, conv_id)
    if not conv:
        conv_id = Conversation.create_conversation(user, "New chat")
        conv = Conversation.get_conversation(user, conv_id)

    if not conv.get("messages"):
        Conversation.set_title(user, conv_id, user_msg[:60])

    Conversation.add_message(user, conv_id, "user", user_msg)

    # RAG
    docs = _VECTORSTORE.similarity_search_with_relevance_scores(user_msg, k=3)
    context_text = "\n\n".join(
        f"Title: {d.metadata.get('title','Untitled')}\nRelevance: {score:.2f}\nSummary: {d.page_content}"
        for d, score in docs
    )

    # reply
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = (
        "You are a friendly book recommendation assistant. "
        "Use the conversation history to stay consistent. "
        "Prefer candidates I give you; if a requested book isn't in them, say so politely and suggest nearby options."
    )
    ai = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": f"Candidate books:\n{context_text}"},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.6,
    )
    assistant_reply = ai.choices[0].message.content
    Conversation.add_message(user, conv_id, "assistant", assistant_reply)

    updated = Conversation.get_conversation(user, conv_id)
    resp = jsonify({
        "ok": True,
        "conv_id": conv_id,
        "assistant_reply": assistant_reply,
        "messages": updated.get("messages", []),
        "title": updated.get("title"),
    })
    resp.set_cookie(COOKIE_CONV, str(conv_id), httponly=True, samesite="Strict")
    return resp
