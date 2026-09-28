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
    payments = db.relationship(
        "ExpensePayment",
        primaryjoin="Expense.id == foreign(ExpensePayment.expense_id)",
        lazy=True
    )


# -------------------------
# Expense Payment Table
# Stores who paid how much
# -------------------------
class ExpensePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, nullable=False)
    person_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)


# -------------------------
# Expense Participant Table
# Stores each person's share
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

    total_expenses = sum(
        expense.amount for expense in expenses
    )

    # -------------------------
    # Calculate balances
    # -------------------------
    balances = {}

    for person in people:
        balances[person.name] = {
            "paid": 0.0,
            "share": 0.0,
            "balance": 0.0
        }

    # Calculate payments
    payments = ExpensePayment.query.all()

    for payment in payments:

        if payment.person_name in balances:
            balances[payment.person_name]["paid"] += payment.amount

    # Calculate shares
    participants = ExpenseParticipant.query.all()

    for participant in participants:

        if participant.person_name in balances:
            balances[participant.person_name]["share"] += participant.share

    # Final balance
    for person_name in balances:

        balances[person_name]["balance"] = round(
            balances[person_name]["paid"]
            - balances[person_name]["share"],
            2
        )

    # -------------------------
    # Calculate settlements
    # -------------------------
    creditors = []
    debtors = []

    for person_name, data in balances.items():

        balance = round(data["balance"], 2)

        if balance > 0.01:

            creditors.append({
                "name": person_name,
                "amount": balance
            })

        elif balance < -0.01:

            debtors.append({
                "name": person_name,
                "amount": abs(balance)
            })

    settlements = []

    creditor_index = 0
    debtor_index = 0

    while (
        creditor_index < len(creditors)
        and debtor_index < len(debtors)
    ):

        creditor = creditors[creditor_index]
        debtor = debtors[debtor_index]

        amount = min(
            creditor["amount"],
            debtor["amount"]
        )

        settlements.append({
            "from": debtor["name"],
            "to": creditor["name"],
            "amount": round(amount, 2)
        })

        creditor["amount"] = round(
            creditor["amount"] - amount,
            2
        )

        debtor["amount"] = round(
            debtor["amount"] - amount,
            2
        )

        if creditor["amount"] <= 0.01:
            creditor_index += 1

        if debtor["amount"] <= 0.01:
            debtor_index += 1

    return render_template(
        "index.html",
        people=people,
        expenses=expenses,
        total_expenses=total_expenses,
        balances=balances,
        settlements=settlements
    )


# -------------------------
# Add Person
# -------------------------
@app.route("/add_person", methods=["POST"])
def add_person():

    name = request.form.get(
        "name",
        ""
    ).strip()

    if name:

        existing_person = Person.query.filter_by(
            name=name
        ).first()

        if not existing_person:

            person = Person(name=name)

            db.session.add(person)
            db.session.commit()

    return redirect(url_for("home"))


# -------------------------
# Add Expense
# -------------------------
@app.route("/add_expense", methods=["POST"])
def add_expense():

    description = request.form.get(
        "description",
        ""
    ).strip()

    amount = request.form.get(
        "amount",
        type=float
    )

    participants = request.form.getlist(
        "participants"
    )

    # Get selected payer names
    payer_names = request.form.getlist(
        "payer_names"
    )

    # Get amounts paid by each payer
    payer_amounts = request.form.getlist(
        "payer_amounts"
    )

    if (
        description
        and amount
        and amount > 0
        and participants
        and payer_names
    ):

        # Convert payer amounts
        payments = []

        for name, paid_amount in zip(
            payer_names,
            payer_amounts
        ):

            try:
                paid_amount = float(paid_amount)
            except (TypeError, ValueError):
                continue

            if paid_amount > 0:

                payments.append({
                    "name": name,
                    "amount": paid_amount
                })

        total_paid = sum(
            payment["amount"]
            for payment in payments
        )

        # Allow small decimal rounding difference
        if (
            payments
            and abs(total_paid - amount) <= 0.01
        ):

            expense = Expense(
                description=description,
                amount=amount
            )

            db.session.add(expense)
            db.session.commit()

            # Save payments
            for payment in payments:

                expense_payment = ExpensePayment(
                    expense_id=expense.id,
                    person_name=payment["name"],
                    amount=payment["amount"]
                )

                db.session.add(expense_payment)

            # Equal split
            share = amount / len(participants)

            for person_name in participants:

                participant = ExpenseParticipant(
                    expense_id=expense.id,
                    person_name=person_name,
                    share=share
                )

                db.session.add(participant)

            db.session.commit()

    return redirect(url_for("home"))


# -------------------------
# Reset All Data
# -------------------------
@app.route("/reset_data", methods=["POST"])
def reset_data():

    ExpensePayment.query.delete()
    ExpenseParticipant.query.delete()
    Expense.query.delete()
    Person.query.delete()

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