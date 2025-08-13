from flask import render_template, request, make_response
from smart_librarian.utils.identity import get_or_set_user_id
from smart_librarian.utils.chat_db import Conversation
from smart_librarian.models.book_model import load_summaries, build_vectorstore
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_SUMMARIES = load_summaries()
_VECTOR = build_vectorstore(_SUMMARIES)

class ChatController:
    def index(self):
        resp = make_response()
        user_id, resp = get_or_set_user_id(resp)
        convs = Conversation.list_conversations(user_id)
        html = render_template("chat_list.html", conversations=convs)
        resp.set_data(html)
        resp.mimetype = "text/html"
        return resp

    def new(self):
        resp = make_response()
        user_id, resp = get_or_set_user_id(resp)
        cid = Conversation.create_conversation(user_id, "New chat")
        resp.status_code = 302
        resp.headers["Location"] = f"/chat/open/{cid}"
        return resp

    def open(self, conv_id: int):
        resp = make_response()
        user_id, resp = get_or_set_user_id(resp)
        conv = Conversation.get_conversation(user_id, conv_id)
        if not conv:
            resp.status_code = 302
            resp.headers["Location"] = "/chat/index"
            return resp
        html = render_template("chat_room.html", conversation=conv)
        resp.set_data(html)
        resp.mimetype = "text/html"
        return resp

    def send(self, conv_id: int):
        resp = make_response()
        user_id, resp = get_or_set_user_id(resp)
        conv = Conversation.get_conversation(user_id, conv_id)
        if not conv:
            resp.status_code = 302
            resp.headers["Location"] = "/chat/index"
            return resp

        user_msg = (request.form.get("message") or "").strip()
        if not user_msg:
            resp.status_code = 302
            resp.headers["Location"] = f"/chat/open/{conv_id}"
            return resp

        # First message sets title
        if not conv.messages:
            conv.title = user_msg[:60]

        Conversation.add_message(user_id, conv_id, "user", user_msg)

        # RAG retrieval
        docs = _VECTOR.similarity_search_with_relevance_scores(user_msg, k=3)
        context_text = "\n\n".join([
            f"Title: {doc.metadata.get('title','Untitled')}\nRelevance: {score:.2f}\nSummary: {doc.page_content}"
            for doc, score in docs
        ])

        # CAG reuse check
        msgs = Conversation.get_conversation(user_id, conv_id).messages
        if len(msgs) >= 2 and msgs[-2]["role"] == "user" and msgs[-2]["content"] == user_msg and msgs[-1]["role"] == "assistant":
            assistant_reply = msgs[-1]["content"]
        else:
            messages = [
                {"role": "system", "content": "You are a friendly book recommendation assistant."},
                {"role": "system", "content": f"Candidate books:\n{context_text}"},
                {"role": "user", "content": user_msg},
            ]
            resp_ai = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.6
            )
            assistant_reply = resp_ai.choices[0].message.content

        Conversation.add_message(user_id, conv_id, "assistant", assistant_reply)

        resp.status_code = 302
        resp.headers["Location"] = f"/chat/open/{conv_id}"
        return resp

    def delete(self, conv_id: int):
        resp = make_response()
        user_id, resp = get_or_set_user_id(resp)
        Conversation.delete_conversation(user_id, conv_id)
        resp.status_code = 302
        resp.headers["Location"] = "/chat/index"
        return resp