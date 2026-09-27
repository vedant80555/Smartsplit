from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///smartsplit.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# -------------------------
# Person Table
# -------------------------
class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)


# -------------------------
# Expense Table
# -------------------------
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_by = db.Column(db.String(100), nullable=False)


# -------------------------
# Expense Participant Table
# -------------------------
class ExpenseParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, nullable=False)
    person_name = db.Column(db.String(100), nullable=False)
    share = db.Column(db.Float, nullable=False)


# -------------------------
# Home Page
# -------------------------
@app.route("/")
def home():
    people = Person.query.all()
    expenses = Expense.query.all()

    total_expenses = sum(expense.amount for expense in expenses)

    return render_template(
        "index.html",
        people=people,
        expenses=expenses,
        total_expenses=total_expenses
    )


# -------------------------
# Add Person
# -------------------------
@app.route("/add_person", methods=["POST"])
def add_person():

    name = request.form.get("name", "").strip()

    if name:
        existing_person = Person.query.filter_by(name=name).first()

        if not existing_person:
            person = Person(name=name)
            db.session.add(person)
            db.session.commit()

    return redirect(url_for("home"))


# -------------------------
# Create Database Tables
# -------------------------
with app.app_context():
    db.create_all()


# -------------------------
# Run Application
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)