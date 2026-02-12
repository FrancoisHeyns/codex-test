import hashlib
import secrets
from http import cookies
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from db import connect

SESSIONS: dict[str, dict] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def parse_body(environ):
    length = int(environ.get("CONTENT_LENGTH", "0") or "0")
    body = environ["wsgi.input"].read(length).decode("utf-8")
    return parse_qs(body)


def get_session(environ):
    raw = environ.get("HTTP_COOKIE", "")
    c = cookies.SimpleCookie(raw)
    session_id = c.get("session_id")
    if not session_id:
        return None
    return SESSIONS.get(session_id.value)


def respond(start_response, body, status="200 OK", headers=None):
    headers = headers or []
    headers.append(("Content-Type", "text/html; charset=utf-8"))
    start_response(status, headers)
    return [body.encode("utf-8")]


def redirect(start_response, location, set_cookie=None):
    headers = [("Location", location)]
    if set_cookie:
        headers.append(("Set-Cookie", set_cookie))
    start_response("302 Found", headers)
    return [b""]


def layout(title, content, user=None):
    nav = ""
    if user:
        nav = f"""
        <div style='margin-bottom:16px;'>
          Logged in as <b>{user['name']}</b> ({user['role']}) |
          <a href='/my-tasks'>My Tasks</a> |
          <a href='/team-dashboard'>Team Dashboard</a> |
          <a href='/logout'>Logout</a>
        </div>
        """
    return f"""
    <html><head><title>{title}</title></head>
    <body style='font-family: Arial; max-width: 900px; margin: 20px auto;'>
    <h1>{title}</h1>
    {nav}
    {content}
    </body></html>
    """


def require_login(environ, start_response):
    session = get_session(environ)
    if not session:
        return None, redirect(start_response, "/")
    return session, None


def fetch_user(user_id):
    with connect() as conn:
        row = conn.execute("SELECT id, email, role, name FROM users WHERE id = ?", (user_id,)).fetchone()
    return row


def app(environ, start_response):
    method = environ["REQUEST_METHOD"]
    path = environ.get("PATH_INFO", "/")

    if path == "/" and method == "GET":
        body = layout(
            "Staff MVP Login",
            """
            <form method='POST' action='/login'>
              <div>Email: <input name='email' /></div>
              <div>Password: <input type='password' name='password' /></div>
              <button type='submit'>Login</button>
            </form>
            <p>Seed users: admin@example.com/admin123, manager@example.com/manager123, staff1@example.com/staff123</p>
            """,
        )
        return respond(start_response, body)

    if path == "/login" and method == "POST":
        data = parse_body(environ)
        email = data.get("email", [""])[0].strip().lower()
        password = data.get("password", [""])[0]
        with connect() as conn:
            user = conn.execute(
                "SELECT id, email, role, name, password_hash FROM users WHERE email = ?", (email,)
            ).fetchone()
        if not user or user["password_hash"] != hash_password(password):
            return respond(start_response, layout("Login failed", "<p>Invalid credentials. <a href='/'>Try again</a></p>"), "401 Unauthorized")

        session_id = secrets.token_urlsafe(24)
        SESSIONS[session_id] = {"user_id": user["id"]}
        cookie = f"session_id={session_id}; Path=/; HttpOnly"
        return redirect(start_response, "/my-tasks", set_cookie=cookie)

    if path == "/logout":
        cookie = "session_id=; Path=/; Max-Age=0"
        return redirect(start_response, "/", set_cookie=cookie)

    if path == "/my-tasks" and method == "GET":
        session, redirect_response = require_login(environ, start_response)
        if redirect_response:
            return redirect_response
        user = fetch_user(session["user_id"])
        with connect() as conn:
            tasks = conn.execute(
                """
                SELECT t.id, t.title, t.due_date, t.priority, t.status, u.name as assigned_name
                FROM tasks t
                JOIN users u ON t.assigned_user_id = u.id
                WHERE t.assigned_user_id = ?
                ORDER BY t.due_date ASC
                """,
                (user["id"],),
            ).fetchall()

        rows = "".join(
            f"""
            <tr>
              <td>{t['title']}</td><td>{t['due_date']}</td><td>{t['priority']}</td><td>{t['status']}</td>
              <td>
                <form method='POST' action='/tasks/{t['id']}/status'>
                  <select name='status'>
                    <option value='not_started'>not_started</option>
                    <option value='in_progress'>in_progress</option>
                    <option value='blocked'>blocked</option>
                    <option value='completed'>completed</option>
                  </select>
                  <button type='submit'>Update</button>
                </form>
              </td>
            </tr>
            """
            for t in tasks
        )
        content = f"""
        <h2>My Tasks</h2>
        <table border='1' cellpadding='6'>
          <tr><th>Title</th><th>Due</th><th>Priority</th><th>Status</th><th>Update</th></tr>
          {rows or '<tr><td colspan=5>No tasks assigned.</td></tr>'}
        </table>
        """
        return respond(start_response, layout("My Tasks", content, user))

    if path.startswith("/tasks/") and path.endswith("/status") and method == "POST":
        session, redirect_response = require_login(environ, start_response)
        if redirect_response:
            return redirect_response
        user = fetch_user(session["user_id"])
        task_id = int(path.split("/")[2])
        data = parse_body(environ)
        status = data.get("status", ["not_started"])[0]
        if status not in {"not_started", "in_progress", "blocked", "completed"}:
            status = "not_started"
        with connect() as conn:
            owner = conn.execute("SELECT assigned_user_id FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if owner and (owner["assigned_user_id"] == user["id"] or user["role"] in {"manager", "admin"}):
                conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        return redirect(start_response, "/my-tasks")

    if path == "/team-dashboard" and method == "GET":
        session, redirect_response = require_login(environ, start_response)
        if redirect_response:
            return redirect_response
        user = fetch_user(session["user_id"])
        if user["role"] not in {"manager", "admin"}:
            return respond(start_response, layout("Forbidden", "<p>Manager/Admin only.</p>", user), "403 Forbidden")

        with connect() as conn:
            tasks = conn.execute(
                """
                SELECT t.id, t.title, t.due_date, t.priority, t.status, u.name as assigned_name
                FROM tasks t
                JOIN users u ON t.assigned_user_id = u.id
                ORDER BY t.due_date ASC
                """
            ).fetchall()
            staff = conn.execute("SELECT id, name FROM users WHERE role = 'staff' ORDER BY name").fetchall()

        rows = "".join(
            f"<tr><td>{t['title']}</td><td>{t['assigned_name']}</td><td>{t['due_date']}</td><td>{t['priority']}</td><td>{t['status']}</td></tr>"
            for t in tasks
        )
        options = "".join(f"<option value='{s['id']}'>{s['name']}</option>" for s in staff)
        content = f"""
        <h2>All Team Tasks</h2>
        <table border='1' cellpadding='6'>
          <tr><th>Title</th><th>Assigned To</th><th>Due</th><th>Priority</th><th>Status</th></tr>
          {rows or '<tr><td colspan=5>No tasks yet.</td></tr>'}
        </table>

        <h3>Create Task</h3>
        <form method='POST' action='/tasks/create'>
          <div>Title: <input name='title' required /></div>
          <div>Description: <input name='description' /></div>
          <div>Assign to: <select name='assigned_user_id'>{options}</select></div>
          <div>Due date: <input name='due_date' type='date' required /></div>
          <div>Priority:
            <select name='priority'>
              <option value='low'>low</option>
              <option value='medium'>medium</option>
              <option value='high'>high</option>
            </select>
          </div>
          <button type='submit'>Create Task</button>
        </form>
        """
        return respond(start_response, layout("Team Dashboard", content, user))

    if path == "/tasks/create" and method == "POST":
        session, redirect_response = require_login(environ, start_response)
        if redirect_response:
            return redirect_response
        user = fetch_user(session["user_id"])
        if user["role"] not in {"manager", "admin"}:
            return respond(start_response, layout("Forbidden", "<p>Manager/Admin only.</p>", user), "403 Forbidden")

        data = parse_body(environ)
        title = data.get("title", [""])[0].strip()
        description = data.get("description", [""])[0].strip()
        assigned_user_id = int(data.get("assigned_user_id", ["0"])[0])
        due_date = data.get("due_date", [""])[0]
        priority = data.get("priority", ["medium"])[0]
        if priority not in {"low", "medium", "high"}:
            priority = "medium"

        if title and due_date and assigned_user_id:
            with connect() as conn:
                conn.execute(
                    """
                    INSERT INTO tasks
                    (title, description, assigned_user_id, created_by_user_id, due_date, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'not_started')
                    """,
                    (title, description, assigned_user_id, user["id"], due_date, priority),
                )
        return redirect(start_response, "/team-dashboard")

    return respond(start_response, layout("Not found", "<p>Route not found.</p>"), "404 Not Found")


if __name__ == "__main__":
    print("Starting Staff MVP app on http://localhost:8000")
    httpd = make_server("0.0.0.0", 8000, app)
    httpd.serve_forever()
