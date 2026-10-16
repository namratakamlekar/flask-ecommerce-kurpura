import re
import secrets
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_all, get_one, run

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.config["SESSION_COOKIE_NAME"] = "user_session"

MAX_QTY = 20
FREE_DELIVERY_ABOVE = 499
DELIVERY_FEE = 49

PRODUCT_SQL = """
    SELECT p.*, c.name AS category, c.id - 1 AS css_index,
           CAST(ROUND((1.0 - p.price * 1.0 / p.mrp) * 100) AS INTEGER) AS discount
    FROM products p JOIN categories c ON c.id = p.category_id
"""


# ---------- helpers ----------
def current_user():
    if "user_id" in session:
        return get_one("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    return None


def cart_lines():
    lines = []
    subtotal = 0
    for product_id, qty in session.get("cart", {}).items():
        product = get_one(PRODUCT_SQL + " WHERE p.id = ? AND p.active = 1", (int(product_id),))
        if product:
            total = product["price"] * qty
            lines.append({"product": product, "qty": qty, "total": total})
            subtotal += total
    return lines, subtotal


@app.before_request
def check_csrf():
    if request.method == "POST":
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if token != session.get("csrf_token"):
            abort(400, "Invalid form token. Go back, refresh the page and try again.")


@app.context_processor
def template_values():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return {
        "csrf_token": session["csrf_token"],
        "current_user": current_user(),
        "cart_count": sum(session.get("cart", {}).values()),
    }


@app.template_filter("rupees")
def rupees(number):
    return "₹{:,}".format(int(number or 0))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("error.html", title="Page not found",
                           text="The page you are looking for does not exist."), 404


@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", title="Something went wrong", text=error.description), 400


# ---------- home, shop, product ----------
@app.route("/")
def index():
    featured = get_all(PRODUCT_SQL + " WHERE p.id IN (1, 2, 6, 11) AND p.active = 1")
    categories = get_all("SELECT * FROM categories ORDER BY id")
    return render_template("index.html", featured=featured, categories=categories)


@app.route("/shop")
def shop():
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "")
    sort = request.args.get("sort", "default")

    categories = get_all("SELECT * FROM categories ORDER BY id")
    if cat not in [c["name"] for c in categories]:
        cat = ""

    sql = PRODUCT_SQL + " WHERE p.active = 1"
    args = []
    if cat:
        sql += " AND c.name = ?"
        args.append(cat)
    if q:
        sql += " AND (p.name LIKE ? OR p.name_hi LIKE ?)"
        args += ["%" + q + "%", "%" + q + "%"]

    sort_options = {"low": "p.price ASC", "high": "p.price DESC", "name": "p.name ASC"}
    sql += " ORDER BY " + sort_options.get(sort, "p.id ASC")

    products = get_all(sql, args)
    return render_template("shop.html", products=products, categories=categories,
                           q=q, cat=cat, sort=sort)


@app.route("/product/<int:id>")
def product(id):
    p = get_one(PRODUCT_SQL + " WHERE p.id = ? AND p.active = 1", (id,))
    if not p:
        abort(404)
    related = get_all(PRODUCT_SQL + " WHERE p.id != ? AND p.active = 1 "
                      "ORDER BY (p.category_id = ?) DESC, p.id LIMIT 4", (id, p["category_id"]))
    return render_template("product.html", p=p, related=related)


# ---------- info pages ----------
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/shipping-returns")
def shipping_returns():
    return render_template("shipping_returns.html")


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    user = current_user()
    form = {"name": "", "email": "", "text": ""}
    if user:
        form["name"] = user["name"]
        form["email"] = user["email"]
    error = None
    success = None

    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["email"] = request.form.get("email", "").strip()
        form["text"] = request.form.get("text", "").strip()

        if not form["name"] or not re.match(r"^\S+@\S+\.\S+$", form["email"]) or not form["text"]:
            error = "Please fill in your name, a valid email and a message."
        elif len(form["text"]) > 2000:
            error = "Message is too long (max 2000 characters)."
        else:
            run("INSERT INTO messages (name, email, text, date) VALUES (?, ?, ?, ?)",
                (form["name"], form["email"].lower(), form["text"],
                 datetime.now().strftime("%d %b %Y, %I:%M %p")))
            success = "Thank you, " + form["name"].split()[0] + ". We have received your message and will reply by email."
            form["text"] = ""

    return render_template("contact.html", form=form, error=error, success=success)


# ---------- register, login, account ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("account"))
    error = None
    form = {"name": "", "email": "", "phone": ""}

    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["email"] = request.form.get("email", "").strip().lower()
        form["phone"] = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if len(form["name"]) < 2:
            error = "Enter your full name."
        elif not re.match(r"^\S+@\S+\.\S+$", form["email"]):
            error = "Enter a valid email address."
        elif not re.match(r"^[6-9]\d{9}$", form["phone"]):
            error = "Enter a valid 10-digit mobile number."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif get_one("SELECT id FROM users WHERE email = ?", (form["email"],)):
            error = "This email is already registered. Try logging in."
        else:
            user_id = run("INSERT INTO users (name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
                          (form["name"], form["email"], form["phone"], generate_password_hash(password)))
            session["user_id"] = user_id
            return redirect(url_for("account"))

    return render_template("register.html", error=error, form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    next_page = request.values.get("next", "")
    if not next_page.startswith("/") or next_page.startswith("//"):
        next_page = ""

    if "user_id" in session:
        return redirect(next_page or url_for("account"))
    error = None
    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_one("SELECT * FROM users WHERE email = ?", (email,))

        if not email or not password:
            error = "Enter your email and password."
        elif not user or not check_password_hash(user["password_hash"], password):
            error = "Email or password is incorrect."
        else:
            session["user_id"] = user["id"]
            return redirect(next_page or url_for("account"))

    return render_template("login.html", error=error, email=email, next=next_page)


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


@app.route("/account")
def account():
    user = current_user()
    if not user:
        return redirect(url_for("login", next="/account"))
    orders = get_all("SELECT *, 1000 + id AS number FROM orders WHERE user_id = ? ORDER BY id DESC",
                     (user["id"],))
    for order in orders:
        order["order_items"] = get_all("SELECT * FROM order_items WHERE order_id = ?", (order["id"],))
    return render_template("account.html", user=user, orders=orders)


@app.route("/orders/<int:id>/cancel", methods=["POST"])
def cancel_order(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    run("UPDATE orders SET status = 'Cancelled' WHERE id = ? AND user_id = ? AND status = 'Placed'",
        (id, session["user_id"]))
    return redirect(url_for("account"))


# ---------- cart ----------
@app.route("/cart")
def cart():
    lines, subtotal = cart_lines()
    return render_template("cart.html", lines=lines, subtotal=subtotal)


@app.route("/cart/add/<int:id>", methods=["POST"])
def cart_add(id):
    product = get_one("SELECT name FROM products WHERE id = ? AND active = 1", (id,))
    if not product:
        abort(404)
    data = request.get_json(silent=True) or {}
    try:
        qty = max(1, min(MAX_QTY, int(data.get("qty", 1))))
    except (TypeError, ValueError):
        qty = 1

    cart = session.get("cart", {})
    cart[str(id)] = min(cart.get(str(id), 0) + qty, MAX_QTY)
    session["cart"] = cart
    return jsonify(name=product["name"], count=sum(cart.values()))


@app.route("/cart/update/<int:id>", methods=["POST"])
def cart_update(id):
    cart = session.get("cart", {})
    key = str(id)
    action = request.form.get("op")

    if key in cart:
        if action == "inc":
            cart[key] = min(cart[key] + 1, MAX_QTY)
        elif action == "dec" and cart[key] > 1:
            cart[key] -= 1
        else:
            del cart[key]
    session["cart"] = cart
    return redirect(url_for("cart"))


# ---------- checkout ----------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    user = current_user()
    if not user:
        return redirect(url_for("login", next="/checkout"))
    lines, subtotal = cart_lines()
    if not lines:
        return redirect(url_for("cart"))

    delivery = 0 if subtotal >= FREE_DELIVERY_ABOVE else DELIVERY_FEE
    total = subtotal + delivery
    form = {"name": user["name"], "phone": user["phone"] or "", "address": "", "city": "", "pin": ""}
    error = None

    if request.method == "POST":
        for field in form:
            form[field] = request.form.get(field, "").strip()
        digits = re.sub(r"\D", "", form["phone"])

        if not form["name"] or not form["address"] or not form["city"]:
            error = "Please fill in your name, address and city."
        elif len(digits) < 10:
            error = "Please enter a valid 10-digit phone number."
        elif not re.match(r"^[0-9]{6}$", form["pin"]):
            error = "Please enter a 6-digit pincode."
        else:
            order_id = run(
                "INSERT INTO orders (user_id, date, subtotal, delivery, total, ship_name, ship_phone, "
                "ship_address, ship_city, ship_pin) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user["id"], datetime.now().strftime("%d %b %Y"), subtotal, delivery, total,
                 form["name"], digits[-10:], form["address"], form["city"], form["pin"]))
            for line in lines:
                run("INSERT INTO order_items (order_id, name, price, qty) VALUES (?, ?, ?, ?)",
                    (order_id, line["product"]["name"], line["product"]["price"], line["qty"]))
            session["cart"] = {}
            return redirect(url_for("order_success", id=order_id))

    return render_template("checkout.html", lines=lines, subtotal=subtotal, delivery=delivery,
                           total=total, form=form, error=error, free_above=FREE_DELIVERY_ABOVE)


@app.route("/order-success/<int:id>")
def order_success(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    order = get_one("SELECT *, 1000 + id AS number FROM orders WHERE id = ? AND user_id = ?",
                    (id, session["user_id"]))
    if order:
        order["order_items"] = get_all("SELECT * FROM order_items WHERE order_id = ?", (id,))
    return render_template("order_success.html", order=order)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
