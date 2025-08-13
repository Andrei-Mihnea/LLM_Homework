# main.py
import os
from smart_librarian import create_app
from smart_librarian.router import Router
from flask import request
from smart_librarian.models.user_db import init_db
from smart_librarian.models.chat_db import init_chat_db
app = create_app()
router = Router()
init_db()
init_chat_db()

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'] )
def handle_request(path):
    full_path = "/" + path
    if full_path.startswith('/api') or full_path.startswith('/static'):
        return f"Page not found: {full_path} <br> <a href='/home/index'>Go to Home</a>", 404
    return router.route(full_path)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
