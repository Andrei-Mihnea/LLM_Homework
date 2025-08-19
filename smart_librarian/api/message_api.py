# smart_librarian/api/message_api.py
from flask import Blueprint, request, jsonify
from smart_librarian.utils.auth_guard import current_user
from smart_librarian.models.chat_db import Conversation
import json
from openai import OpenAI
import os
from smart_librarian.models.book_model import load_summaries, build_vectorstore,get_summary_by_title,titles
api_bp = Blueprint("api", __name__, url_prefix="/api")

COOKIE_CONV = "current_conv_id"
summaries = load_summaries()
VECTORSTORE = build_vectorstore(summaries)
# print(summaries)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_summary_by_title",
            "description": "Retrieves the FULL summary for the given exact book title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "enum": titles,
                        "description": "Exact title of the book (must match a candidate)."
                    }
                },
                "required": ["title"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
]

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
    if not user_msg:
        return jsonify({"error": "empty_message"}), 400

    conv_id = data.get("conv_id") or request.cookies.get(COOKIE_CONV) or Conversation.create_conversation(user, "New chat")
    conv_id = int(conv_id)
    conv = Conversation.get_conversation(user, conv_id) or Conversation.get_conversation(
        user, Conversation.create_conversation(user, "New chat")
    )

    if not conv.get("messages"):
        Conversation.set_title(user, conv_id, user_msg[:60])
    Conversation.add_message(user, conv_id, "user", user_msg)
    msgs = conv.get("messages", [])
    # === RAG: top-k candidați + scoruri ===
    docs = VECTORSTORE.similarity_search_with_relevance_scores(user_msg, k=3)
    candidates_text = "\n\n".join(
        f"- id: {i+1}\n  title: {d.metadata.get('title', 'Untitled')}\n  relevance: {score:.2f}"
        for i, (d, score) in enumerate(docs)
    )

    # === Prompt assistant (reguli clare) ===
    system_prompt = (
        "You are a friendly book recommendation assistant.\n"
        "HARD RULES:\n"
        "- Recommend ONLY from the CANDIDATES list (by exact title).\n"
        "- After you decide the best title, CALL the function get_summary_by_title with that exact title.\n"
        "- If nothing fits, ask up to 2 clarifying questions instead of inventing titles.\n"
        "- Do NOT call the tool for conversation starters or non-book questions.\n"
        "Return a short recommendation first (one short paragraph), then we'll show the full summary below.\n"
        "CANDIDATES:\n"
        f"{candidates_text}\n"
        f"Previous messages{msgs}"
    )

    ctx_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    # === 1) LLM generează recomandarea și (dacă e cazul) un tool-call ===
    ai = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=ctx_messages,
        temperature=0.0,
        tools=tools,
        tool_choice="auto"
    )
    function_call = None
    function_call_arguments = None
    assistant_raw_reply = ai.choices[0].message
    assistant_response = assistant_raw_reply.content or ""
    # print(first.output)
    tool_calls = assistant_raw_reply.tool_calls or []
    for call in tool_calls:
        if call.type == "function" and call.function and call.function.name == "get_summary_by_title":
            print(f"Function called {call.function.name}")
             # arguments e un string JSON
            raw_args = call.function.arguments or "{}"
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
            title = (args.get("title") or "").strip()
            if title:
                summary_text = get_summary_by_title(title)
                assistant_response += f"\n\nRezumatul complet „{title}”\n{summary_text}"
            break  # avem un si
    Conversation.add_message(user, conv_id, "assistant", assistant_response)

    conv = Conversation.get_conversation(user, conv_id)
    resp_json = jsonify({
        "ok": True,
        "conv": {"id": conv_id, "title": conv["title"]},
        "messages": conv.get("messages", []),
        "assistant_reply": assistant_response,
    })
    resp_json.set_cookie(COOKIE_CONV, str(conv_id), httponly=True, samesite="Strict")
    return resp_json