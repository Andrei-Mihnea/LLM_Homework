
from flask import Flask
import os

def create_app():
    # Point templates to the package's templates folder
    template_folder = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_folder)
    return app
