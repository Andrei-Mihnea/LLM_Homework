# smart_librarian/controllers/home_controller.py
from flask import render_template
from smart_librarian.utils.auth_guard import current_user
from smart_librarian.models.book_model import load_summaries, build_vectorstore
from smart_librarian.database.chat_db import Conversation
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




