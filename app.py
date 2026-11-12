import os
import secrets
import sqlite3
from functools import wraps
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request, session, redirect, url_for, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-secret-key-before-use")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1",
)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")
DEFAULT_TEAM_NAMES = {1: "1팀", 2: "2팀", 3: "3팀"}
LEGACY_TEAM_NAMES = {1: "A팀", 2: "B팀", 3: "C팀"}
MAX_POINTS = 1000


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS score_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                points INTEGER NOT NULL,
                game_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                undone INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(team_id) REFERENCES teams(id)
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO teams (id, name) VALUES (?, ?)",
                list(DEFAULT_TEAM_NAMES.items())
            )
        if conn.execute("PRAGMA user_version").fetchone()[0] < 1:
            for team_id, legacy_name in LEGACY_TEAM_NAMES.items():
                conn.execute(
                    "UPDATE teams SET name = ? WHERE id = ? AND name = ?",
                    (DEFAULT_TEAM_NAMES[team_id], team_id, legacy_name)
                )
            conn.execute("PRAGMA user_version = 1")


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "관리자 인증이 필요합니다."}), 401
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


def current_score_rows(conn):
    return conn.execute("""
        SELECT t.id, t.name,
               COALESCE(SUM(CASE WHEN e.undone = 0 THEN e.points ELSE 0 END), 0) AS score
        FROM teams t
        LEFT JOIN score_events e ON e.team_id = t.id
        GROUP BY t.id, t.name
        ORDER BY t.id
    """).fetchall()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    return render_template("admin.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        # Compare the submitted password on the server; never expose it to browser JavaScript.
        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["is_admin"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin"))
        flash("비밀번호가 올바르지 않습니다.")
    return render_template("login.html")


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


@app.get("/api/scoreboard")
def scoreboard():
    with db() as conn:
        teams = [dict(row) for row in current_score_rows(conn)]
        events = conn.execute("""
            SELECT e.id, e.points, e.created_at, t.name AS team_name
            FROM score_events e
            JOIN teams t ON t.id = e.team_id
            WHERE e.undone = 0
            ORDER BY e.id DESC
            LIMIT 12
        """).fetchall()
    return jsonify({
        "teams": teams,
        "events": [dict(row) for row in events],
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds")
    })


@app.get("/api/admin/state")
@admin_required
def admin_state():
    with db() as conn:
        teams = [dict(row) for row in current_score_rows(conn)]
        events = conn.execute("""
            SELECT e.id, e.team_id, e.points, e.created_at,
                   e.undone, t.name AS team_name
            FROM score_events e JOIN teams t ON t.id = e.team_id
            ORDER BY e.id DESC LIMIT 30
        """).fetchall()
        last_event = conn.execute(
            "SELECT id FROM score_events WHERE undone = 0 ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return jsonify({
        "teams": teams,
        "events": [dict(row) for row in events],
        "can_undo": last_event is not None,
        "csrf_token": session.get("csrf_token", "")
    })


def check_csrf():
    supplied = request.headers.get("X-CSRF-Token", "")
    expected = session.get("csrf_token", "")
    return bool(expected) and secrets.compare_digest(supplied, expected)


@app.post("/api/admin/score")
@admin_required
def add_score():
    if not check_csrf():
        return jsonify({"error": "요청을 확인할 수 없습니다. 페이지를 새로고침해 주세요."}), 403
    data = request.get_json(silent=True) or {}
    try:
        team_id = int(data.get("team_id"))
        points = int(data.get("points"))
    except (TypeError, ValueError):
        return jsonify({"error": "팀과 점수를 확인해 주세요."}), 400

    if team_id not in (1, 2, 3) or points == 0 or abs(points) > MAX_POINTS:
        return jsonify({"error": "허용되지 않은 팀 또는 점수입니다. (0점 제외, 최대 ±1000점)"}), 400

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    with db() as conn:
        conn.execute(
            "INSERT INTO score_events (team_id, points, created_at) VALUES (?, ?, ?)",
            (team_id, points, now)
        )
    return jsonify({"ok": True})


@app.post("/api/admin/undo")
@admin_required
def undo_score():
    if not check_csrf():
        return jsonify({"error": "요청을 확인할 수 없습니다."}), 403
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM score_events WHERE undone = 0 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return jsonify({"error": "취소할 점수 기록이 없습니다."}), 400
        conn.execute("UPDATE score_events SET undone = 1 WHERE id = ?", (row["id"],))
    return jsonify({"ok": True})


@app.post("/api/admin/teams")
@admin_required
def rename_teams():
    if not check_csrf():
        return jsonify({"error": "요청을 확인할 수 없습니다."}), 403
    data = request.get_json(silent=True) or {}
    names = data.get("names")
    if not isinstance(names, list) or len(names) != 3:
        return jsonify({"error": "팀 이름 3개를 입력해 주세요."}), 400
    cleaned = [str(n).strip()[:20] for n in names]
    if any(not n for n in cleaned):
        return jsonify({"error": "팀 이름을 비워둘 수 없습니다."}), 400
    with db() as conn:
        conn.executemany("UPDATE teams SET name = ? WHERE id = ?", [(name, i) for i, name in enumerate(cleaned, 1)])
    return jsonify({"ok": True})


@app.post("/api/admin/reset")
@admin_required
def reset_scores():
    if not check_csrf():
        return jsonify({"error": "요청을 확인할 수 없습니다."}), 403
    with db() as conn:
        conn.execute("UPDATE score_events SET undone = 1 WHERE undone = 0")
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    # 0.0.0.0 allows devices on the same network; ngrok can also forward to this port.
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
