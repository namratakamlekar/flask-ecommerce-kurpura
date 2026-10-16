import os
import sqlite3
from werkzeug.security import generate_password_hash

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, "kurpura.db")

ADMIN_EMAIL = "admin@sivarpana.com"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

categories = [
    ("Karpura", "pure-karpura.jpg"),
    ("Agarbatti & Dhoop", "sandal-agarbatti.png"),
    ("Diyas & Wicks", "clay-diyas.jpg"),
    ("Kumkum, Haldi & Chandan", "kumkum.png"),
    ("Thali & Puja Kits", "brass-puja-thali.jpg"),
    ("Gift Combos", "diwali-gift-combo.jpg"),
]

# name, hindi name, category number, price, mrp, size, image, tag, description
products = [
    ("Pure Karpura", "शुद्ध कपूर", 1, 149, 180, "100 g", "pure-karpura.jpg", "Bestseller", "Pure camphor for daily aarti. Burns cleanly and fills the home with a fresh, sacred fragrance."),
    ("Bhimsen Karpura", "भीमसेनी कपूर", 1, 399, 460, "50 g", "bhimsen-karpura.png", "Premium", "Premium Bhimseni karpura, traditionally prized for puja and aarti. Sold in a 50 g pack."),
    ("Puja Camphor Tablets", "पूजा कपूर टिकिया", 1, 99, 120, "Pack of 40", "camphor-tablets.png", "", "Convenient camphor tablets, ready to light for aarti and havan."),
    ("Sandal Agarbatti", "चंदन अगरबत्ती", 2, 79, 95, "Pack of 100", "sandal-agarbatti.png", "", "Sandalwood-scented agarbatti for a calm, fragrant puja."),
    ("Guggul Dhoop Sticks", "गुग्गुल धूप", 2, 129, 150, "Pack of 20", "guggul-dhoop.png", "New", "Guggul dhoop sticks that give a rich, traditional smoke for puja and festivals."),
    ("Clay Diyas", "मिट्टी के दीये", 3, 149, 199, "Set of 12", "clay-diyas.jpg", "Festival", "Handmade clay diyas, a set of 12 for Diwali and everyday puja."),
    ("Cotton Wicks", "रूई की बत्ती", 3, 49, 60, "Pack of 108", "cotton-wicks.jpg", "", "Soft cotton wicks, a pack of 108 for diyas and lamps."),
    ("Kumkum", "कुमकुम", 4, 59, 70, "50 g", "kumkum.png", "", "Fine kumkum for tilak and puja offerings."),
    ("Haldi Powder", "हल्दी", 4, 49, 60, "100 g", "haldi-powder.png", "", "Haldi powder for puja, rituals and auspicious occasions."),
    ("Chandan Paste", "चंदन", 4, 189, 220, "25 g", "chandan-paste.jpg", "Premium", "Fragrant chandan paste for tilak and puja."),
    ("Brass Puja Thali", "पूजा थाली", 5, 899, 1099, "10 inch", "brass-puja-thali.jpg", "Bestseller", "A 10 inch brass thali for aarti and puja offerings."),
    ("Festival Puja Kit", "त्योहार पूजा किट", 5, 549, 649, "21 items", "festival-puja-kit.jpg", "Festival", "A ready-to-use festival puja kit with the essentials in one gift box."),
    ("Diwali Gift Combo", "दिवाली गिफ्ट कॉम्बो", 6, 999, 1249, "8 items", "diwali-gift-combo.jpg", "Gift", "A thoughtful Diwali gift combo with puja essentials in a pink gift box."),
]

conn = sqlite3.connect(DB_PATH)
conn.executescript(open(os.path.join(FOLDER, "schema.sql")).read())

conn.executemany("INSERT INTO categories (name, image) VALUES (?, ?)", categories)
conn.executemany(
    "INSERT INTO products (name, name_hi, category_id, price, mrp, size, image, tag, description) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", products)
conn.execute("insert into order_items(order_id, name,price,qnt) values(2,'Pure Karpura',149,1)")
conn.execute("INSERT INTO admins (email, password_hash) VALUES (?, ?)",
             (ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD)))
conn.commit()
conn.close()

print("Database created:", DB_PATH)
print("Admin login:", ADMIN_EMAIL, "/", ADMIN_PASSWORD)
