from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import pymysql
import os
import time
import smtplib
from email.mime.text import MIMEText
import urllib.parse
import json
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
DB_HOST = os.environ.get("DB_HOST", "host.docker.internal")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "dairy")

PRICE_LIST = {
    "Milk": 60,
    "Cheese": 400,
    "Curd": 80
}

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4'
    )

# ---------------- INIT DB ----------------
def init_db():
    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                mobile VARCHAR(20),
                password VARCHAR(100),
                location TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                cart TEXT,
                total_price INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            conn.commit()
            conn.close()
            print("✅ DB READY")
            break

        except Exception as e:
            print("⏳ Waiting DB...", e)
            time.sleep(3)

init_db()

# ---------------- TEMPLATE FILTER ----------------
@app.template_filter('from_json')
def from_json(value):
    return json.loads(value)

# ---------------- EMAIL ----------------
def send_email(text):
    try:
        sender = os.environ.get("EMAIL_USER")
        password = os.environ.get("EMAIL_PASS")
        receiver = os.environ.get("ADMIN_EMAIL")

        msg = MIMEText(text, "plain", "utf-8")
        msg['Subject'] = "New Order"
        msg['From'] = sender
        msg['To'] = receiver

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email error:", e)

# ---------------- WHATSAPP ----------------
def send_whatsapp(message):
    encoded = urllib.parse.quote(message)
    return f"https://wa.me/918755831257?text={encoded}"

# ---------------- AUTH ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fn = request.form['first_name']
        ln = request.form['last_name']
        mob = request.form['mobile']
        pwd = request.form['password']
        loc = request.form['location']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users (first_name, last_name, mobile, password, location)
        VALUES (%s,%s,%s,%s,%s)
        """, (fn, ln, mob, pwd, loc))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mob = request.form['mobile']
        pwd = request.form['password']

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE mobile=%s AND password=%s", (mob, pwd))
        user = cursor.fetchone()

        conn.close()

        if user:
            session['user_id'] = user[0]
            session['name'] = user[1]
            return redirect('/')
        else:
            return "❌ Invalid login"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- CART (SESSION BASED) ----------------
@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.json
    product = data['product']
    price = PRICE_LIST.get(product, 0)

    if 'cart' not in session:
        session['cart'] = []

    cart = session['cart']
    cart.append({"product": product, "price": price})
    session['cart'] = cart

    return jsonify({"status": "ok"})


@app.route('/get-cart')
def get_cart():
    return jsonify(session.get('cart', []))


@app.route('/remove-from-cart', methods=['POST'])
def remove():
    idx = request.json['index']
    cart = session.get('cart', [])

    if idx < len(cart):
        cart.pop(idx)

    session['cart'] = cart
    return jsonify({"status": "removed"})

# ---------------- HOME ----------------
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html', name=session['name'])

# ---------------- CHECKOUT ----------------
@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect('/login')

    cart = session.get('cart', [])
    total = sum(item['price'] for item in cart)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO orders (user_id, cart, total_price)
    VALUES (%s,%s,%s)
    """, (session['user_id'], json.dumps(cart), total))

    conn.commit()
    conn.close()

    msg = f"Order by {session['name']} Total ₹{total}"

    send_email(msg)
    whatsapp_url = send_whatsapp(msg)

    session['cart'] = []

    return render_template("payment.html", total=total, whatsapp_url=whatsapp_url)

# ---------------- ADMIN ----------------
@app.route('/admin')
def admin():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        orders.id,
        users.first_name,
        users.mobile,
        orders.cart,
        orders.total_price,
        orders.created_at
    FROM orders
    JOIN users ON orders.user_id = users.id
    ORDER BY orders.id DESC
    """)

    orders = cursor.fetchall()
    conn.close()

    total_revenue = sum([o[4] for o in orders]) if orders else 0

    return render_template("admin.html", orders=orders, total=total_revenue)


#-------------------INVOICE---------------
# ---------------- INVOICE PDF ----------------
@app.route('/invoice/<int:order_id>')
def invoice(order_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        orders.id,
        users.first_name,
        users.mobile,
        orders.cart,
        orders.total_price,
        orders.created_at
    FROM orders
    JOIN users ON orders.user_id = users.id
    WHERE orders.id=%s
    """, (order_id,))

    order = cursor.fetchone()
    conn.close()

    if not order:
        return "Order not found"

    # -------- PDF GENERATION --------
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("Choudhry Dairy Invoice", styles['Title']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Order ID: {order[0]}", styles['Normal']))
    elements.append(Paragraph(f"Customer: {order[1]}", styles['Normal']))
    elements.append(Paragraph(f"Mobile: {order[2]}", styles['Normal']))
    elements.append(Paragraph(f"Date: {order[5]}", styles['Normal']))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Items:", styles['Heading3']))

    cart = json.loads(order[3])

    for item in cart:
        elements.append(Paragraph(f"{item['product']} - ₹{item['price']}", styles['Normal']))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Total: ₹{order[4]}", styles['Heading2']))

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_{order_id}.pdf",
        mimetype='application/pdf'
    )



# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
