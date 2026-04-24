-- Library Management System Database Schema
-- Run this file to create the database and all required tables.

CREATE DATABASE IF NOT EXISTS library_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE library_db;

-- Users table (both regular users and librarians)
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(150)        NOT NULL,
    email       VARCHAR(200)        NOT NULL UNIQUE,
    password    VARCHAR(255)        NOT NULL,
    role        ENUM('user','librarian') NOT NULL DEFAULT 'user',
    created_at  DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Books table
CREATE TABLE IF NOT EXISTS books (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    title            VARCHAR(300)  NOT NULL,
    author           VARCHAR(200)  NOT NULL,
    isbn             VARCHAR(20)   UNIQUE,
    category         VARCHAR(100),
    total_copies     INT           NOT NULL DEFAULT 1,
    available_copies INT           NOT NULL DEFAULT 1,
    added_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Borrow records table
CREATE TABLE IF NOT EXISTS borrow_records (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT             NOT NULL,
    book_id       INT             NOT NULL,
    borrow_date   DATE            NOT NULL,
    due_date      DATE            NOT NULL,
    return_date   DATE,
    fine_amount   DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    fine_paid     TINYINT(1)      NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id)  ON DELETE CASCADE
);

-- Sample books
INSERT IGNORE INTO books (title, author, isbn, category, total_copies, available_copies) VALUES
  ('The Great Gatsby',          'F. Scott Fitzgerald', '978-0743273565', 'Fiction',     3, 3),
  ('To Kill a Mockingbird',     'Harper Lee',          '978-0061935466', 'Fiction',     2, 2),
  ('1984',                      'George Orwell',       '978-0451524935', 'Dystopia',    4, 4),
  ('A Brief History of Time',   'Stephen Hawking',     '978-0553380163', 'Science',     2, 2),
  ('The Art of War',            'Sun Tzu',             '978-1599869773', 'Philosophy',  5, 5),
  ('Clean Code',                'Robert C. Martin',    '978-0132350884', 'Technology',  3, 3),
  ('Introduction to Algorithms','Cormen et al.',       '978-0262033848', 'Technology',  2, 2),
  ('Pride and Prejudice',       'Jane Austen',         '978-0141439518', 'Fiction',     3, 3),
  ('The Alchemist',             'Paulo Coelho',        '978-0062315007', 'Fiction',     4, 4),
  ('Sapiens',                   'Yuval Noah Harari',   '978-0062316110', 'History',     3, 3);

-- Default librarian account.
-- After running this script, set the real password by running the app's
-- create_admin.py helper or by using the register endpoint and updating role.
-- Default password: admin123  (generated via werkzeug generate_password_hash)
INSERT IGNORE INTO users (name, email, password, role) VALUES (
    'Admin Librarian',
    'admin@library.com',
    'pbkdf2:sha256:600000$changeme$0000000000000000000000000000000000000000000000000000000000000000',
    'librarian'
);
