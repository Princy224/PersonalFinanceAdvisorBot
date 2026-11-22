
import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template_string,
    redirect, url_for, flash, session
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", "personal-finance-advisor-secret"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "finance.db")

# ---------------- GEMINI CONFIGURATION ----------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

gemini_client = None

try:
    if GEMINI_API_KEY:
        from google import genai
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print("Gemini initialization error:", e)


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- DATABASE INITIALIZATION ----------------

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            monthly_income REAL DEFAULT 0,
            savings_goal REAL DEFAULT 0,
            currency TEXT DEFAULT 'INR'
        )
    """)

    # Automatically repair older settings tables.
    existing_columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(settings)").fetchall()
    ]

    required_columns = {
        "monthly_income": "REAL DEFAULT 0",
        "savings_goal": "REAL DEFAULT 0",
        "currency": "TEXT DEFAULT 'INR'"
    }

    for column, definition in required_columns.items():
        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE settings ADD COLUMN {column} {definition}"
            )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            transaction_date TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO settings
        (id, monthly_income, savings_goal, currency)
        VALUES (1, 0, 0, 'INR')
    """)

    conn.commit()
    conn.close()

    print("Database initialized successfully!")


# ---------------- SETTINGS ----------------

def get_settings():
    conn = get_db()

    settings = conn.execute(
        "SELECT * FROM settings WHERE id = 1"
    ).fetchone()

    conn.close()

    return dict(settings) if settings else {
        "monthly_income": 0,
        "savings_goal": 0,
        "currency": "INR"
    }


# ---------------- TRANSACTION DATA ----------------

def get_transactions():
    conn = get_db()

    transactions = conn.execute("""
        SELECT * FROM transactions
        ORDER BY transaction_date DESC, id DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in transactions]


def calculate_finances():
    settings = get_settings()
    transactions = get_transactions()

    income = float(settings["monthly_income"] or 0)

    expenses = sum(
        t["amount"] for t in transactions
        if t["transaction_type"] == "Expense"
    )

    additional_income = sum(
        t["amount"] for t in transactions
        if t["transaction_type"] == "Income"
    )

    total_income = income + additional_income
    balance = total_income - expenses

    # 50-30-20 budgeting rule
    needs = total_income * 0.50
    wants = total_income * 0.30
    savings = total_income * 0.20

    return {
        "income": total_income,
        "base_income": income,
        "additional_income": additional_income,
        "expenses": expenses,
        "balance": balance,
        "needs": needs,
        "wants": wants,
        "savings": savings,
        "savings_goal": float(settings["savings_goal"] or 0),
        "savings_progress": (
            max(0, balance) / settings["savings_goal"] * 100
            if settings["savings_goal"] > 0 else 0
        ),
        "transactions": transactions
    }


# ---------------- LOCAL FINANCIAL ADVISOR ----------------

def local_advisor(question, finances):
    q = question.lower()

    income = finances["income"]
    expenses = finances["expenses"]
    balance = finances["balance"]
    savings = finances["savings"]

    if any(word in q for word in ["50-30-20", "budget", "budgeting"]):
        return f"""
Your monthly budget using the 50-30-20 rule:

1. Needs (50%): ₹{finances['needs']:,.2f}
2. Wants (30%): ₹{finances['wants']:,.2f}
3. Savings (20%): ₹{savings:,.2f}

Your total monthly income is ₹{income:,.2f}.

Try to keep essential expenses within 50% of your income.
"""

    if any(word in q for word in ["sip", "mutual fund", "investment"]):
        return """
SIP (Systematic Investment Plan) allows you to invest
a fixed amount regularly in a mutual fund.

Benefits:
1. Encourages regular investing.
2. Supports disciplined saving.
3. Allows rupee-cost averaging.
4. Can help build long-term wealth.

Before investing, understand market risks, fund charges,
your time horizon and your risk tolerance.

SIPs do not guarantee returns. This is educational
information, not personalized financial advice.
"""

    if any(word in q for word in ["save", "saving", "savings"]):
        return f"""
Your current monthly income: ₹{income:,.2f}
Your total expenses: ₹{expenses:,.2f}
Your remaining balance: ₹{balance:,.2f}

Suggested monthly savings target (20%):
₹{savings:,.2f}

Suggestions:
1. Set aside savings immediately after receiving income.
2. Track unnecessary expenses.
3. Build an emergency fund.
4. Set a realistic monthly savings goal.
"""

    if any(word in q for word in ["expense", "spending"]):
        return f"""
Your financial summary:

Monthly income: ₹{income:,.2f}
Total expenses: ₹{expenses:,.2f}
Remaining balance: ₹{balance:,.2f}

Try tracking expenses by category and reducing
unnecessary purchases.
"""

    if any(word in q for word in ["hello", "hi", "hey"]):
        return """
Hello! Welcome to your Personal Finance Advisor Bot.

I can help you with:
1. Monthly budgeting.
2. Saving money.
3. Understanding SIPs.
4. Expense management.
5. The 50-30-20 budgeting rule.

Ask me any personal finance learning question!
"""

    return f"""
Here is your current financial overview:

Monthly income: ₹{income:,.2f}
Monthly expenses: ₹{expenses:,.2f}
Remaining balance: ₹{balance:,.2f}

My suggestions:

1. Follow the 50-30-20 budgeting method.
2. Try saving 20% of your income.
3. Monitor your monthly expenses.
4. Build an emergency fund.
5. Learn about SIPs before making investment decisions.

You can ask me specifically about budgeting, savings,
expenses or SIPs for more information.
"""


# ---------------- GEMINI AI RESPONSE ----------------

def get_ai_response(question, finances):
    if gemini_client:
        try:
            prompt = f"""
You are a friendly Personal Finance Advisor Bot
designed to educate students about personal finance.

Explain everything in simple English.

Financial information:
Monthly income: Rs. {finances['income']}
Monthly expenses: Rs. {finances['expenses']}
Remaining balance: Rs. {finances['balance']}

50-30-20 budget:
Needs: Rs. {finances['needs']}
Wants: Rs. {finances['wants']}
Savings: Rs. {finances['savings']}

User question:
{question}

Instructions:
- Explain budgeting, saving and SIP concepts simply.
- Use the user's financial information where relevant.
- Give practical educational suggestions.
- Do not guarantee investment returns.
- Do not claim to be a certified financial advisor.
- Do not invent financial data.
- Keep the answer clear and organized.
- Include a brief educational disclaimer.
"""

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

            if response and response.text:
                return response.text.strip()

        except Exception as e:
            print("Gemini API Error:", str(e))

    print("Using built-in advisor fallback.")
    return local_advisor(question, finances)


# ---------------- DASHBOARD HTML ----------------

PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Personal Finance Advisor Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        * { box-sizing: border-box; }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f3f5fa;
            color: #222;
        }

        header {
            background: #172554;
            color: white;
            padding: 22px;
            text-align: center;
        }

        header h1 { margin: 0; }

        .container {
            max-width: 1150px;
            margin: 25px auto;
            padding: 15px;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 15px;
        }

        .card {
            background: white;
            padding: 22px;
            border-radius: 12px;
            box-shadow: 0 3px 12px #00000010;
        }

        .card h3 {
            color: #64748b;
            font-size: 14px;
        }

        .amount {
            font-size: 23px;
            font-weight: bold;
            color: #172554;
        }

        .section {
            background: white;
            margin-top: 22px;
            padding: 22px;
            border-radius: 12px;
            box-shadow: 0 3px 12px #00000010;
        }

        input, select, textarea {
            width: 100%;
            padding: 12px;
            margin: 8px 0 14px;
            border: 1px solid #cbd5e1;
            border-radius: 7px;
        }

        button {
            padding: 12px 18px;
            background: #2563eb;
            border: none;
            color: white;
            border-radius: 7px;
            cursor: pointer;
        }

        button:hover { background: #1d4ed8; }

        .delete {
            background: #dc2626;
            padding: 7px 10px;
        }

        .budget-row { margin: 18px 0; }

        .bar {
            background: #e2e8f0;
            height: 13px;
            border-radius: 20px;
            overflow: hidden;
        }

        .fill {
            background: #2563eb;
            height: 100%;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        .chat-box {
            height: 300px;
            overflow-y: auto;
            background: #f8fafc;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }

        .message {
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            white-space: pre-wrap;
            line-height: 1.5;
        }

        .user {
            background: #dbeafe;
            text-align: right;
        }

        .bot { background: #e2e8f0; }

        .note {
            font-size: 12px;
            color: #64748b;
            margin-top: 15px;
        }

        .flash {
            padding: 12px;
            background: #dcfce7;
            border-radius: 8px;
            margin-bottom: 12px;
        }

        @media(max-width:600px) {
            table { font-size: 12px; }
            th, td { padding: 7px; }
        }
    </style>
</head>

<body>

<header>
    <h1>💰 Personal Finance Advisor Bot</h1>
    <p>Manage Money | Track Expenses | Plan Savings</p>
</header>

<div class="container">

{% with messages = get_flashed_messages() %}
    {% for message in messages %}
        <div class="flash">{{ message }}</div>
    {% endfor %}
{% endwith %}

<div class="cards">

    <div class="card">
        <h3>Monthly Income</h3>
        <div class="amount">₹{{ "%.2f"|format(f.income) }}</div>
    </div>

    <div class="card">
        <h3>Total Expenses</h3>
        <div class="amount">₹{{ "%.2f"|format(f.expenses) }}</div>
    </div>

    <div class="card">
        <h3>Remaining Balance</h3>
        <div class="amount">₹{{ "%.2f"|format(f.balance) }}</div>
    </div>

    <div class="card">
        <h3>Suggested Savings (20%)</h3>
        <div class="amount">₹{{ "%.2f"|format(f.savings) }}</div>
    </div>

</div>

<div class="section">
    <h2>⚙️ Monthly Financial Settings</h2>

    <form action="/settings" method="POST">

        <label>Monthly Income (₹)</label>
        <input type="number" name="monthly_income"
               min="0" step="0.01"
               value="{{ settings.monthly_income }}" required>

        <label>Monthly Savings Goal (₹)</label>
        <input type="number" name="savings_goal"
               min="0" step="0.01"
               value="{{ settings.savings_goal }}" required>

        <button type="submit">Save Settings</button>
    </form>
</div>

<div class="section">
    <h2>📊 50-30-20 Budget Planner</h2>

    <div class="budget-row">
        <b>Needs (50%) - ₹{{ "%.2f"|format(f.needs) }}</b>
        <div class="bar">
            <div class="fill" style="width:50%"></div>
        </div>
    </div>

    <div class="budget-row">
        <b>Wants (30%) - ₹{{ "%.2f"|format(f.wants) }}</b>
        <div class="bar">
            <div class="fill" style="width:30%;background:#16a34a"></div>
        </div>
    </div>

    <div class="budget-row">
        <b>Savings (20%) - ₹{{ "%.2f"|format(f.savings) }}</b>
        <div class="bar">
            <div class="fill" style="width:20%;background:#f59e0b"></div>
        </div>
    </div>

    <p>These are suggested allocations based on monthly income.</p>
</div>

<div class="section">
    <h2>➕ Add Income / Expense</h2>

    <form action="/add_transaction" method="POST">

        <label>Transaction Type</label>
        <select name="transaction_type" required>
            <option value="Expense">Expense</option>
            <option value="Income">Income</option>
        </select>

        <label>Category</label>
        <select name="category" required>
            <option>Food</option>
            <option>Travel</option>
            <option>Education</option>
            <option>Shopping</option>
            <option>Bills</option>
            <option>Entertainment</option>
            <option>Salary</option>
            <option>Other</option>
        </select>

        <label>Amount (₹)</label>
        <input type="number" name="amount"
               min="0.01" step="0.01" required>

        <label>Description</label>
        <input type="text" name="description"
               placeholder="Enter transaction details">

        <button type="submit">Add Transaction</button>
    </form>
</div>

<div class="section">
    <h2>📋 Transaction History</h2>

    <table>
        <tr>
            <th>Type</th>
            <th>Category</th>
            <th>Amount</th>
            <th>Date</th>
            <th>Action</th>
        </tr>

        {% for t in f.transactions %}
        <tr>
            <td>{{ t.transaction_type }}</td>
            <td>{{ t.category }}</td>
            <td>₹{{ "%.2f"|format(t.amount) }}</td>
            <td>{{ t.transaction_date }}</td>
            <td>
                <form action="/delete_transaction/{{ t.id }}"
                      method="POST">
                    <button class="delete" type="submit">Delete</button>
                </form>
            </td>
        </tr>
        {% else %}
        <tr>
            <td colspan="5">No transactions added yet.</td>
        </tr>
        {% endfor %}
    </table>
</div>

<div class="section">
    <h2>🤖 AI Personal Finance Advisor</h2>
    <p>Ask questions about budgeting, savings, expenses and SIPs.</p>

    <div class="chat-box" id="chatBox">
        <div class="message bot">
            Hello! I am your Personal Finance Advisor.
            Ask me about the 50-30-20 rule, SIPs or saving money!
        </div>
    </div>

    <form id="chatForm">
        <textarea id="question"
                  placeholder="Ask your finance question..."
                  rows="3" required></textarea>

        <button type="submit" id="sendBtn">Send Message</button>
    </form>

    <button type="button" onclick="clearChat()"
            style="background:#64748b">
        Clear Chat
    </button>

    <p class="note">
        AI-generated responses are educational only and do not
        constitute personalized financial advice.
        Investments are subject to market risks.
    </p>
</div>

<div class="section">
    <h2>💡 Financial Tips</h2>
    <ul>
        <li>Save a portion of your income every month.</li>
        <li>Track all your expenses.</li>
        <li>Build an emergency fund.</li>
        <li>Avoid unnecessary spending.</li>
        <li>Understand investment risks before investing.</li>
    </ul>
</div>

</div>

<script>
const chatBox = document.getElementById("chatBox");
const chatForm = document.getElementById("chatForm");
const questionInput = document.getElementById("question");
const sendBtn = document.getElementById("sendBtn");

function addMessage(text, type) {
    const div = document.createElement("div");
    div.className = "message " + type;
    div.textContent = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

chatForm.addEventListener("submit", async function(e) {
    e.preventDefault();

    const question = questionInput.value.trim();
    if (!question) return;

    addMessage(question, "user");
    questionInput.value = "";
    sendBtn.disabled = true;
    sendBtn.textContent = "Thinking...";

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question: question})
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to get response.");
        }

        addMessage(data.answer, "bot");

    } catch(error) {
        addMessage("Error: " + error.message, "bot");
    }

    sendBtn.disabled = false;
    sendBtn.textContent = "Send Message";
});

async function clearChat() {
    try {
        await fetch("/clear-chat", {method: "POST"});
        chatBox.innerHTML = "";
        addMessage("Chat cleared. Ask me a new question!", "bot");
    } catch(e) {
        addMessage("Unable to clear chat.", "bot");
    }
}
</script>

</body>
</html>
"""


# ---------------- HOME / DASHBOARD ----------------

@app.route("/")
@app.route("/dashboard")
def dashboard():
    finances = calculate_finances()
    settings = get_settings()

    return render_template_string(
        PAGE,
        f=finances,
        settings=settings
    )


# ---------------- SAVE SETTINGS ----------------

@app.route("/settings", methods=["POST"])
def save_settings():
    try:
        income = float(request.form.get("monthly_income", 0))
        goal = float(request.form.get("savings_goal", 0))

        if income < 0 or goal < 0:
            raise ValueError("Values cannot be negative.")

        conn = get_db()

        conn.execute("""
            UPDATE settings
            SET monthly_income = ?,
                savings_goal = ?
            WHERE id = 1
        """, (income, goal))

        conn.commit()
        conn.close()

        flash("Financial settings saved successfully!")

    except (ValueError, TypeError):
        flash("Please enter valid positive amounts.")

    return redirect(url_for("dashboard"))


# ---------------- ADD TRANSACTION ----------------

@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    try:
        transaction_type = request.form.get("transaction_type")
        category = request.form.get("category", "Other")
        amount = float(request.form.get("amount", 0))
        description = request.form.get("description", "")

        if transaction_type not in ["Income", "Expense"]:
            raise ValueError("Invalid transaction type.")

        if amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        conn = get_db()

        conn.execute("""
            INSERT INTO transactions
            (transaction_type, category, amount,
             description, transaction_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            transaction_type,
            category,
            amount,
            description,
            datetime.now().strftime("%Y-%m-%d")
        ))

        conn.commit()
        conn.close()

        flash("Transaction added successfully!")

    except (ValueError, TypeError):
        flash("Please enter a valid transaction amount.")

    return redirect(url_for("dashboard"))


# ---------------- DELETE TRANSACTION ----------------

@app.route("/delete_transaction/<int:transaction_id>",
           methods=["POST"])
def delete_transaction(transaction_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM transactions WHERE id = ?",
        (transaction_id,)
    )

    conn.commit()
    conn.close()

    flash("Transaction deleted successfully!")

    return redirect(url_for("dashboard"))


# ---------------- CHATBOT API ----------------

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()

    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    if len(question) > 3000:
        return jsonify({"error": "Question is too long."}), 400

    finances = calculate_finances()

    answer = get_ai_response(question, finances)

    # Save chat history in SQLite
    conn = get_db()

    conn.execute("""
        INSERT INTO chat_history
        (question, answer, created_at)
        VALUES (?, ?, ?)
    """, (
        question,
        answer,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "answer": answer,
        "success": True
    })


# ---------------- CHAT HISTORY ----------------

@app.route("/chat-history")
def chat_history():
    conn = get_db()

    history = conn.execute("""
        SELECT * FROM chat_history
        ORDER BY id DESC
        LIMIT 50
    """).fetchall()

    conn.close()

    return jsonify([
        dict(row) for row in history
    ])


# ---------------- CLEAR CHAT ----------------

@app.route("/clear-chat", methods=["POST"])
def clear_chat():
    conn = get_db()
    conn.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()

    return jsonify({"success": True})


# ---------------- FINANCIAL SUMMARY API ----------------

@app.route("/api/summary")
def api_summary():
    finances = calculate_finances()

    return jsonify({
        "income": finances["income"],
        "expenses": finances["expenses"],
        "balance": finances["balance"],
        "needs": finances["needs"],
        "wants": finances["wants"],
        "savings": finances["savings"]
    })


# ---------------- HEALTH CHECK ----------------

@app.route("/health")
def health():
    return jsonify({
        "status": "running",
        "application": "Personal Finance Advisor Bot",
        "database": os.path.exists(DB_NAME),
        "gemini_configured": gemini_client is not None
    })


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    init_db()

    print("--------------------------------------")
    print("PERSONAL FINANCE ADVISOR BOT")
    print("--------------------------------------")
    print("Database:", DB_NAME)
    print("Gemini available:", gemini_client is not None)
    print("Open: http://127.0.0.1:5000")
    print("--------------------------------------")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
