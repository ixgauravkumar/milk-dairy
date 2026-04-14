from flask import Flask, render_template, request, redirect, send_file
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

app = Flask(__name__, static_folder='static', template_folder='templates')

# ---------------- DATABASE CONFIG ----------------
DB_HOST = os.environ.get("DB_HOST", "host.docker.internal")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "dairy")

# ---------------- DB CONNECTION ----------------
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
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    mobile VARCHAR(20),
                    address TEXT,
                    cart TEXT,
                    total_price INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4
            """)

            conn.commit()
            conn.close()
            print("✅ Database ready")
            break

        except Exception as e:
            print("⏳ Waiting for DB...", e)
            time.sleep(3)

init_db()

# ---------------- EMAIL FUNCTION ----------------
def send_email(order_details):
    try:
        sender = os.environ.get("EMAIL_USER")
        password = os.environ.get("EMAIL_PASS")
        receiver = os.environ.get("ADMIN_EMAIL")

        msg = MIMEText(order_details, "plain", "utf-8")
        msg['Subject'] = "New Dairy Order"
        msg['From'] = sender
        msg['To'] = receiver

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()

        print("📧 Email sent successfully")

    except Exception as e:
        print("❌ Email error:", e)

# ---------------- WHATSAPP FUNCTION ----------------
def send_whatsapp(message):
    encoded_msg = urllib.parse.quote(message)
    phone = "918755831257"
    return f"https://wa.me/{phone}?text={encoded_msg}"

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('index.html')

# ---------------- CHECKOUT ----------------
@app.route('/checkout', methods=['POST'])
def checkout():

    name = request.form['name']
    mobile = request.form['mobile']
    address = request.form['address']
    cart_data = request.form['cart_data']

    cart = json.loads(cart_data)

    total_price = 0
    order_summary = ""

    for item in cart:
        product = item['product']
        price = item['price']
        total_price += price
        order_summary += f"{product} - ₹{price}\n"

    # Save to DB
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO orders (name, mobile, address, cart, total_price)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, mobile, address, json.dumps(cart), total_price))

    conn.commit()
    conn.close()

    # EMAIL
    order_text = f"""
New Order Received:

Name: {name}
Mobile: {mobile}
Address: {address}

Items:
{order_summary}

Total: ₹{total_price}
"""
    send_email(order_text)

    # WHATSAPP
    whatsapp_url = send_whatsapp(order_text)

    return render_template(
        "payment.html",
        name=name,
        total=total_price,
        whatsapp_url=whatsapp_url
    )

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()

    conn.close()

    total_revenue = sum([o[5] for o in orders]) if orders else 0

    return render_template("admin.html", orders=orders, total=total_revenue)

# ---------------- INVOICE PDF ----------------
@app.route('/invoice/<int:order_id>')
def invoice(order_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()

    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("Choudhry Dairy Invoice", styles['Title']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"Order ID: {order[0]}", styles['Normal']))
    elements.append(Paragraph(f"Name: {order[1]}", styles['Normal']))
    elements.append(Paragraph(f"Mobile: {order[2]}", styles['Normal']))
    elements.append(Paragraph(f"Address: {order[3]}", styles['Normal']))
    elements.append(Paragraph(f"Cart: {order[4]}", styles['Normal']))
    elements.append(Paragraph(f"Total: ₹{order[5]}", styles['Normal']))

    doc.build(elements)

    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"invoice_{order_id}.pdf")

# ---------------- ORDER HISTORY ----------------
@app.route('/orders')
def orders():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template('orders.html', orders=data)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
