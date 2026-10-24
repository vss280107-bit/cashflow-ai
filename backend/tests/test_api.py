import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def auth_headers(client, email="a@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": "password123", "name": "Test"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_full_flow():
    with TestClient(app) as c:
        assert c.get("/api/forecast").status_code == 401
        h = auth_headers(c)
        assert c.post("/api/auth/login", json={"email": "a@example.com", "password": "bad-password"}).status_code == 401
        assert c.get("/api/forecast", headers=h).status_code == 409  # no data yet

        # manual entry auto-categorises
        r = c.post("/api/transactions", headers=h, json={"date": "2026-01-05", "amount": 250, "type": "expense", "description": "Swiggy dinner"})
        assert r.status_code == 201 and r.json()["category"] == "food"

        # CSV import
        csv = "date,amount,description\n2026-01-06,-120,Uber ride\n06/01/2026,5000,Freelance client\nbad,1,x\n"
        r = c.post("/api/transactions/import", headers=h, files={"file": ("t.csv", csv, "text/csv")})
        assert r.json()["imported"] == 2 and r.json()["error_count"] == 1

        # demo data + forecast
        assert c.post("/api/transactions/demo?replace=true", headers=h).json()["imported"] > 500
        fc = c.get("/api/forecast?horizon=30", headers=h).json()
        assert fc["model"] == "gradient_boosting" and len(fc["daily"]) == 30
        d0 = fc["daily"][0]
        assert d0["balance_low"] <= d0["balance"] <= d0["balance_high"]
        assert "plan" in fc and "suggestions" in fc["plan"]

        # what-if: a huge purchase must worsen the outlook
        day = fc["daily"][3]["date"]
        w = c.post("/api/forecast/what-if", headers=h, json={"horizon": 30, "expenses": [{"date": day, "amount": 90000, "description": "Laptop"}]}).json()
        assert w["end_balance_change"] < -80000 and w["verdict"] == "unsafe"

        ev = c.get("/api/model/evaluation", headers=h).json()
        assert ev["available"] and ev["test"]["origins"] > 0
        assert c.get("/api/summary", headers=h).json()["recurring"]

        # isolation between users
        h2 = auth_headers(c, "b@example.com")
        assert c.get("/api/transactions", headers=h2).json() == []
