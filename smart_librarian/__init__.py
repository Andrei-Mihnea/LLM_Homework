# app/__init__.py
from flask import Flask
from smart_librarian.controllers.main_controller import main_bp
import os

template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "templates"))

def create_app():
    app = Flask(__name__, template_folder=template_path)
    app.register_blueprint(main_bp)
    return app
