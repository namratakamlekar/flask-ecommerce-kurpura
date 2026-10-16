import os
import secrets
import uuid
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash, abort, send_from_directory)
from werkzeug.security import check_password_hash

from db import get_all, get_one, run

app = Flask(__name__)
app.secret_key = "change-this-admin-secret-key"
app.config["SESSION_COOKIE_NAME"] = "admin_session"
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

# product photos live in the user site's folder, so both sites share them
IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "user", "static", "img", "products")
WEBSITE_URL = "http://127.0.0.1:5000"
STATUSES = ["Placed", "Packed", "Shipped", "Delivered", "Cancelled"]

ORDER_SQL = """
    SELECT o.*, 1000 + o.id AS number, u.email AS email,
           (SELECT SUM(qty) FROM order_items WHERE order_id = o.id) AS item_count
    FROM orders o JOIN users u ON u.id = o.user_id
"""


# ---------- helpers ----------
def logged_in():
    return "admin_id" in session


@app.before_request
def check_login_and_csrf():
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if token != session.get("csrf_token"):
            abort(400, "Invalid form token. Go back, refresh the page and try again.")
    open_pages = ["login", "static"]
    if not logged_in() and request.endpoint not in open_pages:
        return redirect(url_for("login"))


@app.context_processor
def template_values():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    values = {"csrf_token": session["csrf_token"], "website_url": WEBSITE_URL}
    if logged_in():
        admin = get_one("SELECT email FROM admins WHERE id = ?", (session["admin_id"],))
        values["admin_email"] = admin["email"] if admin else ""
        values["placed_count"] = get_one("SELECT COUNT(*) AS n FROM orders WHERE status = 'Placed'")["n"]
        values["unread_count"] = get_one("SELECT COUNT(*) AS n FROM messages WHERE is_read = 0")["n"]
    return values


@app.template_filter("rupees")
def rupees(number):
    return "₹{:,}".format(int(number or 0))


@app.errorhandler(400)
def bad_request(error):
    return error.description, 400


# ---------- login ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect(url_for("dashboard"))
    error = False

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        admin = get_one("SELECT * FROM admins WHERE email = ?", (email,))
        if admin and check_password_hash(admin["password_hash"], request.form.get("password", "")):
            session["admin_id"] = admin["id"]
            return redirect(url_for("dashboard"))
        error = True

    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_id", None)
    return redirect(url_for("login"))


# ---------- dashboard ----------
@app.route("/")
def dashboard():
    stats = {
        "orders": get_one("SELECT COUNT(*) AS n FROM orders")["n"],
        "revenue": get_one("SELECT COALESCE(SUM(total), 0) AS n FROM orders WHERE status != 'Cancelled'")["n"],
        "customers": get_one("SELECT COUNT(*) AS n FROM users")["n"],
        "products": get_one("SELECT COUNT(*) AS n FROM products")["n"],
        "unread": get_one("SELECT COUNT(*) AS n FROM messages WHERE is_read = 0")["n"],
    }
    by_status = []
    for status in STATUSES:
        count = get_one("SELECT COUNT(*) AS n FROM orders WHERE status = ?", (status,))["n"]
        by_status.append((status, count))
    max_n = max([count for status, count in by_status] + [1])

    top = get_all("""SELECT oi.name AS name, SUM(oi.qty) AS sold
                     FROM order_items oi JOIN orders o ON o.id = oi.order_id
                     WHERE o.status != 'Cancelled'
                     GROUP BY oi.name ORDER BY sold DESC LIMIT 5""")
    recent = get_all(ORDER_SQL + " ORDER BY o.id DESC LIMIT 6")

    return render_template("dashboard.html", page="dashboard", title="Dashboard", stats=stats,
                           by_status=by_status, max_n=max_n, top=top, recent=recent)


# ---------- orders ----------
@app.route("/orders")
def orders():
    q = request.args.get("q", "").strip().lstrip("#")
    status = request.args.get("status", "")

    sql = ORDER_SQL + " WHERE 1 = 1"
    args = []
    if status in STATUSES:
        sql += " AND o.status = ?"
        args.append(status)
    if q:
        sql += " AND (u.email LIKE ? OR o.ship_name LIKE ? OR CAST(1000 + o.id AS TEXT) LIKE ?)"
        args += ["%" + q + "%"] * 3

    rows = get_all(sql + " ORDER BY o.id DESC", args)
    return render_template("orders.html", page="orders", title="Orders", orders=rows,
                           q=q, st=status, statuses=STATUSES)


@app.route("/orders/<int:id>")
def order_detail(id):
    order = get_one(ORDER_SQL + " WHERE o.id = ?", (id,))
    if not order:
        abort(404)
    order["order_items"] = get_all("SELECT * FROM order_items WHERE order_id = ?", (id,))
    return render_template("order_detail.html", page="orders", title="Order #" + str(order["number"]),
                           order=order, statuses=STATUSES)


@app.route("/orders/<int:id>/status", methods=["POST"])
def order_status(id):
    status = request.form.get("status")
    if status in STATUSES:
        run("UPDATE orders SET status = ? WHERE id = ?", (status, id))
        flash("Order #" + str(1000 + id) + " is now " + status)
    back = request.form.get("back", "")
    return redirect(back if back.startswith("/") else url_for("orders"))


# ---------- products ----------
@app.route("/product-images/<name>")
def product_image(name):
    return send_from_directory(IMAGE_FOLDER, name)


@app.route("/products")
def products():
    rows = get_all("""SELECT p.*, c.name AS category FROM products p
                      JOIN categories c ON c.id = p.category_id ORDER BY p.id""")
    return render_template("products.html", page="products", title="Products", products=rows)


@app.route("/products/new", methods=["GET", "POST"])
@app.route("/products/<int:id>/edit", methods=["GET", "POST"])
def product_form(id=None):
    categories = get_all("SELECT * FROM categories ORDER BY id")
    if id:
        p = get_one("SELECT * FROM products WHERE id = ?", (id,))
        if not p:
            abort(404)
    else:
        p = {"id": None, "name": "", "name_hi": "", "description": "", "price": "", "mrp": "",
             "size": "", "tag": "", "active": 1, "category_id": 1, "image": "logo.png"}
    error = None

    if request.method == "POST":
        f = request.form
        p.update({"name": f.get("name", "").strip(), "name_hi": f.get("name_hi", "").strip(),
                  "description": f.get("description", "").strip(), "size": f.get("size", "").strip(),
                  "tag": f.get("tag", "").strip(), "active": 1 if "active" in f else 0,
                  "category_id": int(f.get("category_id", 1))})
        try:
            p["price"] = int(f.get("price", ""))
            p["mrp"] = int(f.get("mrp", ""))
        except ValueError:
            error = "Price and MRP must be whole numbers."

        if not error and not p["name"]:
            error = "Product name is required."
        elif not error and (p["price"] < 1 or p["mrp"] < 1):
            error = "Price and MRP must be at least 1."
        elif not error and p["price"] > p["mrp"]:
            error = "Price cannot be higher than MRP."

        photo = request.files.get("image")
        if not error and photo and photo.filename:
            extension = os.path.splitext(photo.filename)[1].lower()
            if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
                error = "Photo must be a JPG, PNG or WEBP file."
            else:
                p["image"] = uuid.uuid4().hex[:12] + extension
                photo.save(os.path.join(IMAGE_FOLDER, p["image"]))

        if not error:
            values = (p["name"], p["name_hi"], p["description"], p["price"], p["mrp"], p["size"],
                      p["image"], p["tag"], p["active"], p["category_id"])
            if id:
                run("UPDATE products SET name=?, name_hi=?, description=?, price=?, mrp=?, size=?, "
                    "image=?, tag=?, active=?, category_id=? WHERE id=?", values + (id,))
            else:
                run("INSERT INTO products (name, name_hi, description, price, mrp, size, image, tag, "
                    "active, category_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values)
            flash("Product saved")
            return redirect(url_for("products"))

    return render_template("product_form.html", page="products",
                           title="Edit product" if id else "Add product",
                           p=p, error=error, categories=categories)


# ---------- customers ----------
@app.route("/customers")
def customers():
    q = request.args.get("q", "").strip()
    sql = """SELECT u.*, COUNT(o.id) AS order_count, COALESCE(SUM(o.total), 0) AS spent
             FROM users u LEFT JOIN orders o ON o.user_id = u.id AND o.status != 'Cancelled'
             WHERE (u.name LIKE ? OR u.email LIKE ? OR u.phone LIKE ?)
             GROUP BY u.id ORDER BY u.id DESC"""
    rows = get_all(sql, ["%" + q + "%"] * 3)
    return render_template("customers.html", page="customers", title="Customers", rows=rows, q=q)


# ---------- messages ----------
@app.route("/messages")
def messages():
    rows = get_all("SELECT * FROM messages ORDER BY id DESC")
    return render_template("messages.html", page="messages", title="Messages", messages=rows)


@app.route("/messages/<int:id>/toggle", methods=["POST"])
def message_toggle(id):
    run("UPDATE messages SET is_read = 1 - is_read WHERE id = ?", (id,))
    return redirect(url_for("messages"))


@app.route("/messages/<int:id>/delete", methods=["POST"])
def message_delete(id):
    run("DELETE FROM messages WHERE id = ?", (id,))
    return redirect(url_for("messages"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
