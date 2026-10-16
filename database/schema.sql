DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS admins;

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    image TEXT
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    name_hi TEXT DEFAULT '',
    description TEXT DEFAULT '',
    price INTEGER NOT NULL,
    mrp INTEGER NOT NULL,
    size TEXT DEFAULT '',
    image TEXT,
    tag TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    category_id INTEGER NOT NULL REFERENCES categories(id)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    password_hash TEXT NOT NULL
);

CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT DEFAULT 'Placed',
    date TEXT,
    subtotal INTEGER,
    delivery INTEGER,
    total INTEGER,
    payment TEXT DEFAULT 'Cash on Delivery',
    ship_name TEXT,
    ship_phone TEXT,
    ship_address TEXT,
    ship_city TEXT,
    ship_pin TEXT
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    name TEXT NOT NULL,
    price INTEGER NOT NULL,
    qty INTEGER NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    text TEXT NOT NULL,
    date TEXT,
    is_read INTEGER DEFAULT 0
);

