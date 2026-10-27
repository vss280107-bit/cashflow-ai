from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def migrate_user_financial_columns():
    """Add older users-table financial defaults without changing existing account data."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    migrations = {
        "opening_balance": "FLOAT NOT NULL DEFAULT 0.0",
        "low_balance_threshold": "FLOAT NOT NULL DEFAULT 2000.0",
        "monthly_budget": "FLOAT NOT NULL DEFAULT 0.0",
    }
    missing = [(name, declaration) for name, declaration in migrations.items() if name not in columns]
    if missing:
        with engine.begin() as connection:
            for name, declaration in missing:
                connection.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {name} {declaration}")


def migrate_transaction_recurring_column():
    """Add the non-null recurrence flag to older transaction tables without rewriting rows."""
    inspector = inspect(engine)
    if "transactions" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "is_recurring" in columns:
        return
    default = "0" if engine.dialect.name == "sqlite" else "FALSE"
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"ALTER TABLE transactions ADD COLUMN is_recurring BOOLEAN NOT NULL DEFAULT {default}"
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
