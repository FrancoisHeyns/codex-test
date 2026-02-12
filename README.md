# Staff Management MVP

This repository contains a minimal working MVP based on `STAFF_MANAGEMENT_SYSTEM_DESIGN.md`.

## Stack used in this environment
Because npm package installation is blocked in this execution environment, this MVP is implemented with:
- Python 3
- SQLite
- Built-in WSGI server (`wsgiref`)

It still delivers the requested core MVP behaviors:
- Login (email/password)
- Roles (`admin`, `manager`, `staff`)
- Tasks with create/assign/due date/priority/status
- Staff view: **My Tasks**
- Manager view: **Team Dashboard**
- DB migration + seed data

## 1) Setup

```bash
python3 --version
```

## 2) Run migrations + seed

```bash
python3 seed.py
```

This creates `staff_mvp.db` with:
- 1 admin: `admin@example.com / admin123`
- 1 manager: `manager@example.com / manager123`
- 2 staff: `staff1@example.com / staff123`, `staff2@example.com / staff123`
- Sample tasks

## 3) Start app

```bash
python3 app.py
```

Open: `http://localhost:8000`

## 4) Basic usage

1. Log in as manager (`manager@example.com / manager123`).
2. Open **Team Dashboard**.
3. Create a task and assign it to staff.
4. Log in as staff and use **My Tasks** to update status.

## 5) Run tests

```bash
python3 -m unittest discover -s tests -v
```

