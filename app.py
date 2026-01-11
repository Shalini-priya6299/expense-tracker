from flask import Flask, render_template, request, redirect, url_for
import mysql.connector, json
from datetime import date

app = Flask(__name__)

# -------------------- DATABASE CONNECTION --------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="NewPassword123!",
        database="expense_tracker",
        port=3306
    )

@app.route("/health")
def health():
    return "App is running"


# -------------------- DASHBOARD --------------------
@app.route("/")
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    today = date.today()

    # Selected month/year
    month = int(request.args.get("month", today.month))
    year = int(request.args.get("year", today.year))

    # ---------------- TOTAL EXPENSE ----------------
    cursor.execute("""
        SELECT SUM(amount) AS total
        FROM expenses
        WHERE MONTH(expense_date)=%s AND YEAR(expense_date)=%s
    """, (month, year))
    total_expense = cursor.fetchone()["total"] or 0

    # ---------------- CATEGORY-WISE ----------------
    cursor.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE MONTH(expense_date)=%s AND YEAR(expense_date)=%s
        GROUP BY category
    """, (month, year))
    rows = cursor.fetchall()

    categories = [r["category"] for r in rows]
    amounts = [float(r["total"]) for r in rows]

    # ---------------- TOP CATEGORY ----------------
    cursor.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE MONTH(expense_date)=%s AND YEAR(expense_date)=%s
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """, (month, year))
    top = cursor.fetchone()

    top_category_name = top["category"] if top else None
    top_category_amount = float(top["total"]) if top else 0

    # ---------------- MONTHLY BUDGET ----------------
    cursor.execute("SELECT amount FROM monthly_budget LIMIT 1")
    budget_row = cursor.fetchone()

    budget_amount = budget_row["amount"] if budget_row else None
    budget_exceeded = budget_amount and total_expense > budget_amount

    # ---------------- YEAR RANGE ----------------
    cursor.execute("""
        SELECT MIN(YEAR(expense_date)) AS min_year,
               MAX(YEAR(expense_date)) AS max_year
        FROM expenses
    """)
    yr = cursor.fetchone()
    min_year = yr["min_year"] or year
    max_year = max(yr["max_year"] or year, year) + 1

    # ---------------- MONTH vs PREVIOUS MONTH ----------------
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1

    cursor.execute("""
        SELECT DAY(expense_date) AS day, SUM(amount) AS total
        FROM expenses
        WHERE MONTH(expense_date)=%s AND YEAR(expense_date)=%s
        GROUP BY DAY(expense_date)
        ORDER BY day
    """, (month, year))
    current_rows = cursor.fetchall()

    cursor.execute("""
        SELECT DAY(expense_date) AS day, SUM(amount) AS total
        FROM expenses
        WHERE MONTH(expense_date)=%s AND YEAR(expense_date)=%s
        GROUP BY DAY(expense_date)
        ORDER BY day
    """, (prev_month, prev_year))
    prev_rows = cursor.fetchall()

    days = list(range(1, 32))
    current_map = {r["day"]: float(r["total"]) for r in current_rows}
    prev_map = {r["day"]: float(r["total"]) for r in prev_rows}

    current_data = [current_map.get(d, 0) for d in days]
    prev_data = [prev_map.get(d, 0) for d in days]

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_expense=total_expense,
        categories=json.dumps(categories),
        amounts=json.dumps(amounts),
        top_category_name=top_category_name,
        top_category_amount=top_category_amount,
        budget_amount=budget_amount,
        budget_exceeded=budget_exceeded,
        selected_month=month,
        selected_year=year,
        month_label=date(year, month, 1).strftime("%B %Y"),
        min_year=min_year,
        max_year=max_year,
        days=json.dumps(days),
        current_data=json.dumps(current_data),
        prev_data=json.dumps(prev_data),
        prev_month_label=date(prev_year, prev_month, 1).strftime("%B %Y")
    )


# -------------------- SET BUDGET --------------------
@app.route("/set_budget", methods=["POST"])
def set_budget():
    budget = request.form["budget"]
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM monthly_budget")
    cursor.execute("INSERT INTO monthly_budget (amount) VALUES (%s)", (budget,))
    conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))


# -------------------- ADD EXPENSE --------------------
@app.route("/add", methods=["GET", "POST"])
def add_expense():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO expenses (title, amount, category, expense_date)
            VALUES (%s, %s, %s, %s)
        """, (
            request.form["title"],
            request.form["amount"],
            request.form["category"],
            request.form["date"]
        ))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("show_expenses"))

    return render_template("add_expense.html")


# -------------------- SHOW EXPENSES --------------------
@app.route("/expenses")
def show_expenses():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM expenses ORDER BY expense_date DESC")
    expenses = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("expenses.html", expenses=expenses)


# -------------------- EDIT EXPENSE --------------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute("""
            UPDATE expenses
            SET title=%s, amount=%s, category=%s, expense_date=%s
            WHERE id=%s
        """, (
            request.form["title"],
            request.form["amount"],
            request.form["category"],
            request.form["date"],
            id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("show_expenses"))

    cursor.execute("SELECT * FROM expenses WHERE id=%s", (id,))
    expense = cursor.fetchone()

    cursor.close()
    conn.close()
    return render_template("edit_expense.html", expense=expense)


# -------------------- DELETE EXPENSE --------------------
@app.route("/delete/<int:id>")
def delete_expense(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM expenses WHERE id=%s", (id,))
    conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for("show_expenses"))


if __name__ == "__main__":
    app.run(debug=True)
