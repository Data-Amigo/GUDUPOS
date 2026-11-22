"""Gudu Bites POS & Stock — API + web app (multi-business)."""
import hashlib
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .db import ON_VERCEL, get_db, prepare_database
from .models import (AuthToken, Business, Category, Device, MenuItem, MpesaPayment, Sale, SaleLine, Staff,
                     StatementImport, StockItem, StockMovement, utcnow)
from .seed import load_starter_menu
from .statement import StatementError, incoming_payments, payer_from_details, read_statement

NAIROBI = timedelta(hours=3)  # Kenya has no daylight saving: fixed UTC+3
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
ROLES = ("owner", "cashier", "storekeeper")
MATCH_PAYMENT_BEFORE_SALE = timedelta(minutes=15)
MATCH_SALE_BEFORE_PAYMENT = timedelta(minutes=60)
MAX_TRIES, LOCK_FOR = 5, timedelta(minutes=5)
# Vercel functions accept request bodies up to 4.5 MB.
MAX_STATEMENT_BYTES = (4 if ON_VERCEL else 15) * 1024 * 1024

prepare_database()
app = FastAPI(title="Gudu Bites POS")


# ---------------------------------------------------------------- helpers

def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def _hash(secret: str, rounds: int) -> str:
    salt = secrets.token_hex(8)
    return f"{rounds}${salt}${hashlib.pbkdf2_hmac('sha256', secret.encode(), salt.encode(), rounds).hex()}"


def _verify(secret: str, stored: str | None) -> bool:
    if not stored:
        return False
    rounds, salt, digest = stored.split("$", 2)
    check = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), int(rounds)).hex()
    return secrets.compare_digest(check, digest)


def hash_pin(pin: str) -> str:
    return _hash(pin, 120_000)


def hash_password(pw: str) -> str:
    return _hash(pw, 240_000)


def check_pin(pin: str) -> None:
    if not (pin.isdigit() and len(pin) == 4):
        raise HTTPException(400, "PIN must be exactly 4 digits")


def check_password(pw: str) -> None:
    if len(pw) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")


def norm_phone(raw: str) -> str:
    """Kenyan mobile numbers in any common form -> 2547XXXXXXXX / 2541XXXXXXXX."""
    d = re.sub(r"\D", "", raw or "")
    if d.startswith("254") and len(d) == 12:
        return d
    if d.startswith("0") and len(d) == 10:
        return "254" + d[1:]
    if len(d) == 9 and d[0] in "17":
        return "254" + d
    raise HTTPException(400, "Enter a Kenyan phone number, e.g. 0712 345 678")


def norm_email(raw: str) -> str | None:
    e = (raw or "").strip().lower()
    if not e:
        return None
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e):
        raise HTTPException(400, "That email address doesn't look right")
    return e


def guard_lock(s: Staff) -> None:
    if s.locked_until and s.locked_until > utcnow():
        mins = max(1, int((s.locked_until - utcnow()).total_seconds() // 60) + 1)
        raise HTTPException(429, f"Too many wrong tries. Try again in {mins} minute{'s' if mins > 1 else ''}.")


def record_failure(db: Session, s: Staff) -> None:
    s.failed_attempts += 1
    if s.failed_attempts >= MAX_TRIES:
        s.failed_attempts, s.locked_until = 0, utcnow() + LOCK_FOR
    db.commit()


def day_bounds(day: str | None) -> tuple[datetime, datetime, str]:
    """UTC start/end of a Nairobi calendar day."""
    d = date.fromisoformat(day) if day else (utcnow() + NAIROBI).date()
    start = datetime(d.year, d.month, d.day) - NAIROBI
    return start, start + timedelta(days=1), d.isoformat()


def own(db: Session, model, obj_id: int, staff: Staff):
    """Fetch a row that belongs to the staff member's business, or 404."""
    obj = db.get(model, obj_id)
    if not obj or obj.business_id != staff.business_id:
        raise HTTPException(404, "Not found")
    return obj


def staff_out(s: Staff) -> dict:
    return {"id": s.id, "name": s.name, "phone": s.phone, "email": s.email, "role": s.role, "active": s.active,
            "has_password": bool(s.password_hash)}


def business_out(b: Business, with_key: bool = False) -> dict:
    out = {"name": b.name, "till_number": b.till_number}
    if with_key:
        out["callback_key"] = b.callback_key
    return out


def stock_out(s: StockItem) -> dict:
    return {"id": s.id, "name": s.name, "unit": s.unit, "kind": s.kind, "quantity": round(s.quantity, 3),
            "reorder_level": s.reorder_level, "last_unit_cost": round(s.last_unit_cost, 2),
            "active": s.active, "low": s.quantity <= s.reorder_level}


def menu_out(m: MenuItem) -> dict:
    return {"id": m.id, "category_id": m.category_id, "name": m.name, "price": m.price,
            "choice_label": m.choice_label,
            "choice_options": [o.strip() for o in m.choice_options.split(",") if o.strip()],
            "stock_item_id": m.stock_item_id, "stock_qty": m.stock_qty,
            "stock_name": m.stock_item.name if m.stock_item else None,
            "stock_unit": m.stock_item.unit if m.stock_item else None,
            "active": m.active, "sort": m.sort}


def payment_out(p: MpesaPayment) -> dict:
    return {"id": p.id, "trans_id": p.trans_id, "amount": p.amount, "msisdn": p.msisdn,
            "payer_name": p.payer_name, "received_at": iso(p.received_at), "sale_id": p.sale_id,
            "sale_number": f"#{p.sale.number:05d}" if p.sale else None,
            "matched_by": p.matched_by, "source": p.source, "simulated": p.source == "simulated"}


def sale_out(s: Sale, with_lines: bool = True) -> dict:
    out = {"id": s.id, "number": f"#{s.number:05d}", "total": s.total, "payment_method": s.payment_method,
           "status": s.status, "cash_tendered": s.cash_tendered,
           "change": max(0, s.cash_tendered - s.total) if s.payment_method == "cash" else 0,
           "staff_name": s.staff.name, "staff_id": s.staff_id,
           "created_at": iso(s.created_at), "paid_at": iso(s.paid_at), "void_reason": s.void_reason,
           "item_count": sum(l.qty for l in s.lines),
           "payment": payment_out(s.payment) if s.payment else None}
    if with_lines:
        out["lines"] = [{"name": l.name, "choice": l.choice, "qty": l.qty, "unit_price": l.unit_price,
                         "line_total": l.line_total} for l in s.lines]
    return out


def move_stock(db: Session, item: StockItem, change: float, reason: str, staff_id: int | None,
               sale_id: int | None = None, total_cost: int = 0, supplier: str = "", note: str = "") -> None:
    item.quantity = round(item.quantity + change, 3)
    db.add(StockMovement(business_id=item.business_id, stock_item_id=item.id, change=change, reason=reason,
                         balance_after=item.quantity, total_cost=total_cost, supplier=supplier, note=note,
                         sale_id=sale_id, staff_id=staff_id))


def link_payment(sale: Sale, payment: MpesaPayment, how: str) -> None:
    payment.sale_id = sale.id
    payment.matched_by = how
    sale.status = "paid"
    sale.paid_at = utcnow()


def try_match_payment(db: Session, payment: MpesaPayment) -> None:
    """A till payment arrived: match it if exactly one waiting sale has the same amount."""
    candidates = db.scalars(select(Sale).where(
        Sale.business_id == payment.business_id, Sale.status == "awaiting_payment", Sale.total == payment.amount,
        Sale.created_at >= payment.received_at - MATCH_SALE_BEFORE_PAYMENT,
        Sale.created_at <= payment.received_at + MATCH_PAYMENT_BEFORE_SALE)).all()
    candidates = [s for s in candidates if s.payment is None]
    if len(candidates) == 1:
        link_payment(candidates[0], payment, "auto")


def try_match_sale(db: Session, sale: Sale) -> None:
    """An M-Pesa sale was recorded: the customer may already have paid."""
    candidates = db.scalars(select(MpesaPayment).where(
        MpesaPayment.business_id == sale.business_id, MpesaPayment.sale_id.is_(None),
        MpesaPayment.amount == sale.total,
        MpesaPayment.received_at >= sale.created_at - MATCH_PAYMENT_BEFORE_SALE)).all()
    if len(candidates) == 1:
        link_payment(sale, candidates[0], "auto")


def _404():
    raise HTTPException(404, "Not found")


# ---------------------------------------------------------------- auth: owner accounts, devices, staff PINs

def current_staff(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> Staff:
    token = authorization.removeprefix("Bearer ").strip()
    row = db.get(AuthToken, token) if token else None
    if not row or not row.staff.active:
        raise HTTPException(401, "Please log in")
    return row.staff


def current_device(x_device: str = Header(default=""), db: Session = Depends(get_db)) -> Device:
    dev = db.get(Device, x_device) if x_device else None
    if not dev:
        raise HTTPException(401, "This phone is not signed in to a business")
    return dev


def require(*roles: str):
    def dep(staff: Staff = Depends(current_staff)) -> Staff:
        if staff.role not in roles:
            raise HTTPException(403, "Your role cannot do this")
        return staff
    return dep


OWNER = require("owner")
SELLERS = require("owner", "cashier")
STOCK_ROLES = require("owner", "storekeeper")
ANYONE = require(*ROLES)


def _session(db: Session, staff: Staff, device: Device | None) -> str:
    token = secrets.token_hex(24)
    db.add(AuthToken(token=token, staff_id=staff.id, device_token=device.token if device else None))
    return token


def _new_device(db: Session, owner: Staff) -> Device:
    dev = Device(token=secrets.token_hex(24), business_id=owner.business_id, created_by=owner.id)
    db.add(dev)
    return dev


def _find_owner_account(db: Session, phone: str | None = None, email: str | None = None) -> Staff | None:
    conds = []
    if phone:
        conds.append(Staff.phone == phone)
    if email:
        conds.append(Staff.email == email)
    if not conds:
        return None
    return db.scalar(select(Staff).where(Staff.password_hash.is_not(None), or_(*conds)))


class SignupIn(BaseModel):
    business_name: str = Field(min_length=1)
    till_number: str = ""
    owner_name: str = Field(min_length=1)
    phone: str
    email: str = ""
    password: str
    pin: str
    starter_menu: bool = True


class SigninIn(BaseModel):
    identifier: str = Field(min_length=3)  # phone or email
    password: str


class LoginIn(BaseModel):
    staff_id: int
    pin: str


class PasswordIn(BaseModel):
    current: str
    new: str


@app.get("/api/status")
def status():
    return {"demo_mode": DEMO_MODE}


@app.post("/api/auth/signup")
def signup(body: SignupIn, db: Session = Depends(get_db)):
    phone, email = norm_phone(body.phone), norm_email(body.email)
    check_password(body.password)
    check_pin(body.pin)
    if _find_owner_account(db, phone=phone):
        raise HTTPException(400, "An account with this phone number already exists. Sign in instead.")
    if email and _find_owner_account(db, email=email):
        raise HTTPException(400, "An account with this email already exists. Sign in instead.")
    biz = Business(name=body.business_name.strip(), till_number=body.till_number.strip(),
                   callback_key=secrets.token_urlsafe(24))
    db.add(biz)
    db.flush()
    owner = Staff(business_id=biz.id, name=body.owner_name.strip(), phone=phone, email=email, role="owner",
                  pin_hash=hash_pin(body.pin), password_hash=hash_password(body.password))
    db.add(owner)
    db.flush()
    if body.starter_menu:
        load_starter_menu(db, biz.id)
    dev = _new_device(db, owner)
    token = _session(db, owner, dev)
    db.commit()
    return {"device_token": dev.token, "token": token, "staff": staff_out(owner), "business": business_out(biz, True)}


@app.post("/api/auth/signin")
def signin(body: SigninIn, db: Session = Depends(get_db)):
    ident = body.identifier.strip()
    if "@" in ident:
        owner = _find_owner_account(db, email=ident.lower())
    else:
        try:
            owner = _find_owner_account(db, phone=norm_phone(ident))
        except HTTPException:
            owner = None
    if not owner:
        raise HTTPException(401, "Wrong phone/email or password")
    guard_lock(owner)
    if not owner.active or not _verify(body.password, owner.password_hash):
        record_failure(db, owner)
        raise HTTPException(401, "Wrong phone/email or password")
    owner.failed_attempts, owner.locked_until = 0, None
    dev = _new_device(db, owner)
    token = _session(db, owner, dev)
    db.commit()
    return {"device_token": dev.token, "token": token, "staff": staff_out(owner),
            "business": business_out(owner.business, True)}


@app.get("/api/device")
def device_info(dev: Device = Depends(current_device)):
    return {"business": business_out(dev.business)}


@app.post("/api/auth/signout-device")
def signout_device(x_device: str = Header(default=""), db: Session = Depends(get_db)):
    dev = db.get(Device, x_device) if x_device else None
    if dev:
        for t in db.scalars(select(AuthToken).where(AuthToken.device_token == dev.token)):
            db.delete(t)
        db.delete(dev)
        db.commit()
    return {"ok": True}


@app.get("/api/login-list")
def login_list(dev: Device = Depends(current_device), db: Session = Depends(get_db)):
    rows = db.scalars(select(Staff).where(Staff.business_id == dev.business_id, Staff.active.is_(True))
                      .order_by(Staff.role, Staff.name)).all()
    return [{"id": s.id, "name": s.name, "role": s.role} for s in rows]


@app.post("/api/login")
def login(body: LoginIn, dev: Device = Depends(current_device), db: Session = Depends(get_db)):
    s = db.get(Staff, body.staff_id)
    if not s or s.business_id != dev.business_id or not s.active:
        raise HTTPException(401, "Wrong PIN")
    guard_lock(s)
    if not _verify(body.pin, s.pin_hash):
        record_failure(db, s)
        raise HTTPException(401, "Wrong PIN")
    s.failed_attempts, s.locked_until = 0, None
    token = _session(db, s, dev)
    db.commit()
    return {"token": token, "staff": staff_out(s)}


@app.post("/api/logout")
def logout(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    row = db.get(AuthToken, authorization.removeprefix("Bearer ").strip())
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@app.get("/api/me")
def me(staff: Staff = Depends(ANYONE)):
    return {"staff": staff_out(staff), "business": business_out(staff.business, staff.role == "owner"),
            "demo_mode": DEMO_MODE}


@app.post("/api/auth/password")
def change_password(body: PasswordIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    if not _verify(body.current, staff.password_hash):
        raise HTTPException(400, "Current password is wrong")
    check_password(body.new)
    staff.password_hash = hash_password(body.new)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- business & staff

class BusinessIn(BaseModel):
    name: str = Field(min_length=1)
    till_number: str = ""


@app.put("/api/business")
def update_business(body: BusinessIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    b = staff.business
    b.name, b.till_number = body.name.strip(), body.till_number.strip()
    db.commit()
    return business_out(b, True)


class StaffIn(BaseModel):
    name: str = Field(min_length=1)
    phone: str = ""
    role: str
    pin: str | None = None
    active: bool = True


@app.get("/api/staff")
def list_staff(staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    q = select(Staff).where(Staff.business_id == staff.business_id).order_by(Staff.active.desc(), Staff.name)
    return [staff_out(s) for s in db.scalars(q)]


def _active_owners(db: Session, business_id: int) -> int:
    return db.scalar(select(func.count()).select_from(Staff).where(
        Staff.business_id == business_id, Staff.role == "owner", Staff.active.is_(True)))


@app.post("/api/staff")
def create_staff(body: StaffIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(400, "Unknown role")
    if not body.pin:
        raise HTTPException(400, "Set a 4-digit PIN for this staff member")
    check_pin(body.pin)
    s = Staff(business_id=staff.business_id, name=body.name.strip(), phone=body.phone.strip(), role=body.role,
              pin_hash=hash_pin(body.pin), active=body.active)
    db.add(s)
    db.commit()
    return staff_out(s)


@app.put("/api/staff/{staff_id}")
def update_staff(staff_id: int, body: StaffIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    s = own(db, Staff, staff_id, staff)
    if body.role not in ROLES:
        raise HTTPException(400, "Unknown role")
    losing_owner = s.role == "owner" and s.active and (body.role != "owner" or not body.active)
    if losing_owner and _active_owners(db, staff.business_id) <= 1:
        raise HTTPException(400, "Keep at least one active owner")
    if s.password_hash and body.role != "owner":
        raise HTTPException(400, "The account owner must stay an owner")
    s.name, s.role, s.active = body.name.strip(), body.role, body.active
    if not s.password_hash:  # the account owner's phone is their sign-in, changed separately
        s.phone = body.phone.strip()
    if body.pin:
        check_pin(body.pin)
        s.pin_hash = hash_pin(body.pin)
        s.failed_attempts, s.locked_until = 0, None
    db.commit()
    return staff_out(s)


# ---------------------------------------------------------------- menu

class CategoryIn(BaseModel):
    name: str = Field(min_length=1)
    sort: int | None = None


def _cat_out(c: Category) -> dict:
    return {"id": c.id, "name": c.name, "sort": c.sort}


@app.get("/api/categories")
def list_categories(staff: Staff = Depends(ANYONE), db: Session = Depends(get_db)):
    q = select(Category).where(Category.business_id == staff.business_id).order_by(Category.sort, Category.id)
    return [_cat_out(c) for c in db.scalars(q)]


@app.post("/api/categories")
def create_category(body: CategoryIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    top = db.scalar(select(func.max(Category.sort)).where(Category.business_id == staff.business_id)) or 0
    c = Category(business_id=staff.business_id, name=body.name.strip(),
                 sort=body.sort if body.sort is not None else top + 1)
    db.add(c)
    db.commit()
    return _cat_out(c)


@app.put("/api/categories/{cat_id}")
def update_category(cat_id: int, body: CategoryIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    c = own(db, Category, cat_id, staff)
    c.name = body.name.strip()
    if body.sort is not None:
        c.sort = body.sort
    db.commit()
    return _cat_out(c)


@app.delete("/api/categories/{cat_id}")
def delete_category(cat_id: int, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    c = own(db, Category, cat_id, staff)
    if db.scalar(select(func.count()).select_from(MenuItem).where(MenuItem.category_id == cat_id)):
        raise HTTPException(400, "Move or delete the items in this category first")
    db.delete(c)
    db.commit()
    return {"ok": True}


class MenuIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1)
    price: int = Field(ge=0)
    choice_label: str = ""
    choice_options: str = ""
    stock_item_id: int | None = None
    stock_qty: float = Field(default=1, gt=0)
    active: bool = True


@app.get("/api/menu")
def list_menu(include_inactive: bool = False, staff: Staff = Depends(ANYONE), db: Session = Depends(get_db)):
    q = (select(MenuItem).join(Category).where(MenuItem.business_id == staff.business_id)
         .order_by(Category.sort, MenuItem.sort, MenuItem.id))
    if not include_inactive:
        q = q.where(MenuItem.active.is_(True))
    return [menu_out(m) for m in db.scalars(q)]


def _apply_menu(m: MenuItem, body: MenuIn, db: Session, staff: Staff) -> None:
    own(db, Category, body.category_id, staff)
    if body.stock_item_id:
        own(db, StockItem, body.stock_item_id, staff)
    options = ", ".join(o.strip() for o in body.choice_options.split(",") if o.strip())
    if options and not body.choice_label.strip():
        raise HTTPException(400, "Give the choice a name, e.g. Accompaniment")
    m.category_id, m.name, m.price = body.category_id, body.name.strip(), body.price
    m.choice_label, m.choice_options = (body.choice_label.strip() if options else ""), options
    m.stock_item_id, m.stock_qty, m.active = body.stock_item_id or None, body.stock_qty, body.active


@app.post("/api/menu")
def create_menu_item(body: MenuIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    m = MenuItem(business_id=staff.business_id, category_id=body.category_id, name="", price=0)
    _apply_menu(m, body, db, staff)
    m.sort = (db.scalar(select(func.max(MenuItem.sort)).where(MenuItem.category_id == body.category_id)) or 0) + 1
    db.add(m)
    db.commit()
    db.refresh(m)
    return menu_out(m)


@app.put("/api/menu/{item_id}")
def update_menu_item(item_id: int, body: MenuIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    m = own(db, MenuItem, item_id, staff)
    _apply_menu(m, body, db, staff)
    db.commit()
    db.refresh(m)
    return menu_out(m)


# ---------------------------------------------------------------- stock

class StockIn(BaseModel):
    name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    kind: str = "direct"
    reorder_level: float = Field(default=0, ge=0)
    opening_qty: float = Field(default=0, ge=0)
    active: bool = True


class ReceiveIn(BaseModel):
    qty: float = Field(gt=0)
    total_cost: int = Field(default=0, ge=0)
    supplier: str = ""
    note: str = ""


class CountIn(BaseModel):
    counted_qty: float = Field(ge=0)
    note: str = ""


class WasteIn(BaseModel):
    qty: float = Field(gt=0)
    note: str = ""


@app.get("/api/stock")
def list_stock(staff: Staff = Depends(STOCK_ROLES), db: Session = Depends(get_db)):
    q = select(StockItem).where(StockItem.business_id == staff.business_id).order_by(StockItem.active.desc(),
                                                                                     StockItem.name)
    return [stock_out(s) for s in db.scalars(q)]


@app.post("/api/stock")
def create_stock(body: StockIn, staff: Staff = Depends(STOCK_ROLES), db: Session = Depends(get_db)):
    if body.kind not in ("direct", "ingredient"):
        raise HTTPException(400, "Kind must be direct or ingredient")
    s = StockItem(business_id=staff.business_id, name=body.name.strip(), unit=body.unit.strip(), kind=body.kind,
                  reorder_level=body.reorder_level, active=body.active, quantity=0)
    db.add(s)
    db.flush()
    if body.opening_qty:
        move_stock(db, s, body.opening_qty, "count", staff.id, note="Opening stock")
    db.commit()
    return stock_out(s)


@app.put("/api/stock/{stock_id}")
def update_stock(stock_id: int, body: StockIn, staff: Staff = Depends(STOCK_ROLES), db: Session = Depends(get_db)):
    s = own(db, StockItem, stock_id, staff)
    s.name, s.unit, s.kind = body.name.strip(), body.unit.strip(), body.kind
    s.reorder_level, s.active = body.reorder_level, body.active
    db.commit()
    return stock_out(s)


@app.post("/api/stock/{stock_id}/receive")
def receive_stock(stock_id: int, body: ReceiveIn, staff: Staff = Depends(STOCK_ROLES),
                  db: Session = Depends(get_db)):
    s = own(db, StockItem, stock_id, staff)
    move_stock(db, s, body.qty, "purchase", staff.id, total_cost=body.total_cost,
               supplier=body.supplier.strip(), note=body.note.strip())
    if body.total_cost:
        s.last_unit_cost = body.total_cost / body.qty
    db.commit()
    return stock_out(s)


@app.post("/api/stock/{stock_id}/count")
def count_stock(stock_id: int, body: CountIn, staff: Staff = Depends(STOCK_ROLES), db: Session = Depends(get_db)):
    s = own(db, StockItem, stock_id, staff)
    diff = round(body.counted_qty - s.quantity, 3)
    move_stock(db, s, diff, "count", staff.id, note=body.note.strip() or "Stock count")
    db.commit()
    return {**stock_out(s), "difference": diff}


@app.post("/api/stock/{stock_id}/waste")
def waste_stock(stock_id: int, body: WasteIn, staff: Staff = Depends(STOCK_ROLES), db: Session = Depends(get_db)):
    s = own(db, StockItem, stock_id, staff)
    move_stock(db, s, -body.qty, "waste", staff.id, note=body.note.strip())
    db.commit()
    return stock_out(s)


@app.get("/api/stock/{stock_id}/movements")
def stock_movements(stock_id: int, staff: Staff = Depends(STOCK_ROLES), db: Session = Depends(get_db)):
    own(db, StockItem, stock_id, staff)
    rows = db.scalars(select(StockMovement).where(StockMovement.stock_item_id == stock_id)
                      .order_by(StockMovement.id.desc()).limit(100))
    out = []
    for m in rows:
        num = db.get(Sale, m.sale_id).number if m.sale_id else None
        out.append({"id": m.id, "change": m.change, "reason": m.reason, "balance_after": m.balance_after,
                    "total_cost": m.total_cost, "supplier": m.supplier, "note": m.note,
                    "sale_number": f"#{num:05d}" if num else None,
                    "staff_name": m.staff.name if m.staff else "", "created_at": iso(m.created_at)})
    return out


# ---------------------------------------------------------------- sales

class LineIn(BaseModel):
    menu_item_id: int
    qty: int = Field(gt=0, le=200)
    choice: str = ""


class SaleIn(BaseModel):
    lines: list[LineIn] = Field(min_length=1)
    payment_method: str
    cash_tendered: int = Field(default=0, ge=0)


@app.post("/api/sales")
def create_sale(body: SaleIn, staff: Staff = Depends(SELLERS), db: Session = Depends(get_db)):
    if body.payment_method not in ("cash", "mpesa"):
        raise HTTPException(400, "Payment must be cash or mpesa")
    number = (db.scalar(select(func.max(Sale.number)).where(Sale.business_id == staff.business_id)) or 0) + 1
    sale = Sale(business_id=staff.business_id, number=number, staff_id=staff.id, total=0,
                payment_method=body.payment_method,
                status="paid" if body.payment_method == "cash" else "awaiting_payment")
    db.add(sale)
    db.flush()
    total = 0
    for line in body.lines:
        item = db.get(MenuItem, line.menu_item_id)
        if not item or item.business_id != staff.business_id or not item.active:
            raise HTTPException(400, "An item in the order is no longer on the menu")
        options = [o.strip() for o in item.choice_options.split(",") if o.strip()]
        if options and line.choice not in options:
            raise HTTPException(400, f"Pick {item.choice_label.lower()} for {item.name}")
        # Price always comes from the menu, never from the phone: cashiers cannot change prices.
        line_total = item.price * line.qty
        total += line_total
        sale.lines.append(SaleLine(menu_item_id=item.id, name=item.name, choice=line.choice if options else "",
                                   unit_price=item.price, qty=line.qty, line_total=line_total))
        if item.stock_item:
            move_stock(db, item.stock_item, -item.stock_qty * line.qty, "sale", staff.id, sale_id=sale.id)
    sale.total = total
    if body.payment_method == "cash":
        if body.cash_tendered and body.cash_tendered < total:
            raise HTTPException(400, "Cash given is less than the total")
        sale.cash_tendered = body.cash_tendered or total
        sale.paid_at = utcnow()
    else:
        db.flush()
        try_match_sale(db, sale)
    db.commit()
    db.refresh(sale)
    return sale_out(sale)


@app.get("/api/sales")
def list_sales(day: str | None = None, status: str | None = None, staff: Staff = Depends(SELLERS),
               db: Session = Depends(get_db)):
    start, end, _ = day_bounds(day)
    q = (select(Sale).where(Sale.business_id == staff.business_id, Sale.created_at >= start, Sale.created_at < end)
         .order_by(Sale.id.desc()))
    if staff.role == "cashier":
        q = q.where(Sale.staff_id == staff.id)
    if status:
        q = q.where(Sale.status == status)
    return [sale_out(s, with_lines=False) for s in db.scalars(q)]


@app.get("/api/sales/awaiting")
def awaiting_sales(days: int = 2, staff: Staff = Depends(SELLERS), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=max(1, min(days, 62)))
    q = select(Sale).where(Sale.business_id == staff.business_id, Sale.status == "awaiting_payment",
                           Sale.created_at >= since).order_by(Sale.id.desc())
    return [sale_out(s, with_lines=False) for s in db.scalars(q)]


@app.get("/api/sales/{sale_id}")
def get_sale(sale_id: int, staff: Staff = Depends(SELLERS), db: Session = Depends(get_db)):
    s = own(db, Sale, sale_id, staff)
    if staff.role == "cashier" and s.staff_id != staff.id:
        raise HTTPException(403, "Not your sale")
    return sale_out(s)


class VoidIn(BaseModel):
    reason: str = Field(min_length=2)


@app.post("/api/sales/{sale_id}/void")
def void_sale(sale_id: int, body: VoidIn, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    s = own(db, Sale, sale_id, staff)
    if s.status == "void":
        raise HTTPException(400, "Already voided")
    for line in s.lines:
        item = db.get(MenuItem, line.menu_item_id) if line.menu_item_id else None
        if item and item.stock_item:
            move_stock(db, item.stock_item, item.stock_qty * line.qty, "void", staff.id, sale_id=s.id,
                       note=f"Void #{s.number:05d}")
    if s.payment:
        s.payment.sale_id, s.payment.matched_by = None, ""
    s.status, s.voided_at, s.void_reason = "void", utcnow(), body.reason.strip()
    db.commit()
    db.refresh(s)
    return sale_out(s)


# ---------------------------------------------------------------- M-Pesa (till, C2B)

def _record_payment(db: Session, business_id: int, trans_id: str, amount: float, msisdn: str, name: str,
                    trans_time: str, raw: dict, source: str, received_at: datetime | None = None,
                    commit: bool = True) -> tuple[MpesaPayment, bool]:
    """Record a till payment once per M-Pesa receipt number (per business). Returns (payment, new)."""
    existing = db.scalar(select(MpesaPayment).where(MpesaPayment.business_id == business_id,
                                                    MpesaPayment.trans_id == trans_id))
    if existing:
        return existing, False
    p = MpesaPayment(business_id=business_id, trans_id=trans_id, amount=int(round(float(amount))), msisdn=msisdn,
                     payer_name=name, trans_time=trans_time, raw=json.dumps(raw, default=str), source=source,
                     received_at=received_at or utcnow())
    db.add(p)
    db.flush()
    try_match_payment(db, p)
    if commit:
        db.commit()
    return p, True


def _business_by_key(db: Session, key: str) -> Business:
    b = db.scalar(select(Business).where(Business.callback_key == key)) if key else None
    if not b:
        raise HTTPException(404)
    return b


@app.post("/api/mpesa/c2b/validation/{key}")
def c2b_validation(key: str, db: Session = Depends(get_db)):
    _business_by_key(db, key)
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@app.post("/api/mpesa/c2b/confirmation/{key}")
async def c2b_confirmation(key: str, request: Request, db: Session = Depends(get_db)):
    # Daraja callbacks are not signed: the business's secret key in the URL keeps random callers out.
    biz = _business_by_key(db, key)
    data = await request.json()
    name = " ".join(x for x in [data.get("FirstName", ""), data.get("MiddleName", ""),
                                data.get("LastName", "")] if x).strip()
    _record_payment(db, biz.id, str(data["TransID"]), data["TransAmount"], str(data.get("MSISDN", "")), name,
                    str(data.get("TransTime", "")), data, source="callback")
    return {"ResultCode": 0, "ResultDesc": "Accepted"}


class SimulateIn(BaseModel):
    amount: int = Field(gt=0)
    payer_name: str = "Demo Customer"
    phone: str = "2547*****123"


@app.post("/api/mpesa/simulate")
def simulate_payment(body: SimulateIn, staff: Staff = Depends(SELLERS), db: Session = Depends(get_db)):
    if not DEMO_MODE:
        raise HTTPException(403, "Simulation is off")
    trans_id = "SIM" + secrets.token_hex(4).upper()[:7]  # 10 characters, like a real receipt number
    p, _new = _record_payment(db, staff.business_id, trans_id, body.amount, body.phone, body.payer_name,
                              (utcnow() + NAIROBI).strftime("%Y%m%d%H%M%S"), {"simulated": True}, source="simulated")
    return payment_out(p)


@app.get("/api/mpesa/payments")
def list_payments(day: str | None = None, unmatched_only: bool = False, staff: Staff = Depends(SELLERS),
                  db: Session = Depends(get_db)):
    q = select(MpesaPayment).where(MpesaPayment.business_id == staff.business_id) \
        .order_by(MpesaPayment.received_at.desc())
    if unmatched_only:
        q = q.where(MpesaPayment.sale_id.is_(None), MpesaPayment.source != "statement",
                    MpesaPayment.received_at >= utcnow() - timedelta(days=2))
    else:
        start, end, _d = day_bounds(day)
        q = q.where(MpesaPayment.received_at >= start, MpesaPayment.received_at < end)
    return [payment_out(p) for p in db.scalars(q)]


class MatchIn(BaseModel):
    sale_id: int


@app.post("/api/mpesa/payments/{payment_id}/match")
def match_payment(payment_id: int, body: MatchIn, staff: Staff = Depends(SELLERS), db: Session = Depends(get_db)):
    p = own(db, MpesaPayment, payment_id, staff)
    s = own(db, Sale, body.sale_id, staff)
    if p.sale_id:
        raise HTTPException(400, "This payment is already matched")
    if s.status != "awaiting_payment" or s.payment:
        raise HTTPException(400, "This sale is not waiting for an M-Pesa payment")
    if p.amount != s.total:
        raise HTTPException(400, f"Amounts differ: payment KSh {p.amount}, sale KSh {s.total}")
    link_payment(s, p, "manual")
    db.commit()
    db.refresh(p)
    return payment_out(p)


# ---------------------------------------------------------------- M-Pesa statement reconciliation

MSISDN_RE = re.compile(r"(\+?254\d{9}|0[17]\d{8}|\d{3,6}\*{2,}\d{2,4})")


def _in_chunks(values: list, size: int = 500):
    for i in range(0, len(values), size):
        yield values[i:i + size]


def statement_report(db: Session, imp: StatementImport) -> dict:
    receipts = json.loads(imp.receipts)
    payments: list[MpesaPayment] = []
    for chunk in _in_chunks(receipts):
        payments += db.scalars(select(MpesaPayment).where(MpesaPayment.business_id == imp.business_id,
                                                          MpesaPayment.trans_id.in_(chunk))).all()
    payments.sort(key=lambda p: p.received_at)
    on_statement = set(receipts)
    start, _e, _d = day_bounds(imp.first_day)
    _s, end, _d2 = day_bounds(imp.last_day)
    sales = db.scalars(select(Sale).where(Sale.business_id == imp.business_id, Sale.payment_method == "mpesa",
                                          Sale.status != "void", Sale.created_at >= start, Sale.created_at < end)
                       .order_by(Sale.created_at)).all()
    matched = [p for p in payments if p.sale_id]
    unrecorded = [p for p in payments if not p.sale_id]
    missing = [s for s in sales if not (s.payment and s.payment.trans_id in on_statement)]
    statement_total = sum(p.amount for p in payments)
    pos_total = sum(s.total for s in sales)
    return {
        "id": imp.id, "filename": imp.filename, "uploaded_at": iso(imp.uploaded_at),
        "uploaded_by": imp.staff.name, "first_day": imp.first_day, "last_day": imp.last_day,
        "rows_read": imp.rows_read, "incoming_count": imp.incoming_count, "new_count": imp.new_count,
        "already_known": imp.incoming_count - imp.new_count,
        "statement_total": statement_total, "pos_mpesa_total": pos_total,
        "difference": statement_total - pos_total,
        "matched_total": sum(p.amount for p in matched),
        "unrecorded_total": sum(p.amount for p in unrecorded),
        "missing_total": sum(s.total for s in missing),
        "matched": [payment_out(p) for p in matched],
        "unrecorded": [payment_out(p) for p in unrecorded],
        "missing": [sale_out(s, with_lines=False) for s in missing],
    }


@app.post("/api/mpesa/statements")
async def upload_statement(file: UploadFile = File(...), password: str = Form(""),
                           staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    data = await file.read()
    if len(data) > MAX_STATEMENT_BYTES:
        raise HTTPException(400, f"This file is too big (limit {MAX_STATEMENT_BYTES // (1024 * 1024)} MB)")
    try:
        rows = read_statement(data, password)  # in memory only: the PDF is never written to disk or stored
    except StatementError as e:
        raise HTTPException(400, str(e))
    incoming = incoming_payments(rows)
    if not incoming:
        raise HTTPException(400, "This statement has no money coming in")
    new = 0
    for r in incoming:
        phone = MSISDN_RE.search(r["details"])
        _p, created = _record_payment(
            db, staff.business_id, r["receipt"], r["paid_in"], phone.group(1) if phone else "",
            payer_from_details(r["details"]), r["completion_time"].strftime("%Y%m%d%H%M%S"),
            {"details": r["details"], "status": r["status"]}, source="statement",
            received_at=r["completion_time"] - NAIROBI, commit=False)
        new += created
    times = [r["completion_time"] for r in incoming]
    imp = StatementImport(business_id=staff.business_id, filename=(file.filename or "")[:200], staff_id=staff.id,
                          first_day=min(times).date().isoformat(), last_day=max(times).date().isoformat(),
                          rows_read=len(rows), incoming_count=len(incoming), new_count=new,
                          receipts=json.dumps([r["receipt"] for r in incoming]))
    db.add(imp)
    db.commit()
    return statement_report(db, imp)


@app.get("/api/mpesa/statements")
def list_statements(staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    rows = db.scalars(select(StatementImport).where(StatementImport.business_id == staff.business_id)
                      .order_by(StatementImport.id.desc()).limit(30))
    return [{"id": i.id, "filename": i.filename, "uploaded_at": iso(i.uploaded_at), "first_day": i.first_day,
             "last_day": i.last_day, "incoming_count": i.incoming_count, "new_count": i.new_count} for i in rows]


@app.get("/api/mpesa/statements/{imp_id}")
def get_statement(imp_id: int, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    return statement_report(db, own(db, StatementImport, imp_id, staff))


# ---------------------------------------------------------------- weekly M-Pesa analytics

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())  # weeks run Monday to Sunday


@app.get("/api/mpesa/analytics")
def mpesa_analytics(week: str | None = None, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    """Till payments (statements, live and demo) for one Monday–Sunday week, Nairobi time."""
    ws = _week_start(date.fromisoformat(week) if week else (utcnow() + NAIROBI).date())
    start = datetime(ws.year, ws.month, ws.day) - NAIROBI
    end = start + timedelta(days=7)
    base = select(MpesaPayment).where(MpesaPayment.business_id == staff.business_id)
    pays = db.scalars(base.where(MpesaPayment.received_at >= start, MpesaPayment.received_at < end)).all()
    prev_total = db.scalar(select(func.coalesce(func.sum(MpesaPayment.amount), 0)).where(
        MpesaPayment.business_id == staff.business_id, MpesaPayment.received_at >= start - timedelta(days=7),
        MpesaPayment.received_at < start)) or 0
    latest = db.scalar(select(func.max(MpesaPayment.received_at)).where(MpesaPayment.business_id == staff.business_id))

    by_day = [{"date": (ws + timedelta(days=i)).isoformat(), "label": DAY_NAMES[i], "total": 0, "count": 0}
              for i in range(7)]
    hours = [0] * 24
    payers: dict[str, dict] = {}
    for p in pays:
        local = p.received_at + NAIROBI
        d = by_day[(local.date() - ws).days]
        d["total"] += p.amount
        d["count"] += 1
        hours[local.hour] += p.amount
        key = p.payer_name or p.msisdn or "Unknown"
        e = payers.setdefault(key, {"name": key, "count": 0, "total": 0})
        e["count"] += 1
        e["total"] += p.amount
    total = sum(p.amount for p in pays)
    matched = [p for p in pays if p.sale_id]
    busiest = max(by_day, key=lambda d: d["total"]) if total else None
    return {
        "week_start": ws.isoformat(), "week_end": (ws + timedelta(days=6)).isoformat(),
        "latest_week": _week_start((latest + NAIROBI).date()).isoformat() if latest else None,
        "total": total, "count": len(pays), "average": round(total / len(pays)) if pays else 0,
        "largest": max((p.amount for p in pays), default=0),
        "previous_total": prev_total,
        "change_pct": round((total - prev_total) / prev_total * 100) if prev_total else None,
        "by_day": by_day, "hours": hours,
        "busiest_day": busiest["label"] if busiest else None,
        "peak_hour": max(range(24), key=lambda h: hours[h]) if total else None,
        "top_payers": sorted(payers.values(), key=lambda x: (-x["total"], -x["count"]))[:5],
        "matched_total": sum(p.amount for p in matched), "matched_count": len(matched),
        "unmatched_total": total - sum(p.amount for p in matched), "unmatched_count": len(pays) - len(matched),
        "sources": {s: sum(1 for p in pays if p.source == s) for s in ("statement", "callback", "simulated")},
    }


# ---------------------------------------------------------------- owner dashboard

@app.get("/api/dashboard")
def dashboard(day: str | None = None, staff: Staff = Depends(OWNER), db: Session = Depends(get_db)):
    bid = staff.business_id
    start, end, day_str = day_bounds(day)
    sales = db.scalars(select(Sale).where(Sale.business_id == bid, Sale.created_at >= start, Sale.created_at < end,
                                          Sale.status != "void")).all()
    voided = db.scalar(select(func.count()).select_from(Sale).where(
        Sale.business_id == bid, Sale.created_at >= start, Sale.created_at < end, Sale.status == "void"))
    cash = sum(s.total for s in sales if s.payment_method == "cash")
    mpesa_paid = sum(s.total for s in sales if s.payment_method == "mpesa" and s.status == "paid")
    mpesa_waiting = sum(s.total for s in sales if s.status == "awaiting_payment")
    received = db.scalars(select(MpesaPayment).where(MpesaPayment.business_id == bid,
                                                     MpesaPayment.received_at >= start,
                                                     MpesaPayment.received_at < end)).all()
    items: dict[str, dict] = {}
    by_staff: dict[str, dict] = {}
    hours = [0] * 24
    for s in sales:
        st = by_staff.setdefault(s.staff.name, {"name": s.staff.name, "sales": 0, "total": 0})
        st["sales"] += 1
        st["total"] += s.total
        hours[(s.created_at + NAIROBI).hour] += s.total
        for l in s.lines:
            it = items.setdefault(l.name, {"name": l.name, "qty": 0, "total": 0})
            it["qty"] += l.qty
            it["total"] += l.line_total
    low = [stock_out(x) for x in db.scalars(select(StockItem).where(
        StockItem.business_id == bid, StockItem.active.is_(True),
        StockItem.quantity <= StockItem.reorder_level).order_by(StockItem.name))]
    return {
        "day": day_str, "total_sales": cash + mpesa_paid + mpesa_waiting,
        "cash": cash, "mpesa_paid": mpesa_paid, "mpesa_waiting": mpesa_waiting,
        "mpesa_received": sum(p.amount for p in received),
        "unmatched_payments": sum(1 for p in received if p.sale_id is None and p.source != "statement"),
        "transactions": len(sales), "voided": voided,
        "items_sold": sum(l.qty for s in sales for l in s.lines),
        "top_items": sorted(items.values(), key=lambda x: (-x["qty"], -x["total"]))[:6],
        "by_staff": sorted(by_staff.values(), key=lambda x: -x["total"]),
        "hours": hours, "low_stock": low,
        "recent": [sale_out(s, with_lines=False) for s in sorted(sales, key=lambda s: -s.id)[:6]],
    }


# ---------------------------------------------------------------- web app

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/sw.js")
def service_worker():
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/{path:path}")
def web_app(path: str):
    if path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return FileResponse(STATIC_DIR / "index.html")
