import os
import json
os.environ["DATABASE_URL"] = "sqlite:///./cashflow_test.db"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.security import verify_password  # noqa: E402
from app.models import Transaction, User  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.routers import auth as auth_routes  # noqa: E402
from app.schemas import LoginIn, RegisterIn  # noqa: E402
from app.deps import get_current_user  # noqa: E402
from app.routers import transactions as transaction_routes  # noqa: E402
from app.routers.analysis import get_forecast, summary  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
import app.database as database_module  # noqa: E402
import uuid  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from app.routers import budget as budget_routes  # noqa: E402
from app.schemas import BudgetIn  # noqa: E402


def register(client, email):
    response = client.post("/api/auth/register", json={"email": email, "password": "password123", "name": "Student"})
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_routes_register_duplicate_login_and_me():
    Base.metadata.create_all(bind=engine)
    database_module.migrate_user_financial_columns()
    db = SessionLocal()
    email = f"auth-{uuid.uuid4().hex}@example.com"
    legacy_email = f"Legacy-{uuid.uuid4().hex}@example.com"
    try:
        legacy_user = User(email=legacy_email, name="Legacy", hashed_password=auth_routes.hash_password("legacy-pass-123"))
        db.add(legacy_user)
        db.commit()
        assert auth_routes.login(LoginIn(email=legacy_email.lower(), password="legacy-pass-123"), db)
        try:
            auth_routes.register(RegisterIn(email=legacy_email.lower(), password="legacy-pass-123", name="Again"), db)
            raise AssertionError("case-insensitive duplicate registration should fail")
        except HTTPException as exc:
            assert exc.status_code == 409

        registered = auth_routes.register(
            RegisterIn(email=email, password="secure-pass-123", name="Auth Test"), db
        )
        user = db.query(User).filter_by(email=email).one()
        assert user.hashed_password != "secure-pass-123"
        assert verify_password("secure-pass-123", user.hashed_password)
        assert user.opening_balance == 0.0
        assert user.low_balance_threshold == 2000.0

        try:
            auth_routes.register(RegisterIn(email=email, password="secure-pass-123", name="Again"), db)
            raise AssertionError("duplicate registration should fail")
        except HTTPException as exc:
            assert exc.status_code == 409
            assert "already exists" in exc.detail

        try:
            auth_routes.login(LoginIn(email=email, password="wrong-password"), db)
            raise AssertionError("invalid credentials should fail")
        except HTTPException as exc:
            assert exc.status_code == 401
            assert exc.detail == "Incorrect email or password"

        logged_in = auth_routes.login(LoginIn(email=email, password="secure-pass-123"), db)
        authenticated = get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=logged_in.access_token), db
        )
        assert auth_routes.me(authenticated).email == email

        try:
            get_current_user(None, db)
            raise AssertionError("unauthenticated profile requests should fail")
        except HTTPException as exc:
            assert exc.status_code == 401
    finally:
        db.rollback()
        db.close()


def test_user_financial_column_migration_preserves_existing_account(monkeypatch):
    legacy_engine = create_engine("sqlite:///:memory:")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL, "
            "name TEXT NOT NULL, hashed_password TEXT NOT NULL, created_at DATETIME NOT NULL)"
        )
        connection.execute(
            text("INSERT INTO users (id, email, name, hashed_password, created_at) "
                 "VALUES (1, 'kept@example.com', 'Kept', 'existing-hash', '2026-01-01')")
        )
    monkeypatch.setattr(database_module, "engine", legacy_engine)
    database_module.migrate_user_financial_columns()
    with legacy_engine.connect() as connection:
        account = connection.execute(
        text("SELECT email, opening_balance, low_balance_threshold, monthly_budget FROM users WHERE id = 1")
        ).one()
    assert tuple(account) == ("kept@example.com", 0.0, 2000.0, 0.0)
    legacy_engine.dispose()


def test_transaction_recurring_migration_preserves_existing_rows(monkeypatch):
    legacy_engine = create_engine("sqlite:///:memory:")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE transactions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
            "date DATE NOT NULL, amount FLOAT NOT NULL, type VARCHAR(10) NOT NULL, "
            "category VARCHAR(40) NOT NULL, description TEXT NOT NULL, created_at DATETIME NOT NULL)"
        )
        connection.execute(
            text("INSERT INTO transactions (id, user_id, date, amount, type, category, description, created_at) "
                 "VALUES (1, 7, '2026-01-01', 42.0, 'expense', 'food', '', '2026-01-01')")
        )
    monkeypatch.setattr(database_module, "engine", legacy_engine)
    database_module.migrate_transaction_recurring_column()
    with legacy_engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, amount, is_recurring FROM transactions WHERE id = 1")
        ).one()
    assert tuple(row) == (1, 42.0, 0)
    legacy_engine.dispose()


def test_demo_and_dashboard_work_with_legacy_not_null_recurring_schema():
    legacy_engine = create_engine("sqlite:///:memory:")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE, "
            "name VARCHAR(120) NOT NULL, hashed_password VARCHAR(255) NOT NULL, "
            "opening_balance FLOAT NOT NULL, low_balance_threshold FLOAT NOT NULL, "
            "monthly_budget FLOAT NOT NULL DEFAULT 0.0, created_at DATETIME NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE transactions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
            "date DATE NOT NULL, amount FLOAT NOT NULL, type VARCHAR(10) NOT NULL, "
            "category VARCHAR(40) NOT NULL, description TEXT NOT NULL, "
            "is_recurring BOOLEAN NOT NULL, created_at DATETIME NOT NULL)"
        )
    db = sessionmaker(bind=legacy_engine, autoflush=False, autocommit=False)()
    email = f"legacy-demo-{uuid.uuid4().hex}@example.com"
    try:
        auth_routes.register(RegisterIn(email=email, password="secure-pass-123", name="Legacy Demo"), db)
        user = db.query(User).filter_by(email=email).one()
        result = transaction_routes.load_demo(replace=False, user=user, db=db)
        rows = db.query(Transaction).filter_by(user_id=user.id).all()
        assert result["imported"] == len(rows) and rows
        assert all(row.is_recurring is False for row in rows)
        assert get_forecast(user, db)["available"] is True
        assert summary(user, db)["monthly"]
    finally:
        db.close()
        legacy_engine.dispose()


def test_dashboard_loads_after_csv_import_and_skips_nonfinite_amounts():
    Base.metadata.create_all(bind=engine)
    database_module.migrate_user_financial_columns()
    database_module.migrate_transaction_recurring_column()
    db = SessionLocal()
    email = f"dashboard-{uuid.uuid4().hex}@example.com"
    try:
        auth_routes.register(RegisterIn(email=email, password="secure-pass-123", name="Dashboard"), db)
        user = db.query(User).filter_by(email=email).one()
        csv = (
            "date,amount,type,category,description\n"
            "2026-01-05,100,expense,food,January spending\n"
            "2026-01-10,1000,income,salary,January income\n"
            "2026-02-05,120,expense,food,February spending\n"
            "2026-02-10,1000,income,salary,February income\n"
            "2026-03-05,140,expense,food,March spending\n"
            "2026-03-10,1000,income,salary,March income\n"
            "2026-04-05,160,expense,food,April spending\n"
            "2026-04-10,1000,income,salary,April income\n"
            "2026-04-20,NaN,expense,other,Invalid amount\n"
            "2026-04-21,Infinity,expense,other,Invalid amount\n"
        )
        imported = transaction_routes._import_csv_text(csv, user, db)
        assert imported["imported"] == 8
        assert imported["error_count"] == 2
        imported_rows = db.query(Transaction).filter_by(user_id=user.id).all()
        assert len(imported_rows) == 8
        assert all(row.is_recurring is False for row in imported_rows)

        forecast = get_forecast(user, db)
        dashboard_summary = summary(user, db)
        assert forecast["available"] is True
        assert len(dashboard_summary["monthly"]) == 4
        assert dashboard_summary["monthly"][-1]["expense"] == 160.0
        json.dumps(forecast, allow_nan=False)
        json.dumps(dashboard_summary, allow_nan=False)
    finally:
        db.rollback()
        db.close()


def test_auth_transaction_isolation_and_csv_import():
    with TestClient(app) as client:
        h1 = register(client, "one@example.com")
        h2 = register(client, "two@example.com")
        assert client.get("/api/auth/me", headers=h1).status_code == 200
        assert client.post("/api/auth/login", json={"email": "one@example.com", "password": "wrong-password"}).status_code == 401
        assert client.post("/api/transactions", headers=h1, json={"date": "2026-01-05", "amount": 250, "type": "expense", "description": "Swiggy dinner"}).json()["category"] == "food"
        csv = "date,amount,type,description\n2026-01-06,120,expense,Bus\n06/01/2026,5000,income,Stipend\nbad,1,expense,Invalid\n"
        imported = client.post("/api/transactions/import", headers=h1, files={"file": ("history.csv", csv, "text/csv")})
        assert imported.status_code == 200
        assert imported.json()["imported"] == 2 and imported.json()["error_count"] == 1
        assert len(client.get("/api/transactions", headers=h1).json()) == 3
        assert client.get("/api/transactions", headers=h2).json() == []
        transaction_id = client.get("/api/transactions", headers=h1).json()[0]["id"]
        assert client.delete(f"/api/transactions/{transaction_id}", headers=h2).status_code == 404
        assert client.put(f"/api/transactions/{transaction_id}", headers=h2, json={"date": "2026-01-05", "amount": 2, "type": "expense"}).status_code == 404


def test_password_is_hashed():
    with TestClient(app) as client:
        register(client, "hash@example.com")
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email="hash@example.com").one()
            assert user.hashed_password != "password123"
            assert verify_password("password123", user.hashed_password)
        finally:
            db.close()


def test_demo_data_forecast_and_insufficient_history():
    with TestClient(app) as client:
        headers = register(client, "forecast@example.com")
        empty = client.get("/api/forecast", headers=headers).json()
        assert empty["available"] is False and empty["predicted_expenses"] is None
        demo = client.post("/api/transactions/demo?replace=false", headers=headers)
        assert demo.status_code == 200, demo.text
        assert demo.json()["imported"] > 0
        assert client.get("/api/transactions", headers=headers).json()
        forecast = client.get("/api/forecast", headers=headers).json()
        assert forecast["available"] is True
        assert forecast["model"] == "Random Forest regression"
        assert forecast["predicted_expenses"] >= 0
        assert forecast["mae"] is not None
        assert forecast["evaluation"]
        summary = client.get("/api/summary", headers=headers).json()
        assert summary["monthly"] and summary["categories"]


def test_demo_transactions_default_recurring_and_dashboard_results():
    Base.metadata.create_all(bind=engine)
    database_module.migrate_user_financial_columns()
    database_module.migrate_transaction_recurring_column()
    db = SessionLocal()
    email = f"demo-{uuid.uuid4().hex}@example.com"
    try:
        auth_routes.register(RegisterIn(email=email, password="secure-pass-123", name="Demo Test"), db)
        user = db.query(User).filter_by(email=email).one()
        result = transaction_routes.load_demo(replace=False, user=user, db=db)
        assert result["imported"] > 0
        rows = db.query(Transaction).filter_by(user_id=user.id).all()
        assert len(rows) == result["imported"]
        assert all(row.is_recurring is False for row in rows)

        forecast = get_forecast(user, db)
        dashboard_summary = summary(user, db)
        assert forecast["available"] is True
        assert dashboard_summary["monthly"]
        json.dumps(forecast, allow_nan=False)
        json.dumps(dashboard_summary, allow_nan=False)
    finally:
        db.rollback()
        db.close()


def test_budget_calculation_thresholds_and_user_isolation():
    Base.metadata.create_all(bind=engine)
    database_module.migrate_user_financial_columns()
    database_module.migrate_transaction_recurring_column()
    db = SessionLocal()
    today = date.today()
    prior_month = today.replace(day=1) - timedelta(days=1)
    emails = [f"budget-{uuid.uuid4().hex}@example.com" for _ in range(2)]
    try:
        for email in emails:
            auth_routes.register(RegisterIn(email=email, password="secure-pass-123", name="Budget"), db)
        first, second = [db.query(User).filter_by(email=email).one() for email in emails]
        db.add_all([
            Transaction(user_id=first.id, date=today, amount=800, type="expense", category="food", description=""),
            Transaction(user_id=first.id, date=today, amount=2500, type="income", category="salary", description=""),
            Transaction(user_id=first.id, date=prior_month, amount=900, type="expense", category="food", description=""),
            Transaction(user_id=second.id, date=today, amount=500, type="expense", category="food", description=""),
        ])
        db.commit()

        selected_month = today.strftime("%Y-%m")
        first_state = budget_routes.set_budget(BudgetIn(amount=1000, month=selected_month), first, db)
        assert first_state["amount_spent"] == 800
        assert first_state["remaining_balance"] == 200
        assert first_state["percentage_used"] == 80
        assert first_state["status"] == "warning"
        assert budget_routes.calculate_budget_state(1000, 799.99, selected_month)["status"] == "on_track"
        assert budget_routes.calculate_budget_state(1000, 800, selected_month)["status"] == "warning"
        assert budget_routes.calculate_budget_state(1000, 999.99, selected_month)["status"] == "warning"
        assert budget_routes.calculate_budget_state(1000, 1000, selected_month)["status"] == "exceeded"
        assert budget_routes.calculate_budget_state(0, 40, selected_month)["percentage_used"] is None
        assert budget_routes.calculate_budget_state(float("nan"), 40, selected_month)["status"] == "not_set"

        second_state = budget_routes.get_budget(selected_month, second, db)
        assert second_state["budget_amount"] is None
        assert second_state["amount_spent"] == 500
        assert second_state["status"] == "not_set"
        first_again = budget_routes.get_budget(selected_month, first, db)
        assert first_again["budget_amount"] == 1000
        assert first_again["amount_spent"] == 800

        previous_month = prior_month.strftime("%Y-%m")
        previous_state = budget_routes.set_budget(BudgetIn(amount=500, month=previous_month), first, db)
        assert previous_state["amount_spent"] == 900
        assert previous_state["remaining_balance"] == -400
        assert previous_state["percentage_used"] == 180
        assert previous_state["status"] == "exceeded"
        assert budget_routes.get_budget(previous_month, first, db)["budget_amount"] == 500
    finally:
        db.rollback()
        db.close()
