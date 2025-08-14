import os
import bcrypt
from flask import request, redirect, make_response
from sqlalchemy.exc import IntegrityError
from smart_librarian.models.user_db import SessionLocal, User
from smart_librarian.utils.jwt_helper import create_jwt

COOKIE_NAME = "access_token"
IS_SECURE = False  # set True behind HTTPS in prod

class AuthController:
    def index(self):
        current_dir = os.path.dirname(__file__)
        template_path = os.path.join(current_dir, '..', 'templates', 'auth.html')
        template_path = os.path.abspath(template_path)
        with open(template_path, 'r', encoding='utf-8') as f:
            html = f.read()
        return make_response(html)

    def login(self):
        if request.method != 'POST':
            return redirect("/auth/index")

        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if User.exists_password_and_user(username, password):
            token = create_jwt({"sub": username})  #subject = username

            resp = make_response(redirect("/home/index"))
            resp.set_cookie(
                COOKIE_NAME,
                token,
                httponly=True,
                secure=IS_SECURE,
                samesite="Lax",
                max_age=60 * 60 * 24,  # cookie lifetime (not JWT lifetime)
                path="/",
            )
            return resp

        return """
            <script>
              alert("Invalid username or password");
              window.location.href = "/auth/index";
            </script>
        """

    def register(self):
        if request.method != 'POST':
            return redirect("/auth/index")

        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')

        if not username or not email or not password:
            return """
                <script>
                  alert("Please fill all fields.");
                  window.location.href = "/auth/index";
                </script>
            """

        session_db = SessionLocal()
        try:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode()
            user = User(username=username, email=email, password=hashed)
            session_db.add(user)
            session_db.commit()
        except IntegrityError:
            session_db.rollback()
            return """
                <script>
                  alert("User already exists (username or email).");
                  window.location.href = "/auth/index";
                </script>
            """
        except Exception:
            session_db.rollback()
            return """
                <script>
                  alert("Registration failed due to a server error.");
                  window.location.href = "/auth/index";
                </script>
            """
        finally:
            session_db.close()

        return """
            <script>
              alert("Registration successful! You can log in now.");
              window.location.href = "/auth/index";
            </script>
        """

    def logout(self):
        resp = make_response(redirect("/auth/index"))
        resp.set_cookie(
            COOKIE_NAME, "", expires=0, httponly=True, secure=IS_SECURE, samesite="Lax", path="/"
        )
        return resp
