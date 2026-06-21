# Library Management System (LMS)

A web-based Library Management System built with **Flask** and **MySQL**.  
Users and librarians log in through the website. The system handles book search, borrowing, returns, due-date tracking, and automatic fine calculation.

---

## Features

| Role | Capabilities |
|------|-------------|
| **User** | Register / Login, Search books by title/author/ISBN/category, Borrow & return books, View active borrows and fine history |
| **Librarian** | Full user-management dashboard, Add / Edit / Delete books, View all borrow records (active, overdue, returned), Manage & mark fines as paid |

---

## Tech Stack

- **Backend** – Python 3, Flask 2, Flask-Login, PyMySQL
- **Database** – MySQL 8
- **Frontend** – Jinja2 templates, Bootstrap 5, Bootstrap Icons

---

## Prerequisites

- Python 3.10+
- MySQL 8 running locally (or a remote server)
- [VS Code](https://code.visualstudio.com/) with the **Python** extension

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/shifakhuhro/LM_System-.git
cd LM_System-
```

### 2. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set your MySQL credentials:

```ini
SECRET_KEY=your-very-secret-key-change-this
MYSQL_HOST=localhost
MYSQL_USER=lmsuser
MYSQL_PASSWORD=lmspass
MYSQL_DB=library_db
```

### 5. Initialise the database

Create the MySQL user and database first:

```sql
-- run in MySQL shell as root
CREATE USER IF NOT EXISTS 'lmsuser'@'localhost' IDENTIFIED BY 'lmspass';
GRANT ALL ON library_db.* TO 'lmsuser'@'localhost';
FLUSH PRIVILEGES;
```

Then run the init script (creates tables + admin account + sample books):

```bash
python init_db.py
```

Default librarian credentials: **admin@library.com** / **admin123**

---

## Running in VS Code

1. **Open the project folder** in VS Code (`File → Open Folder…`).

2. **Install recommended extensions** – VS Code will prompt you automatically.  
   Or open the Extensions panel, search `@recommended`, and install all.

3. **Select the Python interpreter** – press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac),  
   type `Python: Select Interpreter`, and choose `.venv`.

4. **Set up `.env`** – make sure step 4 above is done so the DB credentials are available.

5. **Start debugging** – press `F5` (or go to **Run → Start Debugging**).  
   Select the **"Flask: Run LMS"** configuration.

6. Open your browser at **http://127.0.0.1:5000**

> **Tip:** Breakpoints work in both Python files and Jinja2 templates. The debugger reloads automatically when you save a file.

### Alternative: run from the integrated terminal

```bash
flask --app app run --debug
```

---

## Project Structure

```
LM_System-/
├── app.py              # Flask application & all routes
├── config.py           # Configuration (reads from .env)
├── init_db.py          # One-time DB initialisation script
├── schema.sql          # SQL schema + sample data
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .vscode/
│   ├── launch.json     # VS Code debug configurations
│   ├── settings.json   # Editor & Python settings
│   └── extensions.json # Recommended extensions
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── user/
    │   ├── dashboard.html
    │   ├── search.html
    │   └── fines.html
    └── librarian/
        ├── dashboard.html
        ├── books.html
        ├── book_form.html
        ├── users.html
        ├── borrows.html
        └── fines.html
```

---

## Fine Policy

Books are due **14 days** after borrowing.  
A fine of **$0.50 per overdue day** is calculated automatically on return.  
Librarians can mark fines as paid from the Fines dashboard.