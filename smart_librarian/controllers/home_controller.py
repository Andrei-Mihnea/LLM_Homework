# smart_librarian/controllers/home_controller.py
from flask import render_template, request, make_response, jsonify
from smart_librarian.utils.auth_guard import current_user
from smart_librarian.models.book_model import load_summaries, build_vectorstore
from smart_librarian.models.chat_db import Conversation
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COOKIE_CONV = "current_conv_id"  # single source of truth cookie name

class HomeController:
    def __init__(self):
        self.summaries = load_summaries()
        self.vectorstore = build_vectorstore(self.summaries)

    def index(self):
        user = current_user()
        if not user:
            from flask import redirect
            return redirect("/auth/index")

        convs = Conversation.list_conversations(user)
        current = None
        # if convs:
        #     current = Conversation.get_conversation(user, convs[0]["id"])

        return render_template("index.html", conversations=convs, current=current)

    # GET /home/messages/<conv_id>  (used by /home/api/messages/<conv_id>)
    def messages(self, conv_id: int):
        user = current_user()
        if not user:
            return jsonify({"error": "unauthorized"}), 401

        conv = Conversation.get_conversation(user, int(conv_id))
        if not conv:
            return jsonify({"error": "not_found"}), 404

        return jsonify({
            "id": conv["id"],
            "title": conv["title"],
            "messages": conv.get("messages", []),
            "updated_at": str(conv.get("updated_at"))
        })

    # GET /home/open/<id>
    def open(self, conv_id: int):
        user = current_user()
        if not user:
            from flask import redirect
            return redirect("/auth/index")

        convs = Conversation.list_conversations(user)
        current = Conversation.get_conversation(user, int(conv_id))
        if not current and convs:
            current = convs[0]

        resp = make_response(render_template("index.html", conversations=convs, current=current))
        # unify cookie name
        resp.set_cookie(COOKIE_CONV, str(conv_id), httponly=True, samesite="Strict")
        return resp

    # GET /home/new
    def new(self):
        user = current_user()
        if not user:
            from flask import redirect
            return redirect("/auth/index")

        cid = Conversation.create_conversation(user, "New chat")
        from flask import redirect
        return redirect(f"/home/open/{cid}")

    # POST /home/send  (called via /home/api/send)
    def send(self):
        user = current_user()
        if not user:
            return jsonify({"error": "unauthorized"}), 401

        data = request.get_json(silent=True) or {}
        user_msg = (data.get("message") or "").strip()
        if not user_msg:
            return jsonify({"error": "empty_message"}), 400

        # conv_id from body OR cookie
        conv_id = data.get("conv_id") or request.cookies.get(COOKIE_CONV)
        if not conv_id:
            # no conv selected → create one
            conv_id = Conversation.create_conversation(user, "New chat")
        conv_id = int(conv_id)

        conv = Conversation.get_conversation(user, conv_id)
        if not conv:
            # if somehow missing, create it
            conv_id = Conversation.create_conversation(user, "New chat")
            conv = Conversation.get_conversation(user, conv_id)

        # first message → set title
        if not conv.get("messages"):
            Conversation.set_title(user, conv_id, user_msg[:60])

        # save user message
        Conversation.add_message(user, conv_id, "user", user_msg)

        # RAG: build context_text (don't overwrite it!)
        docs = self.vectorstore.similarity_search_with_relevance_scores(user_msg, k=3)
        context_text = "\n\n".join([
            f"Title: {doc.metadata.get('title','Untitled')}\nRelevance: {score:.2f}\nSummary: {doc.page_content}"
            for doc, score in docs
        ])

        # cheap CAG (reuse last if same)
        fresh = Conversation.get_conversation(user, conv_id)
        msgs = fresh.get("messages", [])
        if (len(msgs) >= 2 and
            msgs[-2].get("role") == "user" and
            msgs[-2].get("content") == user_msg and
            msgs[-1].get("role") == "assistant"):
            assistant_reply = msgs[-1].get("content", "")
        else:
            system_prompt = ("You are a friendly book recommendation assistant. "
                            "Always use the ongoing conversation to stay consistent. "
                            "If the user asks about 'earlier' or 'previous', refer to the chat history you received if none is given in a respectfully manner say you didn't discuss about anything yet. "
                            "Prefer recommending from the provided candidate books when relevant. "
                            "If the question is not about books, politely steer back to reading topics.")

            ai = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content":system_prompt},
                    {"role": "system", "content": f"Candidate books:\n{context_text}"},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.6,
            )
            assistant_reply = ai.choices[0].message.content

        Conversation.add_message(user, conv_id, "assistant", assistant_reply)

        # respond with updated state + set cookie so FE doesn't lose selection
        updated = Conversation.get_conversation(user, conv_id)
        resp = jsonify({
            "ok": True,
            "conv_id": conv_id,
            "assistant_reply": assistant_reply,
            "messages": updated.get("messages", []),
            "title": updated.get("title")
        })
        resp.set_cookie(COOKIE_CONV, str(conv_id), httponly=True, samesite="Strict")
        return resp

    # POST /home/delete/<id>
    def delete(self, conv_id: int):
        from flask import redirect
        user = current_user()
        if not user:
            return redirect("/auth/index")

        Conversation.delete_conversation(user, int(conv_id))
        return redirect("/home/index")
