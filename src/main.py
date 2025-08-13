from smart_librarian import create_app
from smart_librarian.router import Router
from flask import request
import os

app = create_app()
router = Router()

@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def handle_request(path):
    full_path = "/" + path
    if full_path.startswith('/api') or full_path.startswith('/static'):
        return "404 - Reserved route", 404
    return router.route(full_path)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
