# smart_librarian/api/message_api.py
from flask import Blueprint, request, jsonify
from smart_librarian.utils.auth_guard import current_user
from smart_librarian.models.chat_db import Conversation
from openai import OpenAI
import os
from smart_librarian.models.book_model import BookModel
api_bp = Blueprint("api", __name__, url_prefix="/api")

COOKIE_CONV = "current_conv_id"

VECTORSTORE = BookModel()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def _require_user():
    u = current_user()
    if not u: return None, (jsonify({"error":"unauthorized"}), 401)
    return u, None

@api_bp.get("/list")
def list_convs():
    user, err = _require_user()
    if err: 
        return err
    convs = Conversation.list_conversations(user)
    return jsonify({"conversations": [
        {"id": c["id"], "title": c["title"], "updated_at": str(c["updated_at"])} for c in convs
    ]})

@api_bp.post("/open")
def api_open():
    user, err = _require_user()  
    if err: 
        return err
    conv_id = (request.get_json(silent=True) or {}).get("conv_id")
    if not conv_id:
        return jsonify({"error":"missing_conv_id"}), 400
    conv = Conversation.get_conversation(user, int(conv_id))
    if not conv: return jsonify({"error":"not_found"}), 404
    resp = jsonify({"conv": {
        "id": conv["id"], "title": conv["title"], "messages": conv.get("messages", [])
    }})
    resp.set_cookie(COOKIE_CONV, str(conv["id"]), httponly=True, samesite="Strict")
    return resp

@api_bp.post("/new")
def api_new():
    user, err = _require_user() 
    if err: 
        return err
    cid = Conversation.create_conversation(user, "New chat")
    conv = Conversation.get_conversation(user, cid)
    resp = jsonify({"conv": {"id": conv["id"], "title": conv["title"], "messages": []}})
    resp.set_cookie(COOKIE_CONV, str(cid), httponly=True, samesite="Strict")
    return resp

@api_bp.post("/delete")
def api_delete():
    user, err = _require_user()
    if err: 
        return err
    conv_id = (request.get_json(silent=True) or {}).get("conv_id")
    if not conv_id: return jsonify({"error":"missing_conv_id"}), 400
    Conversation.delete_conversation(user, int(conv_id))
    return jsonify({"ok": True})

@api_bp.post("/send")
def api_send():
    user, err = _require_user()
    if err: 
        return err
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg: return jsonify({"error":"empty_message"}), 400
    conv_id = data.get("conv_id") or request.cookies.get(COOKIE_CONV) or Conversation.create_conversation(user, "New chat")
    conv_id = int(conv_id)
    conv = Conversation.get_conversation(user, conv_id) or Conversation.get_conversation(user, Conversation.create_conversation(user, "New chat"))
    if not conv.get("messages"): Conversation.set_title(user, conv_id, user_msg[:60])
    Conversation.add_message(user, conv_id, "user", user_msg)

    docs = VECTORSTORE.similarity_search_with_relevance_scores(user_msg, k=3)
    context_text = "\n\n".join(
        f"Title: {d.metadata.get('title','Untitled')}\nRelevance: {score:.2f}\nSummary: {d.page_content}"
        for d, score in docs
    )
    print(context_text)
    msgs = conv.get("messages", [])
    system_prompt = (
                    "You are a friendly book recommendation assistant.\n"
                    "HARD RULES:\n"
                    "- Recommend ONLY from the CANDIDATES list (by id).\n"
                    "- If nothing fits, ask 1–2 clarifying questions instead of inventing titles.\n"
                    "CANDIDATES are provided via tool schema.\n"
                    )
    ai = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content":f"{system_prompt}\nCandidate books:\n{context_text}\nPrevious context:\n{msgs}"},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.6,
    )
    assistant_reply = ai.choices[0].message.content

    Conversation.add_message(user, conv_id, "assistant", assistant_reply)
    conv = Conversation.get_conversation(user, conv_id)
    resp = jsonify({
        "ok": True,
        "conv": {"id": conv_id, "title": conv["title"]},
        "messages": conv.get("messages", []),
        "assistant_reply": assistant_reply,
    })
    resp.set_cookie(COOKIE_CONV, str(conv_id), httponly=True, samesite="Strict")
    return resp
