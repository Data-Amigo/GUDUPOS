"""Starter menu taken from part of the Gudu Bites menu photo.

Only part of the menu is loaded on purpose: the owner adds the rest, sets prices and
links items to stock from the Menu screen. Staff and stock start empty.
"""
from sqlalchemy.orm import Session

from .models import Category, MenuItem

ACCOMPANIMENT = ("Accompaniment", "Ugali, Rice, Chapati")

STARTER_MENU = [
    ("Hot & Cold Beverages", [
        ("Mixed Tea", 50), ("Black Tea", 50), ("White Coffee", 60),
        ("Soda 350ml", 70), ("Soda 500ml", 100), ("Water", 50),
    ]),
    ("Snacks & Bites", [("Sausage", 100), ("Smokie", 50), ("Samosa", 50), ("Andazi", 20)]),
    ("Accompaniments", [("Ugali", 100), ("Chapati", 40), ("Plain Rice", 150)]),
    ("Chips", [("Chips Plain", 150), ("Chips Masala", 250)]),
    ("Shawarma", [("Shawarma", 300)]),
    ("Rice Dishes", [("Pilau", 350)]),
    ("Beef Dishes", [("Beef Wet Fry", 350, ACCOMPANIMENT), ("Beef Dry Fry", 350, ACCOMPANIMENT)]),
    ("Chicken Dishes", [
        ("Kienyeji Chicken (Half)", 1500, ("Style", "Dry, Wet")),
        ("Broiler Chicken Deep Fried", 200),
    ]),
]


def load_starter_menu(db: Session, business_id: int) -> None:
    for c_sort, (cat_name, items) in enumerate(STARTER_MENU):
        cat = Category(business_id=business_id, name=cat_name, sort=c_sort)
        db.add(cat)
        db.flush()
        for i_sort, item in enumerate(items):
            name, price = item[0], item[1]
            label, options = item[2] if len(item) > 2 else ("", "")
            db.add(MenuItem(business_id=business_id, category_id=cat.id, name=name, price=price, choice_label=label,
                            choice_options=options, sort=i_sort))
