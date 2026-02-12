import hashlib
from db import connect, run_migration


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed(db_path: str | None = None):
    run_migration(db_path)
    with connect(db_path) as conn:
        users = [
            ("admin@example.com", hash_password("admin123"), "admin", "Alice Admin"),
            ("manager@example.com", hash_password("manager123"), "manager", "Mark Manager"),
            ("staff1@example.com", hash_password("staff123"), "staff", "Sara Staff"),
            ("staff2@example.com", hash_password("staff123"), "staff", "Sam Staff"),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)",
            users,
        )

        user_map = {
            row["email"]: row["id"]
            for row in conn.execute("SELECT id, email FROM users")
        }

        sample_tasks = [
            (
                "Open store checklist",
                "Daily opening checks",
                user_map["staff1@example.com"],
                user_map["manager@example.com"],
                "2026-02-15",
                "high",
                "not_started",
            ),
            (
                "Weekly inventory count",
                "Count and report variances",
                user_map["staff2@example.com"],
                user_map["manager@example.com"],
                "2026-02-16",
                "medium",
                "in_progress",
            ),
        ]

        conn.executemany(
            """
            INSERT OR IGNORE INTO tasks
            (title, description, assigned_user_id, created_by_user_id, due_date, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            sample_tasks,
        )


if __name__ == "__main__":
    seed()
    print("Database migrated and seeded.")
