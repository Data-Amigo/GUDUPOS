# Decisions log

## 2026-11-21: Prototype build

| # | Decision | Why |
|---|---|---|
| 1 | FastAPI + SQLAlchemy, with a no-build mobile web app served by the same server | One project, one deploy. Python is the team's strongest tool. Easy to host on Railway. |
| 2 | SQLite locally, Postgres in production (`DATABASE_URL`) | Zero setup for a laptop demo. Postgres keeps data safe on Railway. |
| 3 | The client enters menu, staff and stock themselves. Setup optionally loads part of the menu from the photo | The owner must be able to change prices and items without us. The starter menu only speeds up the first demo. |
| 4 | Login = tap your name + 4-digit PIN, three roles (owner, cashier, storekeeper) | Fast on a shared phone. Cashiers cannot change prices or see others' sales. Storekeepers only see stock. |
| 5 | Prices always come from the server's menu, never from the phone | A cashier cannot sell at a different price by editing the request. |
| 6 | Payment is a **Till** (Buy Goods). An M-Pesa sale is `awaiting_payment` until a till payment is matched | We never mark a sale paid just because the cashier chose M-Pesa. Till payments carry no order reference, so matching is by amount and time. |
| 7 | Automatic match only when exactly **one** candidate fits (same amount, payment within 15 min before / 60 min after the sale). Otherwise manual match | Two KSh 250 sales at the same time can't be told apart. Guessing would hide errors. |
| 8 | C2B callbacks are recorded once per `TransID`, and the callback URL contains a secret | Safaricom can resend callbacks. Daraja callbacks are not signed. |
| 9 | Demo mode simulates till payments | The live till needs Safaricom approval (Store Number + business admin). The client can still see the full flow today. |
| 10 | Stock v1: sold-as-is items linked to menu items go down automatically. Ingredients go in by Receive and out by Count. No recipes yet | Recipe deduction gives false precision until portions are measured. Counts are needed either way. |
| 11 | No KRA eTIMS | The client confirmed it isn't needed now. |
| 12 | ~~Single business per install for the prototype~~ (replaced by 21) | Speed. Multi-business (for the salon/barbershop version) is a later change: add `business_id` to every table. |
| 13 | Voiding is owner-only and puts stock back. A matched payment becomes unmatched again | Keeps the money and stock trail honest. |

## 2026-11-21: M-Pesa statement check

| # | Decision | Why |
|---|---|---|
| 14 | Reuse the PDF reader from `Project Finance/parser.py`, without pandas | Proven code. The POS only needs a list of rows, which keeps the server light. |
| 15 | Keep only completed **Paid In** rows | Reconciliation is about money coming in. Charges, withdrawals, failed and reversed rows are left out. |
| 16 | Statement payments are **recorded** as till payments (source `statement`) and go through the normal matching | Before the live till is connected, the statement is the only proof of M-Pesa money, so waiting sales should become Paid from it. |
| 17 | One payment per receipt number across callback, statement and re-uploads | Overlapping statements, or a callback followed by a statement, must never count money twice. |
| 18 | Report = statement total vs POS M-Pesa total for the statement's days + three lists: matched, paid but no sale, M-Pesa sale but no payment | These are the owner's two real questions: did money come in without a sale, and did a "M-Pesa" sale come in without money? |
| 19 | The PDF is read in memory and never stored. Only receipt, time, amount, payer and details are kept | Data protection: an M-Pesa statement is sensitive. |
| 20 | Built against the personal statement layout for now. The client will send a till statement after seeing the demo | The user's call. The reader must be checked and adjusted against a real till statement before go-live. |

## 2026-11-21: Accounts, many businesses, weekly analytics, Vercel

| # | Decision | Why |
|---|---|---|
| 21 | **Many businesses** can sign up. Every business-owned table has `business_id`, and every query filters on it | The user's choice: it makes this the product, so the salon/barbershop version can run on it. Replaces decision 12. |
| 22 | Owner account = phone **or** email + password (min 8 characters). The phone is normalised to `2547XXXXXXXX`, so any format signs in | The standard POS pattern (Loyverse, Shopify POS, Poster). Phone is natural for Kenyan owners, and email is optional. |
| 23 | Owner sign-in links the **phone (device)** to the business. Staff then use name + 4-digit PIN on that phone | Staff never need the owner's password. The PIN screen only lists that business's staff. |
| 24 | 5 wrong PINs or passwords lock that person for 5 minutes | A 4-digit PIN on a public URL must not be guessable by trying them all. |
| 25 | Each business gets a private `callback_key` used in its M-Pesa callback URLs | Tells the server which business a Safaricom callback belongs to, and keeps strangers from posting fake payments. |
| 26 | M-Pesa receipt numbers are unique **per business** | Two businesses can't clash, and a callback followed by a statement is still counted once. |
| 27 | Receipt numbers (`#00001`) count per business | Each business sees its own sequence. |
| 28 | Weekly analytics cover every till payment (statement, live and demo), Monday–Sunday, Nairobi time | The owner's question is how much came in on M-Pesa this week, whatever the source. |
| 29 | Vercel + **Neon Postgres**. On Vercel the app refuses to start without `DATABASE_URL`, and uses no connection pool (NullPool) | Vercel functions have no lasting disk. Serverless functions shouldn't hold database connections open. |
| 30 | `pyproject.toml` names `app.main:app` as the Vercel entrypoint. `.vercelignore` leaves out tests, tools and docs | Follows Vercel's FastAPI docs and keeps the function bundle small. |
| 31 | Statement uploads are capped at 4 MB on Vercel | Vercel's request body limit is 4.5 MB. |

Tested on SQLite and on Postgres (in Vercel mode with NullPool). Not yet deployed to Vercel itself.

## Open / next

- Forgot-password flow (needs SMS or email sending). For now the owner changes the password in Settings while signed in.
- First real Vercel deploy: check one sale, one statement upload and the weekly page.

- Check `app/statement.py` against a real Gudu Bites till statement (PDF from M-Pesa for Business, or Excel/CSV from the business portal).

- Connect the live till (Daraja go-live with the client's M-Pesa admin + Store Number).
- Pull Transactions API to recover payments if a callback is missed.
- Daily closing report on WhatsApp.
- Recipes and the "should vs actual" stock report.
- Offline selling if the hotel's internet is unreliable.
