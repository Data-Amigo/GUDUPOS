"""Data model. Money is stored in whole Kenya shillings (int). Times are stored in UTC.

Every business-owned table carries `business_id`; the API always filters on it, so one
business can never read or change another business's data.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Business(Base):
    __tablename__ = "business"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    till_number: Mapped[str] = mapped_column(String(20), default="")
    callback_key: Mapped[str] = mapped_column(String(64), unique=True)  # identifies the business in M-Pesa callback URLs
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Staff(Base):
    __tablename__ = "staff"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str] = mapped_column(String(20), default="")
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    role: Mapped[str] = mapped_column(String(20))  # owner | cashier | storekeeper
    pin_hash: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)  # owner account sign-in
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    business: Mapped[Business] = relationship()


class Device(Base):
    """A phone the owner signed in on. It can then show the staff PIN screen for that business."""
    __tablename__ = "device"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    business: Mapped[Business] = relationship()


class AuthToken(Base):
    """A staff member's session on a device (ends when they log out / lock the till)."""
    __tablename__ = "auth_token"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    device_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    staff: Mapped[Staff] = relationship()


class Category(Base):
    __tablename__ = "category"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    sort: Mapped[int] = mapped_column(Integer, default=0)


class StockItem(Base):
    __tablename__ = "stock_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(20))
    kind: Mapped[str] = mapped_column(String(20), default="direct")  # direct | ingredient
    quantity: Mapped[float] = mapped_column(Float, default=0)
    reorder_level: Mapped[float] = mapped_column(Float, default=0)
    last_unit_cost: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MenuItem(Base):
    __tablename__ = "menu_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))
    name: Mapped[str] = mapped_column(String(80))
    price: Mapped[int] = mapped_column(Integer)
    choice_label: Mapped[str] = mapped_column(String(40), default="")
    choice_options: Mapped[str] = mapped_column(Text, default="")
    stock_item_id: Mapped[int | None] = mapped_column(ForeignKey("stock_item.id"), nullable=True)
    stock_qty: Mapped[float] = mapped_column(Float, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[Category] = relationship()
    stock_item: Mapped[StockItem | None] = relationship()


class StockMovement(Base):
    __tablename__ = "stock_movement"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    stock_item_id: Mapped[int] = mapped_column(ForeignKey("stock_item.id"), index=True)
    change: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(20))  # purchase | sale | count | waste | void
    balance_after: Mapped[float] = mapped_column(Float, default=0)
    total_cost: Mapped[int] = mapped_column(Integer, default=0)
    supplier: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(String(200), default="")
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("sale.id"), nullable=True)
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    stock_item: Mapped[StockItem] = relationship()
    staff: Mapped[Staff | None] = relationship()


class Sale(Base):
    __tablename__ = "sale"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    number: Mapped[int] = mapped_column(Integer, default=0)  # receipt number within the business
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    total: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String(20))  # cash | mpesa
    status: Mapped[str] = mapped_column(String(20))  # paid | awaiting_payment | void
    cash_tendered: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    void_reason: Mapped[str] = mapped_column(String(200), default="")
    staff: Mapped[Staff] = relationship()
    lines: Mapped[list["SaleLine"]] = relationship(back_populates="sale", cascade="all, delete-orphan")
    payment: Mapped["MpesaPayment | None"] = relationship(back_populates="sale", uselist=False)


class SaleLine(Base):
    __tablename__ = "sale_line"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sale.id"), index=True)
    menu_item_id: Mapped[int | None] = mapped_column(ForeignKey("menu_item.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    choice: Mapped[str] = mapped_column(String(60), default="")
    unit_price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[int] = mapped_column(Integer)
    sale: Mapped[Sale] = relationship(back_populates="lines")


class MpesaPayment(Base):
    """A till payment: from a Safaricom callback, an uploaded statement, or a demo simulation."""
    __tablename__ = "mpesa_payment"
    __table_args__ = (UniqueConstraint("business_id", "trans_id", name="uq_payment_receipt"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    trans_id: Mapped[str] = mapped_column(String(30))
    amount: Mapped[int] = mapped_column(Integer)
    msisdn: Mapped[str] = mapped_column(String(40), default="")
    payer_name: Mapped[str] = mapped_column(String(80), default="")
    trans_time: Mapped[str] = mapped_column(String(20), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    sale_id: Mapped[int | None] = mapped_column(ForeignKey("sale.id"), nullable=True, unique=True)
    matched_by: Mapped[str] = mapped_column(String(20), default="")  # auto | manual
    source: Mapped[str] = mapped_column(String(20), default="callback")  # callback | simulated | statement
    raw: Mapped[str] = mapped_column(Text, default="")
    sale: Mapped[Sale | None] = relationship(back_populates="payment")


class StatementImport(Base):
    """One uploaded M-Pesa statement. The PDF itself is never stored, only what was read from it."""
    __tablename__ = "statement_import"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("business.id"), index=True)
    filename: Mapped[str] = mapped_column(String(200), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"))
    first_day: Mapped[str] = mapped_column(String(10))
    last_day: Mapped[str] = mapped_column(String(10))
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    incoming_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    receipts: Mapped[str] = mapped_column(Text, default="[]")
    staff: Mapped[Staff] = relationship()
