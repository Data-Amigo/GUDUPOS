"""Read an M-Pesa statement PDF and return the money that came in.

Adapted from parser.py in Project Finance (M-Pesa Ledger), without pandas.
It targets the standard Safaricom statement table:

    Receipt No. | Completion Time | Details | Transaction Status | Paid In | Withdrawn | Balance

It tries pdfplumber's table extraction first and falls back to reading the raw
text line by line when the table grid is messy.

NOTE: written against the personal statement layout. A till (business)
statement may differ; adjust here once we have a real till sample.
"""
from __future__ import annotations

import io
import re
from datetime import datetime

import pdfplumber

RECEIPT_RE = re.compile(r"^[A-Z0-9]{10}$")
DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
MONEY_RE = re.compile(r"-?[\d,]+\.\d{2}")
STATUS_RE = re.compile(r"(COMPLETED|FAILED|PENDING|REVERSED|CANCELLED)", re.I)


class StatementError(ValueError):
    pass


def _to_float(value) -> float:
    if value is None:
        return 0.0
    text = str(value).replace(",", "").strip()
    if text in ("", "-"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _looks_like_header(row) -> bool:
    joined = " ".join(str(c or "").lower() for c in row)
    return "receipt" in joined or "completion time" in joined


def _parse_tables(pdf) -> list[dict]:
    rows: list[dict] = []
    for page in pdf.pages:
        for table in page.extract_tables() or []:
            for raw in table:
                if not raw or len(raw) < 7 or _looks_like_header(raw):
                    continue
                receipt = str(raw[0] or "").strip()
                completion = str(raw[1] or "").strip()
                dt = DATETIME_RE.search(completion)
                if not RECEIPT_RE.match(receipt) or not dt:
                    continue
                rows.append({
                    "receipt": receipt,
                    "completion_time": dt.group(0),
                    "details": str(raw[2] or "").strip().replace("\n", " "),
                    "status": str(raw[3] or "").strip(),
                    "paid_in": _to_float(raw[4]),
                    "withdrawn": abs(_to_float(raw[5])),
                    "balance": _to_float(raw[6]),
                })
    return rows


def _parse_text(pdf) -> list[dict]:
    lines: list[str] = []
    for page in pdf.pages:
        lines.extend((page.extract_text() or "").split("\n"))

    rows: list[dict] = []

    def flush(buffer: list[str]) -> None:
        block = " ".join(buffer)
        receipt_match = re.match(r"^([A-Z0-9]{10})\s+", block)
        dt_match = DATETIME_RE.search(block)
        if not receipt_match or not dt_match:
            return
        money = MONEY_RE.findall(block)
        if len(money) < 3:
            return
        after_dt = block[dt_match.end():]
        first_money = MONEY_RE.search(after_dt)
        details = after_dt[: first_money.start()] if first_money else after_dt
        status = ""
        m = STATUS_RE.search(details)
        if m:
            status = m.group(1).upper()
            details = details[: m.start()]
        rows.append({
            "receipt": receipt_match.group(1),
            "completion_time": dt_match.group(0),
            "details": details.strip(),
            "status": status,
            "paid_in": _to_float(money[-3]),
            "withdrawn": abs(_to_float(money[-2])),
            "balance": _to_float(money[-1]),
        })

    current: list[str] | None = None
    for line in lines:
        if re.match(r"^[A-Z0-9]{10}\s", line) and DATETIME_RE.search(line):
            if current:
                flush(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current:
        flush(current)
    return rows


def payer_from_details(details: str) -> str:
    """'Funds received from 0712***678 - JOHN KAMAU' -> 'JOHN KAMAU' (best effort)."""
    if " - " in details:
        return details.rsplit(" - ", 1)[1].strip()[:80]
    return details.strip()[:80]


def read_statement(data: bytes, password: str | None = None) -> list[dict]:
    """All transactions in the statement, oldest first, as dicts."""
    try:
        with pdfplumber.open(io.BytesIO(data), password=password or "") as pdf:
            rows = _parse_tables(pdf)
            if len(rows) < 3:
                rows = _parse_text(pdf)
    except Exception as e:  # wrong password, not a PDF, damaged file
        name = type(e).__name__.lower()
        if "password" in name or "password" in str(e).lower():
            raise StatementError("Wrong statement password") from e
        raise StatementError("Could not read this file. Upload the M-Pesa statement PDF.") from e
    if not rows:
        raise StatementError("No transactions found. Check the password and that this is a full M-Pesa statement.")
    seen, unique = set(), []
    for r in rows:  # same row on two pages / extracted twice
        key = tuple(r.values())
        if key not in seen:
            seen.add(key)
            unique.append(r)
    for r in unique:
        r["completion_time"] = datetime.strptime(r["completion_time"], "%Y-%m-%d %H:%M:%S")
    return sorted(unique, key=lambda r: r["completion_time"])


def incoming_payments(rows: list[dict]) -> list[dict]:
    """Only completed money in. Charges, withdrawals, failed and reversed rows are left out."""
    out, seen = [], set()
    for r in rows:
        status = r["status"].upper()
        if r["paid_in"] <= 0 or (status and status != "COMPLETED"):
            continue
        if r["receipt"] in seen:
            continue
        seen.add(r["receipt"])
        out.append(r)
    return out
