# Śivārpaṇa Karpura (Flask)

Two separate websites that share one database.

```
kurpura_project/
├── database/
│   ├── schema.sql      table definitions
│   └── seed.py         creates kurpura.db + products + admin login
├── user/               customer website  -> http://127.0.0.1:5000
│   ├── app.py          all pages and logic
│   ├── db.py           3 small database helpers
│   ├── templates/
│   └── static/         css, js, images
└── admin/              admin panel       -> http://127.0.0.1:5001
    ├── app.py
    ├── db.py
    ├── templates/
    └── static/
```

## Run
```
pip install -r requirements.txt
python database/seed.py     # once. It wipes and recreates the database.

cd user  && python app.py   # terminal 1
cd admin && python app.py   # terminal 2
```
Admin login: admin@sivarpana.com / admin123

Before going live: set a strong password with `ADMIN_PASSWORD=YourPass python database/seed.py`
and change `app.secret_key` in both app.py files.
