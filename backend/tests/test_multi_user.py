import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, init_db, engine
from models.user import User
from models.trade import Trade
from models.trade import TradeMode, TradeStatus

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    # Re-init db tables
    init_db()
    db = SessionLocal()
    # Clean up tables
    db.query(Trade).delete()
    db.query(User).delete()
    db.commit()
    db.close()
    yield


def test_auth_and_user_isolation():
    # 1. Register User 1
    res1 = client.post("/api/v1/auth/register", json={
        "username": "userone",
        "password": "password123"
    })
    assert res1.status_code == 201
    user1_data = res1.json()
    assert user1_data["username"] == "userone"

    # 2. Register User 2
    res2 = client.post("/api/v1/auth/register", json={
        "username": "usertwo",
        "password": "password456"
    })
    assert res2.status_code == 201

    # 3. Login User 1
    login_res1 = client.post("/api/v1/auth/login", json={
        "username": "userone",
        "password": "password123"
    })
    assert login_res1.status_code == 200
    token1 = login_res1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # 4. Login User 2
    login_res2 = client.post("/api/v1/auth/login", json={
        "username": "usertwo",
        "password": "password456"
    })
    assert login_res2.status_code == 200
    token2 = login_res2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 5. Check User 1 profile
    me_res = client.get("/api/v1/auth/me", headers=headers1)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "userone"

    # 6. Update User 1 settings
    update_res = client.put("/api/v1/settings", json={
        "trading_mode": "forward",
        "capital": 250000.0,
        "risk_pct": 1.5,
        "max_sl_pct": 10.0,
        "min_quality": 80
    }, headers=headers1)
    assert update_res.status_code == 200

    # 7. Check User 1 settings updated, User 2 settings untouched
    s1 = client.get("/api/v1/settings", headers=headers1).json()
    s2 = client.get("/api/v1/settings", headers=headers2).json()
    
    assert s1["trading_mode"] == "forward"
    assert s1["capital"] == 250000.0
    assert s1["risk_pct"] == 1.5
    
    assert s2["trading_mode"] == "paper"  # default
    assert s2["capital"] == 200000.0       # default

    # 8. Open trade for User 1
    trade_res = client.post("/api/v1/trades", json={
        "symbol": "RELIANCE.NS",
        "strategy": "VCP",
        "entry_price": 2500.0,
        "stop_loss": 2400.0,
        "target": 2800.0,
        "quantity": 10,
        "capital_deployed": 25000.0
    }, headers=headers1)
    assert trade_res.status_code == 201
    
    # 9. List trades for User 1 (should see 1 trade) and User 2 (should see 0 trades)
    t1 = client.get("/api/v1/trades", headers=headers1).json()
    t2 = client.get("/api/v1/trades", headers=headers2).json()

    assert len(t1) == 1
    assert t1[0]["symbol"] == "RELIANCE.NS"
    assert len(t2) == 0
