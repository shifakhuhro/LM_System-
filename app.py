"""
Library Management System – Flask Application
"""

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta, datetime
import pymysql
import pymysql.cursors
from config import Config

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'


@app.context_processor
def inject_now():
    return {'now': datetime.now()}


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------
def get_db():
    """Return a new PyMySQL connection using app config."""
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


# ---------------------------------------------------------------------------
# User model (flask-login)
# ---------------------------------------------------------------------------
class User(UserMixin):
    def __init__(self, id, name, email, role):
        self.id = id
        self.name = name
        self.email = email
        self.role = role

    @property
    def is_librarian(self):
        return self.role == 'librarian'


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM users WHERE id=%s', (user_id,))
            row = cur.fetchone()
            if row:
                return User(row['id'], row['name'], row['email'], row['role'])
    finally:
        db.close()
    return None


# ---------------------------------------------------------------------------
# Fine helper
# ---------------------------------------------------------------------------
FINE_PER_DAY = Config.FINE_PER_DAY


def calc_fine(due_date, return_date=None):
    """Return fine amount for a borrow record."""
    check = return_date or date.today()
    if isinstance(due_date, str):
        due_date = date.fromisoformat(due_date)
    if isinstance(check, str):
        check = date.fromisoformat(check)
    overdue_days = (check - due_date).days
    return round(max(0, overdue_days) * FINE_PER_DAY, 2)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_librarian:
            return redirect(url_for('librarian_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute('SELECT * FROM users WHERE email=%s', (email,))
                row = cur.fetchone()
        finally:
            db.close()
        if row and check_password_hash(row['password'], password):
            user = User(row['id'], row['name'], row['email'], row['role'])
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            db = get_db()
            try:
                with db.cursor() as cur:
                    cur.execute('SELECT id FROM users WHERE email=%s', (email,))
                    if cur.fetchone():
                        flash('Email already registered.', 'danger')
                    else:
                        hashed = generate_password_hash(password)
                        cur.execute(
                            'INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,"user")',
                            (name, email, hashed)
                        )
                        db.commit()
                        flash('Account created! Please log in.', 'success')
                        return redirect(url_for('login'))
            finally:
                db.close()
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# User routes
# ---------------------------------------------------------------------------
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.is_librarian:
        return redirect(url_for('librarian_dashboard'))
    db = get_db()
    try:
        with db.cursor() as cur:
            # Active borrows
            cur.execute("""
                SELECT br.id, b.title, b.author, br.borrow_date,
                       br.due_date, br.fine_amount
                FROM borrow_records br
                JOIN books b ON b.id = br.book_id
                WHERE br.user_id = %s AND br.return_date IS NULL
                ORDER BY br.due_date
            """, (current_user.id,))
            active_borrows = cur.fetchall()

            # Update live fines for display
            today = date.today()
            for rec in active_borrows:
                rec['current_fine'] = calc_fine(rec['due_date'])
                rec['overdue'] = today > rec['due_date']

            # Past borrows
            cur.execute("""
                SELECT br.id, b.title, b.author, br.borrow_date,
                       br.due_date, br.return_date,
                       br.fine_amount, br.fine_paid
                FROM borrow_records br
                JOIN books b ON b.id = br.book_id
                WHERE br.user_id = %s AND br.return_date IS NOT NULL
                ORDER BY br.return_date DESC
                LIMIT 10
            """, (current_user.id,))
            past_borrows = cur.fetchall()

            # Total unpaid fines
            cur.execute("""
                SELECT COALESCE(SUM(fine_amount),0) AS total
                FROM borrow_records
                WHERE user_id=%s AND fine_paid=0 AND return_date IS NOT NULL
            """, (current_user.id,))
            unpaid = cur.fetchone()['total']
    finally:
        db.close()
    return render_template(
        'user/dashboard.html',
        active_borrows=active_borrows,
        past_borrows=past_borrows,
        unpaid_fines=unpaid,
    )


@app.route('/user/search')
@login_required
def search_books():
    if current_user.is_librarian:
        return redirect(url_for('librarian_dashboard'))
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    books = []
    categories = []
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT DISTINCT category FROM books WHERE category IS NOT NULL ORDER BY category')
            categories = [r['category'] for r in cur.fetchall()]
            sql = 'SELECT * FROM books WHERE 1=1'
            params = []
            if query:
                sql += ' AND (title LIKE %s OR author LIKE %s OR isbn LIKE %s)'
                like = f'%{query}%'
                params += [like, like, like]
            if category:
                sql += ' AND category=%s'
                params.append(category)
            sql += ' ORDER BY title'
            cur.execute(sql, params)
            books = cur.fetchall()
    finally:
        db.close()
    return render_template('user/search.html', books=books, query=query,
                           category=category, categories=categories)


@app.route('/user/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    if current_user.is_librarian:
        return redirect(url_for('librarian_dashboard'))
    db = get_db()
    try:
        with db.cursor() as cur:
            # Check if already borrowed this book and not returned
            cur.execute("""
                SELECT id FROM borrow_records
                WHERE user_id=%s AND book_id=%s AND return_date IS NULL
            """, (current_user.id, book_id))
            if cur.fetchone():
                flash('You already have this book borrowed.', 'warning')
                return redirect(url_for('search_books'))

            cur.execute('SELECT * FROM books WHERE id=%s', (book_id,))
            book = cur.fetchone()
            if not book:
                flash('Book not found.', 'danger')
                return redirect(url_for('search_books'))
            if book['available_copies'] < 1:
                flash('No copies available right now.', 'warning')
                return redirect(url_for('search_books'))

            borrow_date = date.today()
            due_date = borrow_date + timedelta(days=14)  # 2 weeks
            cur.execute("""
                INSERT INTO borrow_records (user_id, book_id, borrow_date, due_date)
                VALUES (%s, %s, %s, %s)
            """, (current_user.id, book_id, borrow_date, due_date))
            cur.execute("""
                UPDATE books SET available_copies = available_copies - 1
                WHERE id=%s
            """, (book_id,))
            db.commit()
            flash(f'"{book["title"]}" borrowed successfully! Due: {due_date}.', 'success')
    finally:
        db.close()
    return redirect(url_for('search_books'))


@app.route('/user/return/<int:record_id>', methods=['POST'])
@login_required
def return_book(record_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT br.*, b.title FROM borrow_records br
                JOIN books b ON b.id = br.book_id
                WHERE br.id=%s AND br.return_date IS NULL
            """, (record_id,))
            rec = cur.fetchone()
            if not rec:
                flash('Record not found or already returned.', 'danger')
                return redirect(url_for('user_dashboard'))

            # Only the borrower or a librarian can return
            if not current_user.is_librarian and rec['user_id'] != current_user.id:
                flash('Unauthorized.', 'danger')
                return redirect(url_for('user_dashboard'))

            return_date = date.today()
            fine = calc_fine(rec['due_date'], return_date)
            cur.execute("""
                UPDATE borrow_records
                SET return_date=%s, fine_amount=%s
                WHERE id=%s
            """, (return_date, fine, record_id))
            cur.execute("""
                UPDATE books SET available_copies = available_copies + 1
                WHERE id=%s
            """, (rec['book_id'],))
            db.commit()
            msg = f'"{rec["title"]}" returned.'
            if fine > 0:
                msg += f' Fine charged: ${fine:.2f}'
            flash(msg, 'success' if fine == 0 else 'warning')
    finally:
        db.close()
    if current_user.is_librarian:
        return redirect(url_for('librarian_borrows'))
    return redirect(url_for('user_dashboard'))


@app.route('/user/fines')
@login_required
def user_fines():
    if current_user.is_librarian:
        return redirect(url_for('librarian_dashboard'))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT br.id, b.title, br.borrow_date, br.due_date,
                       br.return_date, br.fine_amount, br.fine_paid
                FROM borrow_records br
                JOIN books b ON b.id = br.book_id
                WHERE br.user_id=%s AND br.fine_amount > 0
                ORDER BY br.return_date DESC
            """, (current_user.id,))
            fines = cur.fetchall()
            total_unpaid = sum(
                f['fine_amount'] for f in fines if not f['fine_paid']
            )
    finally:
        db.close()
    return render_template('user/fines.html', fines=fines, total_unpaid=total_unpaid)


# ---------------------------------------------------------------------------
# Librarian routes
# ---------------------------------------------------------------------------
def librarian_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_librarian:
            flash('Librarian access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/librarian/dashboard')
@login_required
@librarian_required
def librarian_dashboard():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS c FROM books')
            total_books = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) AS c FROM users WHERE role="user"')
            total_users = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) AS c FROM borrow_records WHERE return_date IS NULL')
            active_borrows = cur.fetchone()['c']
            cur.execute("""
                SELECT COALESCE(SUM(fine_amount),0) AS c
                FROM borrow_records WHERE fine_paid=0 AND return_date IS NOT NULL
            """)
            unpaid_fines = cur.fetchone()['c']

            # Recent activity
            cur.execute("""
                SELECT br.id, u.name AS user_name, b.title,
                       br.borrow_date, br.due_date, br.return_date
                FROM borrow_records br
                JOIN users u ON u.id = br.user_id
                JOIN books b ON b.id = br.book_id
                ORDER BY br.id DESC LIMIT 10
            """)
            recent = cur.fetchall()
    finally:
        db.close()
    return render_template(
        'librarian/dashboard.html',
        total_books=total_books,
        total_users=total_users,
        active_borrows=active_borrows,
        unpaid_fines=unpaid_fines,
        recent_activity=recent,
    )


# -- Books management --------------------------------------------------------
@app.route('/librarian/books')
@login_required
@librarian_required
def librarian_books():
    query = request.args.get('q', '').strip()
    db = get_db()
    try:
        with db.cursor() as cur:
            if query:
                like = f'%{query}%'
                cur.execute("""
                    SELECT * FROM books
                    WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s
                    ORDER BY title
                """, (like, like, like))
            else:
                cur.execute('SELECT * FROM books ORDER BY title')
            books = cur.fetchall()
    finally:
        db.close()
    return render_template('librarian/books.html', books=books, query=query)


@app.route('/librarian/books/add', methods=['GET', 'POST'])
@login_required
@librarian_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip() or None
        category = request.form.get('category', '').strip() or None
        try:
            copies = int(request.form.get('copies', 1))
        except ValueError:
            copies = 1
        if not title or not author:
            flash('Title and Author are required.', 'danger')
        else:
            db = get_db()
            try:
                with db.cursor() as cur:
                    cur.execute("""
                        INSERT INTO books (title, author, isbn, category,
                                          total_copies, available_copies)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """, (title, author, isbn, category, copies, copies))
                    db.commit()
                flash('Book added successfully.', 'success')
                return redirect(url_for('librarian_books'))
            except pymysql.IntegrityError:
                flash('ISBN already exists.', 'danger')
            finally:
                db.close()
    return render_template('librarian/book_form.html', book=None)


@app.route('/librarian/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@librarian_required
def edit_book(book_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('SELECT * FROM books WHERE id=%s', (book_id,))
            book = cur.fetchone()
        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('librarian_books'))

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            author = request.form.get('author', '').strip()
            isbn = request.form.get('isbn', '').strip() or None
            category = request.form.get('category', '').strip() or None
            try:
                total = int(request.form.get('copies', book['total_copies']))
            except ValueError:
                total = book['total_copies']
            borrowed = book['total_copies'] - book['available_copies']
            available = max(0, total - borrowed)
            if not title or not author:
                flash('Title and Author are required.', 'danger')
            else:
                try:
                    with db.cursor() as cur:
                        cur.execute("""
                            UPDATE books
                            SET title=%s, author=%s, isbn=%s, category=%s,
                                total_copies=%s, available_copies=%s
                            WHERE id=%s
                        """, (title, author, isbn, category, total, available, book_id))
                        db.commit()
                    flash('Book updated.', 'success')
                    return redirect(url_for('librarian_books'))
                except pymysql.IntegrityError:
                    flash('ISBN already used by another book.', 'danger')
    finally:
        db.close()
    return render_template('librarian/book_form.html', book=book)


@app.route('/librarian/books/delete/<int:book_id>', methods=['POST'])
@login_required
@librarian_required
def delete_book(book_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('DELETE FROM books WHERE id=%s', (book_id,))
            db.commit()
        flash('Book deleted.', 'success')
    finally:
        db.close()
    return redirect(url_for('librarian_books'))


# -- Users management --------------------------------------------------------
@app.route('/librarian/users')
@login_required
@librarian_required
def librarian_users():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.name, u.email, u.role, u.created_at,
                       COUNT(br.id) AS total_borrows
                FROM users u
                LEFT JOIN borrow_records br ON br.user_id = u.id
                GROUP BY u.id
                ORDER BY u.created_at DESC
            """)
            users = cur.fetchall()
    finally:
        db.close()
    return render_template('librarian/users.html', users=users)


@app.route('/librarian/users/delete/<int:user_id>', methods=['POST'])
@login_required
@librarian_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('librarian_users'))
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute('DELETE FROM users WHERE id=%s', (user_id,))
            db.commit()
        flash('User deleted.', 'success')
    finally:
        db.close()
    return redirect(url_for('librarian_users'))


# -- Borrow records ----------------------------------------------------------
@app.route('/librarian/borrows')
@login_required
@librarian_required
def librarian_borrows():
    filter_by = request.args.get('filter', 'active')
    db = get_db()
    try:
        with db.cursor() as cur:
            if filter_by == 'overdue':
                cur.execute("""
                    SELECT br.id, u.name AS user_name, b.title,
                           br.borrow_date, br.due_date, br.return_date,
                           br.fine_amount, br.fine_paid
                    FROM borrow_records br
                    JOIN users u ON u.id = br.user_id
                    JOIN books b ON b.id = br.book_id
                    WHERE br.return_date IS NULL AND br.due_date < CURDATE()
                    ORDER BY br.due_date
                """)
            elif filter_by == 'returned':
                cur.execute("""
                    SELECT br.id, u.name AS user_name, b.title,
                           br.borrow_date, br.due_date, br.return_date,
                           br.fine_amount, br.fine_paid
                    FROM borrow_records br
                    JOIN users u ON u.id = br.user_id
                    JOIN books b ON b.id = br.book_id
                    WHERE br.return_date IS NOT NULL
                    ORDER BY br.return_date DESC LIMIT 100
                """)
            else:  # active
                cur.execute("""
                    SELECT br.id, u.name AS user_name, b.title,
                           br.borrow_date, br.due_date, br.return_date,
                           br.fine_amount, br.fine_paid
                    FROM borrow_records br
                    JOIN users u ON u.id = br.user_id
                    JOIN books b ON b.id = br.book_id
                    WHERE br.return_date IS NULL
                    ORDER BY br.due_date
                """)
            records = cur.fetchall()
            # Compute live fine for active records
            today = date.today()
            for r in records:
                if r['return_date'] is None:
                    r['current_fine'] = calc_fine(r['due_date'])
                    r['overdue'] = today > r['due_date']
                else:
                    r['current_fine'] = r['fine_amount']
                    r['overdue'] = False
    finally:
        db.close()
    return render_template('librarian/borrows.html', records=records, filter_by=filter_by)


# -- Fines management --------------------------------------------------------
@app.route('/librarian/fines')
@login_required
@librarian_required
def librarian_fines():
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT br.id, u.name AS user_name, b.title,
                       br.return_date, br.fine_amount, br.fine_paid
                FROM borrow_records br
                JOIN users u ON u.id = br.user_id
                JOIN books b ON b.id = br.book_id
                WHERE br.fine_amount > 0
                ORDER BY br.fine_paid, br.return_date DESC
            """)
            fines = cur.fetchall()
            total_unpaid = sum(f['fine_amount'] for f in fines if not f['fine_paid'])
            total_collected = sum(f['fine_amount'] for f in fines if f['fine_paid'])
    finally:
        db.close()
    return render_template(
        'librarian/fines.html',
        fines=fines,
        total_unpaid=total_unpaid,
        total_collected=total_collected,
    )


@app.route('/librarian/fines/mark_paid/<int:record_id>', methods=['POST'])
@login_required
@librarian_required
def mark_fine_paid(record_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                'UPDATE borrow_records SET fine_paid=1 WHERE id=%s',
                (record_id,)
            )
            db.commit()
        flash('Fine marked as paid.', 'success')
    finally:
        db.close()
    return redirect(url_for('librarian_fines'))


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
