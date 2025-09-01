from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from models import Teacher

bp = Blueprint("auth", __name__, template_folder="../templates")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    t = Teacher.query.filter_by(email=email).first()
    if not t or not check_password_hash(t.password_hash, password):
        flash("Invalid email or password.", "danger")
        return render_template("login.html"), 401
    login_user(t)
    return redirect(url_for("index"))

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))
