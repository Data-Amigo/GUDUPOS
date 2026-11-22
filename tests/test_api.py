"""End-to-end API tests: accounts, PIN login, isolation between businesses, sales, stock,
M-Pesa matching, statement check and weekly analytics."""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", f"sqlite:///{DB}")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from make_demo_statement import build_pdf  # noqa: E402

c = TestClient(app)
S = {}  # shared state between tests


def h(token=None, device=None):
    out = {}
    if token:
        out["Authorization"] = f"Bearer {token}"
    if device:
        out["X-Device"] = device
    return out


def signup(name, phone, email="", pin="1234", password="secret123"):
    r = c.post("/api/auth/signup", json={"business_name": name, "till_number": "5123456", "owner_name": "Owner " + name,
                                         "phone": phone, "email": email, "password": password, "pin": pin})
    assert r.status_code == 200, r.text
    return r.json()


def test_accounts_and_pin_login():
    assert c.post("/api/auth/signup", json={"business_name": "X", "owner_name": "Y", "phone": "12",
                                            "password": "secret123", "pin": "1234"}).status_code == 400
    assert c.post("/api/auth/signup", json={"business_name": "X", "owner_name": "Y", "phone": "0712345678",
                                            "password": "short", "pin": "1234"}).status_code == 400
    a = signup("Gudu Bites", "0712 345 678", "Owner@Gudu.co.ke")
    S["a"] = a
    assert a["business"]["callback_key"]
    # same phone in another format, or same email -> already exists
    assert c.post("/api/auth/signup", json={"business_name": "Z", "owner_name": "Z", "phone": "+254712345678",
                                            "password": "secret123", "pin": "1111"}).status_code == 400
    # sign in with phone (any format) or email
    for ident in ["0712345678", "+254 712 345 678", "owner@gudu.co.ke"]:
        r = c.post("/api/auth/signin", json={"identifier": ident, "password": "secret123"})
        assert r.status_code == 200, (ident, r.text)
    # device -> PIN screen
    dev = a["device_token"]
    assert c.get("/api/login-list").status_code == 401
    names = c.get("/api/login-list", headers=h(device=dev)).json()
    assert [n["name"] for n in names] == ["Owner Gudu Bites"]
    assert c.post("/api/login", json={"staff_id": a["staff"]["id"], "pin": "1234"}, headers=h(device=dev)).status_code == 200
    # lockout after 5 wrong PINs
    for _ in range(5):
        assert c.post("/api/login", json={"staff_id": a["staff"]["id"], "pin": "0000"}, headers=h(device=dev)).status_code == 401
    assert c.post("/api/login", json={"staff_id": a["staff"]["id"], "pin": "1234"}, headers=h(device=dev)).status_code == 429
    # unlock for the rest of the tests
    from app.db import SessionLocal
    from app.models import Staff
    with SessionLocal() as db:
        s = db.get(Staff, a["staff"]["id"])
        s.locked_until = None
        db.commit()


def test_full_flow():
    a = S["a"]
    owner, dev = a["token"], a["device_token"]
    cashier = c.post("/api/staff", json={"name": "Wanjiku", "role": "cashier", "pin": "1111"}, headers=h(owner)).json()
    ctok = c.post("/api/login", json={"staff_id": cashier["id"], "pin": "1111"}, headers=h(device=dev)).json()["token"]
    S["ctok"] = ctok
    assert c.get("/api/staff", headers=h(ctok)).status_code == 403
    assert c.get("/api/stock", headers=h(ctok)).status_code == 403

    soda = c.post("/api/stock", json={"name": "Soda 350ml", "unit": "bottles", "reorder_level": 12, "opening_qty": 24},
                  headers=h(owner)).json()
    c.post(f"/api/stock/{soda['id']}/receive", json={"qty": 24, "total_cost": 1200}, headers=h(owner))
    menu = {m["name"]: m for m in c.get("/api/menu", headers=h(owner)).json()}
    S["menu"] = menu
    m = menu["Soda 350ml"]
    assert c.put(f"/api/menu/{m['id']}", json={**m, "choice_options": "", "stock_item_id": soda["id"], "stock_qty": 1},
                 headers=h(owner)).status_code == 200

    beef = menu["Beef Wet Fry"]
    lines = [{"menu_item_id": menu["Chips Masala"]["id"], "qty": 1},
             {"menu_item_id": beef["id"], "qty": 1, "choice": "Ugali"}, {"menu_item_id": m["id"], "qty": 1}]
    S["lines"] = lines
    assert c.post("/api/sales", json={"lines": [{"menu_item_id": beef["id"], "qty": 1}], "payment_method": "cash"},
                  headers=h(ctok)).status_code == 400
    s1 = c.post("/api/sales", json={"lines": lines, "payment_method": "cash", "cash_tendered": 1000}, headers=h(ctok)).json()
    assert s1["total"] == 670 and s1["status"] == "paid" and s1["change"] == 330 and s1["number"] == "#00001"
    s2 = c.post("/api/sales", json={"lines": lines, "payment_method": "mpesa"}, headers=h(ctok)).json()
    assert s2["status"] == "awaiting_payment"
    p = c.post("/api/mpesa/simulate", json={"amount": 670}, headers=h(ctok)).json()
    assert p["sale_id"] == s2["id"] and len(p["trans_id"]) == 10
    s3 = c.post("/api/sales", json={"lines": lines[:1], "payment_method": "mpesa"}, headers=h(ctok)).json()
    s4 = c.post("/api/sales", json={"lines": lines[:1], "payment_method": "mpesa"}, headers=h(ctok)).json()
    p2 = c.post("/api/mpesa/simulate", json={"amount": 250}, headers=h(ctok)).json()
    assert p2["sale_id"] is None
    assert c.post(f"/api/mpesa/payments/{p2['id']}/match", json={"sale_id": s3["id"]}, headers=h(ctok)).status_code == 200

    key = a["business"]["callback_key"]
    cb = {"TransactionType": "Buy Goods", "TransID": "TKL1ABC234", "TransTime": "20261121120000",
          "TransAmount": "250.00", "BusinessShortCode": "123456", "MSISDN": "2547 ***** 126", "FirstName": "JOHN"}
    assert c.post("/api/mpesa/c2b/confirmation/wrong", json=cb).status_code == 404
    for _ in range(2):
        assert c.post(f"/api/mpesa/c2b/confirmation/{key}", json=cb).json()["ResultCode"] == 0
    assert c.get(f"/api/sales/{s4['id']}", headers=h(owner)).json()["status"] == "paid"

    c.post(f"/api/sales/{s1['id']}/void", json={"reason": "Wrong order"}, headers=h(owner))
    stock = {x["name"]: x for x in c.get("/api/stock", headers=h(owner)).json()}
    assert stock["Soda 350ml"]["quantity"] == 47
    d = c.get("/api/dashboard", headers=h(owner)).json()
    assert d["total_sales"] == 1170 and d["voided"] == 1 and d["mpesa_paid"] == 1170


def test_businesses_are_isolated():
    a = S["a"]
    b = signup("Mama Oliech", "0722000111", pin="2222")
    bt, bdev = b["token"], b["device_token"]
    # B's PIN screen only lists B's staff, and A's staff can't log in on B's phone
    assert [n["name"] for n in c.get("/api/login-list", headers=h(device=bdev)).json()] == ["Owner Mama Oliech"]
    assert c.post("/api/login", json={"staff_id": a["staff"]["id"], "pin": "1234"}, headers=h(device=bdev)).status_code == 401
    # B sees none of A's data
    assert c.get("/api/sales", headers=h(bt)).json() == []
    assert c.get("/api/stock", headers=h(bt)).json() == []
    assert c.get("/api/mpesa/payments", headers=h(bt)).json() == []
    a_sales = c.get("/api/sales", headers=h(a["token"])).json()
    assert c.get(f"/api/sales/{a_sales[0]['id']}", headers=h(bt)).status_code == 404
    a_item = S["menu"]["Chips Masala"]["id"]
    assert c.post("/api/sales", json={"lines": [{"menu_item_id": a_item, "qty": 1}], "payment_method": "cash"},
                  headers=h(bt)).status_code == 400
    assert c.put(f"/api/menu/{a_item}", json={"category_id": 1, "name": "Hacked", "price": 1}, headers=h(bt)).status_code == 404
    # receipt numbers start at 1 per business
    bmenu = c.get("/api/menu", headers=h(bt)).json()
    s = c.post("/api/sales", json={"lines": [{"menu_item_id": bmenu[0]["id"], "qty": 1}], "payment_method": "cash"},
               headers=h(bt)).json()
    assert s["number"] == "#00001"
    # the same M-Pesa receipt can exist in both businesses without clashing
    cb = {"TransID": "TKL1ABC234", "TransAmount": "100", "MSISDN": "x", "FirstName": "Y"}
    assert c.post(f"/api/mpesa/c2b/confirmation/{b['business']['callback_key']}", json=cb).status_code == 200
    assert len(c.get("/api/mpesa/payments", headers=h(bt)).json()) == 1


def test_statement_reconciliation():
    a = S["a"]
    owner, menu = a["token"], S["menu"]
    s5 = c.post("/api/sales", json={"lines": [{"menu_item_id": menu["Chips Plain"]["id"], "qty": 1}],
                                    "payment_method": "mpesa"}, headers=h(owner)).json()
    s6 = c.post("/api/sales", json={"lines": [{"menu_item_id": menu["Samosa"]["id"], "qty": 1}],
                                    "payment_method": "mpesa"}, headers=h(owner)).json()
    now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)
    rows = [
        {"receipt": "TKL1ABC234", "time": now - timedelta(minutes=5), "details": "Merchant Payment from 2547***126 - JOHN", "paid_in": 250},
        {"receipt": "TKL1ABC500", "time": now + timedelta(minutes=1), "details": "Merchant Payment from 2547***318 - MARY WANJIRU", "paid_in": 150},
        {"receipt": "TKL1ABC777", "time": now - timedelta(minutes=50), "details": "Merchant Payment from 2547***902 - PAUL OTIENO", "paid_in": 300},
        {"receipt": "TKL1ABC888", "time": now - timedelta(minutes=20), "details": "Business Withdrawal", "withdrawn": 2000},
        {"receipt": "TKL1ABC888", "time": now - timedelta(minutes=20), "details": "Withdrawal Charge", "withdrawn": 30},
        {"receipt": "TKL1ABC999", "time": now - timedelta(minutes=10), "details": "Merchant Payment - X", "paid_in": 999, "status": "Failed"},
    ]
    pdf = DB.parent / "stmt.pdf"
    build_pdf(rows, str(pdf), "4321")

    def up(pw, data=None):
        return c.post("/api/mpesa/statements", headers=h(owner),
                      files={"file": ("stmt.pdf", data or pdf.read_bytes(), "application/pdf")}, data={"password": pw})

    assert up("0000").status_code == 400
    assert up("4321", b"not a pdf").status_code == 400
    r = up("4321")
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["incoming_count"] == 3 and rep["new_count"] == 2 and rep["already_known"] == 1
    assert rep["statement_total"] == 700
    assert {p["trans_id"] for p in rep["matched"]} == {"TKL1ABC234", "TKL1ABC500"}
    assert [p["trans_id"] for p in rep["unrecorded"]] == ["TKL1ABC777"]
    missing = {s["id"] for s in rep["missing"]}
    assert s6["id"] in missing and s5["id"] not in missing
    assert rep["pos_mpesa_total"] == 670 + 250 + 250 + 150 + 50
    assert up("4321").json()["new_count"] == 0
    # another business cannot open this report
    other = c.post("/api/auth/signin", json={"identifier": "0722000111", "password": "secret123"}).json()["token"]
    assert c.get(f"/api/mpesa/statements/{rep['id']}", headers=h(other)).status_code == 404


def test_weekly_analytics():
    owner = S["a"]["token"]
    d = c.get("/api/mpesa/analytics", headers=h(owner)).json()
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).date()
    assert d["week_start"] == (today - timedelta(days=today.weekday())).isoformat()
    # this week: 670 + 250 (sim) + 250 (callback) + 150 + 300 (statement) = 1620, 5 payments
    assert d["total"] == 1620 and d["count"] == 5 and d["largest"] == 670
    assert sum(x["total"] for x in d["by_day"]) == 1620 and len(d["by_day"]) == 7
    assert d["matched_total"] == 1620 - 300 and d["unmatched_count"] == 1
    assert d["top_payers"][0]["total"] >= d["top_payers"][-1]["total"]
    assert d["sources"] == {"statement": 2, "callback": 1, "simulated": 2}
    prev = c.get(f"/api/mpesa/analytics?week={(today - timedelta(days=7)).isoformat()}", headers=h(owner)).json()
    assert prev["total"] == 0 and prev["latest_week"] == d["week_start"]
    assert c.get("/api/mpesa/analytics", headers=h(S["ctok"])).status_code == 403
