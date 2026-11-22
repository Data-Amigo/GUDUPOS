# POS & Stock — phone-first POS for Kenyan hotels and eateries

Built first for **Gudu Bites**. Any business can sign up, and each one sees only its own data. Staff use their own smartphones: no computers, scanners or app store download needed.

## How people get in

1. **Create account** (owner, once): business name, till number, owner name, phone, optional email, password, and a 4-digit PIN for the till screen.
2. **Sign in** on a phone (owner): phone number (any format: `0712…`, `+254 712…`) or email, plus the password. That links the phone to the business.
3. **Who is working? + PIN** (everyone, every shift): staff tap their name and enter their PIN. Logging out locks the till. The password is only needed again on a new phone or after **Sign this phone out**.

Five wrong PINs or passwords lock that person out for 5 minutes. This is the same pattern as Loyverse and Shopify POS: an owner account with a password, plus a staff PIN on the device.

## What each role can do

| Who | What they can do |
|---|---|
| **Owner** | Dashboard, sell, all sales, void, menu, staff, stock, M-Pesa matching, statement checks, weekly M-Pesa analytics, settings |
| **Cashier** | Sell, see only their own sales, match M-Pesa payments to sales |
| **Storekeeper** | Stock: add items, receive, count, record waste |

## Features

- **Selling:** tap items, pick choices (e.g. Ugali / Rice / Chapati), pay by cash (change worked out) or M-Pesa (till number shown). Prices always come from the menu, so cashiers can't change them.
- **Stock:** items sold as they are (sodas, water) go down automatically when sold. Ingredients go in with *Receive* and are checked with *Count*. A voided sale puts its stock back.
- **M-Pesa till:** an M-Pesa sale stays *Waiting* until a till payment is matched to it. If exactly one waiting sale has the same amount, the match is automatic; otherwise someone picks the sale. Demo mode can simulate payments until Safaricom approves the live connection.
- **Statement check:** upload an M-Pesa statement PDF and its password. Each incoming payment is recorded once by receipt number and matched where possible. The report shows the statement total vs POS M-Pesa sales, **paid but no sale recorded**, and **M-Pesa sale but no payment on the statement**. The PDF is read in memory and never stored. The reader is adapted from `Project Finance/parser.py` (personal statement layout) and must be checked against a real till statement.
- **M-Pesa by week:** pick any Monday–Sunday week to see money received, number of payments, average and largest payment, change vs last week, takings by day, time of day, top payers, and how much is matched to sales.
- **Owner dashboard:** daily sales, cash vs M-Pesa, sales by hour, best sellers, sales by cashier, stock alerts.

## Put it online on Vercel

Vercel can't keep a database file, so the app needs a Postgres database. Neon is free and is added from inside Vercel.

1. Put this folder in a GitHub repo.
2. Go to **vercel.com/new** and import the repo. Vercel detects FastAPI (`pyproject.toml` points it at `app/main.py`). Don't deploy yet if it asks for settings: open the project.
3. Open **Storage → Create Database → Neon (Postgres)**, then connect it to this project. That adds `DATABASE_URL` for you.
4. Click **Deployments → Redeploy** (or deploy for the first time).
5. Open the project URL and **Create account**. On each phone, Chrome menu → *Add to Home screen*.

From a terminal instead: `npm i -g vercel`, then run `vercel` in this folder and `vercel --prod`. Add the Neon database from the dashboard as in step 3.

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | SQLite file locally | Required on Vercel (set by the Neon integration) |
| `DEMO_MODE` | `true` | Shows the "simulate till payment" buttons. Set to `false` once the live till is connected |

Limits to know on Vercel:
- Uploads must be under **4 MB**, the Vercel limit; a month's statement PDF is usually well under that.
- The first request after a quiet period can take a few seconds while the function starts.

## Run it on a laptop (Windows)

1. Install Python 3.11+ from python.org (tick "Add Python to PATH").
2. Double-click `run_local.bat`, then open http://localhost:8000 and create an account.
3. To use it from a phone on the same Wi-Fi, run `ipconfig` and open `http://LAPTOP-IP:8000` on the phone.

A `gudu_pos.db` file from the earlier single-business prototype is rebuilt automatically, which wipes its demo data. Delete `gudu_pos.db` any time to start fresh.

## Connecting the real till (after Safaricom approval)

**Settings → M-Pesa live connection** shows this business's two private callback URLs. Register them with the Daraja C2B Register URL API for the till's Store Number, then set `DEMO_MODE=false`. Each payment is recorded once by its M-Pesa receipt number, so repeated callbacks, and statements that include the same payments, are safe.

## Demo the statement check

Until the client sends a real till statement, make a clearly labelled demo PDF from today's M-Pesa sales. This works with the local SQLite database:

```
pip install reportlab
python tools/make_demo_statement.py --business gudu    # writes demo_statement.pdf, password 1234
```

Then on the M-Pesa screen: **Upload statement** → `demo_statement.pdf` → password `1234`.

## Tests

```
pip install pytest reportlab playwright
python -m pytest -q tests/test_api.py      # accounts, PIN lockout, business isolation, sales, stock,
                                           # M-Pesa matching, statement check, weekly analytics
TEST_DATABASE_URL=postgresql://... python -m pytest -q tests/test_api.py   # same, against Postgres
python tests/screens.py URL OUTDIR         # phone-size screenshots (needs a running server)
```

## Project layout

```
app/main.py        API + serves the web app (Vercel entrypoint)
app/models.py      database tables (every business-owned table has business_id)
app/db.py          SQLite locally, Postgres via DATABASE_URL (serverless-safe on Vercel)
app/statement.py   M-Pesa statement PDF reader (from Project Finance)
app/seed.py        sample hotel menu from the Gudu Bites menu photo
static/            the mobile web app (index.html, app.js, styles.css, PWA files)
tools/             demo statement generator
docs/DECISIONS.md  what was decided and why
```
