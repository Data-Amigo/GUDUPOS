"""Browser walkthrough of the statement check (run against a fresh server + its DB path)."""
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE, DB, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
errors = []
ROOT = Path(__file__).resolve().parent.parent


def shot(page, name):
    page.wait_for_timeout(450)
    page.screenshot(path=str(OUT / f"{name}.png"))


def sell(page, item, pay):
    page.click(f".tile:has-text('{item}')")
    page.click(".cartbar")
    page.click(f"[data-act=pay][data-m={pay}]")
    page.click("[data-act=checkout]")
    page.wait_for_selector(".result")


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    page = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.wait_for_selector("form[data-form=signin]")
    page.click("[data-act=auth-mode][data-m=signup]")
    page.fill("[name=business_name]", "Gudu Bites")
    page.fill("[name=till_number]", "5123456")
    page.fill("[name=owner_name]", "Peter Gudu")
    page.fill("[name=phone]", "0712345678")
    page.fill("[name=password]", "secret123")
    page.fill("[name=pin]", "1234")
    page.fill("[name=pin2]", "1234")
    page.click("form[data-form=signup] button.btn"); page.wait_for_selector(".hero")
    page.goto(BASE + "/#/sell"); page.wait_for_selector("#tiles")
    sell(page, "Chips Masala", "mpesa"); page.click("[data-act=sim-pay]")
    page.wait_for_selector("text=M-Pesa payment received", timeout=8000); page.click(".result [data-act=close-sheet]")
    sell(page, "Pilau", "mpesa"); page.click(".result [data-act=close-sheet]")
    sell(page, "Shawarma", "mpesa"); page.click(".result [data-act=close-sheet]")
    sell(page, "Samosa", "cash"); page.click(".result [data-act=close-sheet]")
    pdf = OUT / "demo_statement.pdf"
    subprocess.run([sys.executable, str(ROOT / "tools/make_demo_statement.py"), "--db", DB, "--out", str(pdf)], check=True)
    page.goto(BASE + "/#/mpesa"); page.wait_for_selector("text=Upload statement")
    shot(page, "s1-mpesa")
    page.click("[data-act=statement-open]")
    page.set_input_files("input[name=file]", str(pdf))
    page.fill("input[name=password]", "1234")
    shot(page, "s2-upload")
    page.click("text=Check statement")
    page.wait_for_selector("text=Statement check")
    shot(page, "s3-report")
    page.screenshot(path=str(OUT / "s3b-report-full.png"), full_page=True)
    page.goto(BASE + "/#/mpesa-week"); page.wait_for_selector("text=M-Pesa by week")
    shot(page, "s4-week")
    page.screenshot(path=str(OUT / "s4b-week-full.png"), full_page=True)
    page.goto(BASE + "/#/settings"); page.wait_for_selector("text=M-Pesa live connection")
    page.screenshot(path=str(OUT / "s5-settings-full.png"), full_page=True)
    # lock and the PIN screen; then sign the phone out
    page.click("[data-act=logout]"); page.wait_for_selector(".who")
    shot(page, "s6-pin-screen")
    page.on("dialog", lambda d: d.accept())
    page.click("[data-act=signout-device]"); page.wait_for_selector("form[data-form=signin]")
    page.fill("[name=identifier]", "+254 712 345 678"); page.fill("[name=password]", "secret123")
    shot(page, "s7-signin")
    page.click("form[data-form=signin] button.btn"); page.wait_for_selector(".hero")
    b.close()
print("ERRORS:", errors or "none")
