"""Drive the app in a phone-sized browser and save screenshots of each screen."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8077"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/shots")
OUT.mkdir(parents=True, exist_ok=True)
errors = []


def shot(page, name):
    page.wait_for_timeout(450)
    page.screenshot(path=str(OUT / f"{name}.png"))


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    page.goto(BASE)
    page.wait_for_selector("form[data-form=signin]")
    shot(page, "00-signin")
    page.click("[data-act=auth-mode][data-m=signup]")
    page.fill("[name=business_name]", "Gudu Bites")
    page.fill("[name=till_number]", "5123456")
    page.fill("[name=owner_name]", "Peter Gudu")
    page.fill("[name=phone]", "0712345678")
    page.fill("[name=password]", "secret123")
    page.fill("[name=pin]", "1234")
    page.fill("[name=pin2]", "1234")
    shot(page, "01-signup")
    page.click("form[data-form=signup] button.btn")
    page.wait_for_selector(".hero")
    shot(page, "02-dashboard-empty")

    # stock: add sodas
    page.goto(BASE + "/#/stock")
    page.wait_for_selector(".fab")
    page.click(".fab")
    page.wait_for_timeout(250)
    page.fill("[name=name]", "Soda 350ml")
    page.fill("[name=unit]", "bottles")
    page.fill("[name=reorder_level]", "12")
    page.fill("[name=opening_qty]", "14")
    shot(page, "03-stock-new")
    page.click("text=Add stock item")
    page.wait_for_selector("text=Soda 350ml")
    page.click(".fab")
    page.wait_for_timeout(250)
    page.fill("[name=name]", "Potatoes")
    page.fill("[name=unit]", "kg")
    page.select_option("[name=kind]", "ingredient")
    page.fill("[name=reorder_level]", "10")
    page.fill("[name=opening_qty]", "40")
    page.click("text=Add stock item")
    page.wait_for_selector("text=Potatoes")
    shot(page, "04-stock-list")

    # menu: link soda to stock
    page.goto(BASE + "/#/menu")
    page.wait_for_selector("text=Soda 350ml")
    shot(page, "05-menu")
    page.click("button.row:has-text('Soda 350ml')")
    page.select_option("[name=stock_item_id]", label="Soda 350ml (bottles)")
    shot(page, "06-menu-item")
    page.click("text=Save item")
    page.wait_for_selector("text=Uses 1 bottles of Soda 350ml")

    # staff: add cashier
    page.goto(BASE + "/#/staff")
    page.click(".fab")
    page.wait_for_timeout(250)
    page.fill("[name=name]", "Wanjiku")
    page.fill("[name=phone]", "0722000111")
    page.fill("[name=pin]", "1111")
    page.click("text=Add staff member")
    page.wait_for_selector("text=Wanjiku")
    shot(page, "07-staff")

    # log out, log in as cashier
    page.click("[data-act=logout]")
    page.wait_for_selector(".who")
    shot(page, "08-login")
    page.click(".who button:has-text('Wanjiku')")
    for k in "1111":
        page.click(f".keypad button[data-k='{k}']")
    page.wait_for_selector("#tiles")
    shot(page, "09-sell")

    # order: chips masala + beef wet fry (ugali) + soda
    page.click(".tile:has-text('Chips Masala')")
    page.click(".tile:has-text('Beef Wet Fry')")
    page.wait_for_selector(".choice-grid")
    shot(page, "10-choice")
    page.click(".choice-grid button:has-text('Ugali')")
    page.click(".tile:has-text('Soda 350ml')")
    shot(page, "11-sell-with-cart")
    page.click(".cartbar")
    page.click("[data-act=pay][data-m=cash]")
    page.click("[data-act=cash-quick][data-v='1000']")
    shot(page, "12-cart-cash")
    page.click("[data-act=checkout]")
    page.wait_for_selector(".result")
    shot(page, "13-cash-done")
    page.click(".result [data-act=close-sheet]")

    # M-Pesa sale
    page.click(".tile:has-text('Chips Masala')")
    page.click(".tile:has-text('Beef Wet Fry')")
    page.click(".choice-grid button:has-text('Chapati')")
    page.click(".tile:has-text('Soda 350ml')")
    page.click(".cartbar")
    page.click("[data-act=pay][data-m=mpesa]")
    shot(page, "14-cart-mpesa")
    page.click("[data-act=checkout]")
    page.wait_for_selector(".spinner")
    shot(page, "15-mpesa-waiting")
    page.click("[data-act=sim-pay]")
    page.wait_for_selector("text=M-Pesa payment received", timeout=8000)
    shot(page, "16-mpesa-paid")
    page.click(".result [data-act=close-sheet]")

    # one more waiting sale + an unmatched payment for the reconciliation screen
    page.click(".tile:has-text('Pilau')")
    page.click(".cartbar")
    page.click("[data-act=pay][data-m=mpesa]")
    page.click("[data-act=checkout]")
    page.wait_for_selector(".spinner")
    page.click(".result [data-act=close-sheet]")
    page.goto(BASE + "/#/mpesa")
    page.wait_for_selector("text=Sales waiting for payment")
    page.click("[data-act=sim-open]")
    page.fill("[name=amount]", "500")
    page.click("text=Send payment")
    page.wait_for_timeout(600)
    shot(page, "17-mpesa-page")
    page.goto(BASE + "/#/sales")
    page.wait_for_selector(".list")
    shot(page, "18-my-sales")

    # back to owner
    page.click("[data-act=logout]")
    page.click(".who button:has-text('Peter')")
    for k in "1234":
        page.click(f".keypad button[data-k='{k}']")
    page.wait_for_selector(".hero")
    shot(page, "19-dashboard")
    page.screenshot(path=str(OUT / "19b-dashboard-full.png"), full_page=True)
    page.goto(BASE + "/#/stock")
    page.wait_for_selector("text=Soda 350ml")
    page.click("a.row:has-text('Soda 350ml')")
    page.wait_for_selector(".big-stat")
    shot(page, "20-stock-item")
    page.goto(BASE + "/#/more")
    page.wait_for_selector("text=M-Pesa by week")
    shot(page, "21-more")
    page.goto(BASE + "/#/sales")
    page.wait_for_selector(".list")
    page.click("button.row >> nth=0")
    page.wait_for_selector(".receipt")
    shot(page, "22-sale-detail")
    b.close()

print("ERRORS:", errors if errors else "none")
