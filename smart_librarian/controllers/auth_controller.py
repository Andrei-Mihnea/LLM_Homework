
import os
import bcrypt
from flask import request, redirect, make_response
from smart_librarian.models.user_db import SessionLocal, User
class AuthController:
    def index(self):
        current_dir = os.path.dirname(__file__)
        template_path = os.path.join(current_dir, '..', 'templates', 'auth.html')
        template_path = os.path.abspath(template_path)

        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()

        response = make_response(html)
        return response

    def login(self):
        if request.method != 'POST':
            return "405 Method Not Allowed", 405

        username = request.form.get('username', '')
        password = request.form.get('password', '')

        user_model = User()

        if user_model.exists_password_and_user(username, password):
            return redirect("/home/index")

        return "<h1>Invalid username or password</h1>"

    def register(self):
        if request.method != 'POST':
            return "405 Method Not Allowed", 405

        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        if password != confirm_password:
            return'''
                <script>
                    alert("Registration failed: Invalid passwords not matching.");
                    window.location.href = "/auth/index";
                </script>
            '''
        session = SessionLocal()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            user = User(
                username=username,
                email=email,
                password=hashed.decode()
            )
            session.add(user)
            session.commit()
        except Exception:
            session.rollback()
            return '''
                <script>
                    alert("Registration failed: Invalid data or user already exists.");
                    window.location.href = "/auth/index";
                </script>
            '''
        finally:
            session.close()

        return redirect("/auth/index")
