# smart_librarian/controllers/home_controller.py
from flask import render_template, request, make_response, jsonify
from smart_librarian.utils.auth_guard import current_user  # your login helper
from smart_librarian.models.book_model import load_summaries, build_vectorstore
from smart_librarian.models.chat_db import Conversation
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class HomeController:
    def __init__(self):
        # Build RAG index once
        self.summaries = load_summaries()
        self.vectorstore = build_vectorstore(self.summaries)

    # GET /home/index  → render chat page with sidebar
    def index(self):
        user = current_user()
        if not user:
            from flask import redirect
            return redirect("/auth/index")

        convs = Conversation.list_conversations(user)
        current = None
        if convs:
            # fetch the full conversation (with messages) for the first item
            current = Conversation.get_conversation(user, convs[0]["id"])

        return render_template("index.html", conversations=convs, current=current)
    
    def messages(self,conv_id: int):
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

    # GET /home/open/<id>  → open a specific conversation
    def open(self, conv_id: int):
        user = current_user()
        if not user:
            from flask import redirect
            return redirect("/auth/index")

        convs = Conversation.list_conversations(user)
        current = Conversation.get_conversation(user, int(conv_id))
        if not current and convs:
            current = convs[0]
        return render_template("index.html", conversations=convs, current=current)

    # ✅ GET /home/new  → create a new chat and redirect to it
    def new(self):
        user = current_user()
        if not user:
            from flask import redirect
            return redirect("/auth/index")

        cid = Conversation.create_conversation(user, "New chat")
        from flask import redirect
        return redirect(f"/home/open/{cid}")

    # POST /home/send/<id>  → append a message, run RAG+LLM, append reply
    def send(self, conv_id: int):
        user = current_user()
        if not user:
            return jsonify({"error": "unauthorized"}), 401

        data = request.get_json(silent=True) or {}
        user_msg = (data.get("message") or "").strip()
        if not user_msg:
            print("Empty user message")
            return jsonify({"error": "empty_message"}), 400

        # Ensure conversation exists
        conv = Conversation.get_conversation(user, int(conv_id))
        if not conv:
            conv_id = Conversation.create_conversation(user, "New chat")
            conv = Conversation.get_conversation(user, int(conv_id))

        # First user message => set title
        if not conv.get("messages"):
            Conversation.set_title(user, int(conv_id), user_msg[:60])

        # Save user msg
        Conversation.add_message(user, int(conv_id), "user", user_msg)

        # RAG context
        docs = self.vectorstore.similarity_search_with_relevance_scores(user_msg, k=3)
        context_text = "\n\n".join([
            f"Title: {doc.metadata.get('title','Untitled')}\nRelevance: {score:.2f}\nSummary: {doc.page_content}"
            for doc, score in docs
        ])

        # Cheap CAG reuse
        context_text = Conversation.get_conversation(user, int(conv_id))
        msgs = context_text.get("messages", [])
        if (len(msgs) >= 2 and
            msgs[-2].get("role") == "user" and
            msgs[-2].get("content") == user_msg and
            msgs[-1].get("role") == "assistant"):
            assistant_reply = msgs[-1].get("content", "")
        else:
            messages = [
                {"role": "system", "content": "You are a friendly book recommendation assistant. Prefer titles from the provided context. Be warm and concise.If you don't know the answer, say 'I don't know' and ask for more details. If you are asked about informations not related to books, use a funny politely decline(like telling a joke about it)."},
                {"role": "system", "content": f"Candidate books:\n{context_text}"},
                {"role": "user", "content": user_msg},
            ]
            ai = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.6,
            )
            assistant_reply = ai.choices[0].message.content

        # Save assistant msg
        Conversation.add_message(user, int(conv_id), "assistant", assistant_reply)

        # Return the whole updated message list for convenience
        updated = Conversation.get_conversation(user, int(conv_id))
        return jsonify({
            "assistant_reply": assistant_reply,
            "messages": updated.get("messages", []),
            "id": updated["id"],
            "title": updated["title"]
        })
    
    # POST /home/delete/<id>  → delete conversation
    def delete(self, conv_id: int):
        from flask import redirect
        user = current_user()
        if not user:
            return redirect("/auth/index")

        Conversation.delete_conversation(user, int(conv_id))
        return redirect("/home/index")
