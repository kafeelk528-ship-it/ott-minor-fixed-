import os
from flask import Flask, render_template, redirect, url_for, request, session, flash
import requests

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# Telegram config (set on Render as env vars)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

# Admin credentials (set as env vars on Render)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "12345")

# Product data
PLANS = [
    {"id": 1, "name": "Netflix Premium", "price": 199, "logo": "netflix.png", "desc": "4K UHD • 30 Days", "stock": 10},
    {"id": 2, "name": "Amazon Prime Video", "price": 149, "logo": "prime.png", "desc": "HD • 30 Days", "stock": 12},
    {"id": 3, "name": "Disney+ Hotstar", "price": 299, "logo": "hotstar.png", "desc": "Sports + Movies", "stock": 8},
    {"id": 4, "name": "Sony LIV Premium", "price": 129, "logo": "sonyliv.png", "desc": "TV Shows + Movies", "stock": 15},
    {"id": 5, "name": "Zee5 Premium", "price": 99, "logo": "zee5.png", "desc": "HD Content", "stock": 20},
]

def get_plan(pid):
    return next((p for p in PLANS if int(p["id"]) == int(pid)), None)

@app.route("/")
def home():
    return render_template("index.html", plans=PLANS)

@app.route("/plans")
def plans_page():
    return render_template("plans.html", plans=PLANS)

@app.route("/plan/<int:plan_id>")
def plan_details(plan_id):
    plan = get_plan(plan_id)
    if not plan:
        return "Plan not found", 404
    return render_template("plan-details.html", plan=plan)

# Cart
@app.route("/add-to-cart/<int:plan_id>")
def add_to_cart(plan_id):
    if get_plan(plan_id) is None:
        flash("Invalid product", "danger")
        return redirect(url_for("plans_page"))
    session.setdefault("cart", [])
    if plan_id not in session["cart"]:
        session["cart"].append(plan_id)
    session.modified = True
    flash("Added to cart")
    return redirect(url_for("cart_page"))

@app.route("/cart")
def cart_page():
    cart_items = [get_plan(pid) for pid in session.get("cart", []) if get_plan(pid)]
    total = sum(int(i["price"]) for i in cart_items)
    return render_template("cart.html", cart=cart_items, total=total)

@app.route("/remove/<int:plan_id>")
def remove_item(plan_id):
    if "cart" in session and plan_id in session["cart"]:
        session["cart"].remove(plan_id)
        session.modified = True
    return redirect(url_for("cart_page"))

# Payment + UTR
@app.route("/payment")
def payment_page():
    cart_items = [get_plan(pid) for pid in session.get("cart", []) if get_plan(pid)]
    if not cart_items:
        flash("Cart is empty", "info")
        return redirect(url_for("plans_page"))
    total = sum(int(i["price"]) for i in cart_items)
    return render_template("payment.html", total=total)

@app.route("/submit_utr", methods=["POST"])
def submit_utr():
    utr = (request.form.get("utr") or "").strip()
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    if not utr:
        flash("Please enter UTR", "danger")
        return redirect(url_for("payment_page"))
    cart_items = [get_plan(pid) for pid in session.get("cart", []) if get_plan(pid)]
    total = sum(int(i["price"]) for i in cart_items)
    message = f"*New payment received*\nName: {name or '-'}\nPhone: {phone or '-'}\nUTR: `{utr}`\nAmount: ₹{total}\nItems: {', '.join(i['name'] for i in cart_items)}"
    if BOT_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            app.logger.exception("Telegram error: %s", e)
    # clear cart
    session.pop("cart", None)
    flash("UTR submitted. Owner will verify.", "success")
    return render_template("success.html")

# Contact
@app.route("/contact")
def contact_page():
    return render_template("contact.html")

# Admin
@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("admin.html", error=True)
    return render_template("admin.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    return render_template("dashboard.html", plans=PLANS)

@app.route("/admin/add-plan", methods=["POST"])
def admin_add_plan():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    new_id = max([p["id"] for p in PLANS]) + 1 if PLANS else 1
    PLANS.append({
        "id": new_id,
        "name": request.form.get("name"),
        "price": int(request.form.get("price") or 0),
        "logo": request.form.get("logo") or "netflix.png",
        "desc": request.form.get("desc") or "",
        "stock": int(request.form.get("stock") or 0)
    })
    flash("Plan added", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete-plan/<int:plan_id>", methods=["POST"])
def admin_delete_plan(plan_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    global PLANS
    PLANS = [p for p in PLANS if p["id"] != plan_id]
    flash("Plan deleted", "info")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT",5000)), debug=(os.getenv("FLASK_ENV","")!="production"))
