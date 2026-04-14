from flask import Flask, render_template, request, redirect
import pymysql
import os
import time

app = Flask(__name__, static_folder='static', template_folder='templates')

# ---------------- DATABASE CONFIG ----------------
DB_HOST = os.environ.get("DB_HOST", "host.docker.internal")  # use 172.17.0.1 for Linux
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "dairy")

# ---------------- DB CONNECTION ----------------
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# ---------------- INIT DB (OPTIONAL SAFETY) ----------------
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
                    product VARCHAR(50),
                    quantity VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()
            print("✅ Database connected & table ready")
            break

        except Exception as e:
            print("⏳ Waiting for DB connection...", e)
            time.sleep(3)

# Run DB init
init_db()

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('index.html')

# ---------------- PLACE ORDER ----------------
@app.route('/place-order', methods=['POST'])
def place_order():
    name = request.form['name']
    mobile = request.form['mobile']
    address = request.form['address']
    product = request.form['product']
    quantity = request.form['quantity']

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO orders (name, mobile, address, product, quantity)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (name, mobile, address, product, quantity)
    )

    conn.commit()
    conn.close()

    return redirect('/orders')

# ---------------- ORDER HISTORY ----------------
@app.route('/orders')
def orders():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template('orders.html', orders=data)

# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
