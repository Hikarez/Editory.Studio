"""Editory Studio: company profile, generator proposal penawaran, dan dashboard target."""
import json
import math
import os
import re
import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_file, session, url_for)

from pdf_proposal import build_proposal_pdf
from utils import add_months, bulan_singkat, bulan_tahun, rupiah, tanggal, valid_until

BASE_DIR = Path(__file__).resolve().parent
CONTENT_FILE = BASE_DIR / "data" / "content.json"
DB_FILE = Path(os.environ.get("EDITORY_DB", BASE_DIR / "instance" / "editory.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "ganti-dengan-secret-key-sendiri")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "editory123")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATUSES = {"draft": "Draft", "dikirim": "Dikirim", "deal": "Deal", "batal": "Batal"}
MAX_QTY = 24
MAX_DISCOUNT = 50

app.jinja_env.filters["rupiah"] = rupiah
app.jinja_env.filters["tanggal"] = tanggal


# ---------------------------------------------------------------- konten

def load_content():
    """Konten dibaca ulang tiap request, jadi edit data/content.json langsung terlihat."""
    with CONTENT_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


def find_package(content, package_id):
    return next((pkg for pkg in content["packages"] if pkg["id"] == package_id), None)


@app.context_processor
def inject_globals():
    return {"brand": load_content()["brand"], "current_year": date.today().year,
            "is_admin": session.get("admin", False), "statuses": STATUSES}


# ---------------------------------------------------------------- database

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    service TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    client_company TEXT NOT NULL,
    client_name TEXT NOT NULL,
    client_email TEXT,
    package_id TEXT NOT NULL,
    package_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    unit_label TEXT NOT NULL,
    qty INTEGER NOT NULL,
    unit_price INTEGER NOT NULL,
    discount INTEGER NOT NULL DEFAULT 0,
    total INTEGER NOT NULL,
    start_date TEXT,
    needs TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
"""


def get_db():
    if "db" not in g:
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        db.commit()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def next_code(db):
    prefix = f"EDT-{date.today().year}-"
    row = db.execute("SELECT code FROM proposals WHERE code LIKE ? ORDER BY id DESC LIMIT 1",
                     (prefix + "%",)).fetchone()
    number = int(row["code"].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{prefix}{number:03d}"


def calc_total(price, qty, discount):
    return price * qty * (100 - discount) // 100


def insert_proposal(db, data, pkg, qty, discount, status="draft"):
    code = next_code(db)
    db.execute(
        """INSERT INTO proposals (code, client_company, client_name, client_email, package_id,
               package_name, unit, unit_label, qty, unit_price, discount, total, start_date,
               needs, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (code, data["client_company"], data["client_name"], data.get("client_email", ""),
         pkg["id"], pkg["name"], pkg["unit"], pkg["unit_label"], qty, pkg["price"], discount,
         calc_total(pkg["price"], qty, discount), data.get("start_date") or None,
         data.get("needs", ""), status, now_iso()))
    db.commit()
    return code


def get_proposal_or_404(code):
    row = get_db().execute("SELECT * FROM proposals WHERE code = ?", (code,)).fetchone()
    if row is None:
        abort(404)
    return row


# ---------------------------------------------------------------- halaman publik

@app.route("/")
def index():
    c = load_content()
    return render_template("index.html", services=c["services"], packages=c["packages"],
                           portfolio=c["portfolio"][:3], process=c["process"])


@app.route("/tentang")
def tentang():
    c = load_content()
    return render_template("tentang.html", about=c["about"], team=c["team"])


@app.route("/layanan")
def layanan():
    c = load_content()
    return render_template("layanan.html", services=c["services"], packages=c["packages"],
                           process=c["process"], faq=c["faq"])


@app.route("/portofolio")
def portofolio():
    items = load_content()["portfolio"]
    categories = sorted({item["category"] for item in items})
    active = request.args.get("kategori", "")
    if active:
        items = [item for item in items if item["category"] == active]
    return render_template("portofolio.html", items=items, categories=categories, active=active)


@app.route("/kontak", methods=["GET", "POST"])
def kontak():
    c = load_content()
    form, errors = {}, {}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in ("name", "email", "service", "message")}
        if not form["name"]:
            errors["name"] = "Nama wajib diisi."
        if not EMAIL_RE.match(form["email"]):
            errors["email"] = "Masukkan alamat email yang valid."
        if len(form["message"]) < 10:
            errors["message"] = "Ceritakan kebutuhanmu minimal 10 karakter."
        if not errors:
            db = get_db()
            db.execute("INSERT INTO messages (name, email, service, message, created_at) "
                       "VALUES (?, ?, ?, ?, ?)",
                       (form["name"], form["email"], form["service"], form["message"], now_iso()))
            db.commit()
            flash("Pesan terkirim. Kami balas lewat email dalam 1x24 jam pada hari kerja.", "success")
            return redirect(url_for("kontak"))
    return render_template("kontak.html", form=form, errors=errors, packages=c["packages"])


# ---------------------------------------------------------------- proposal

@app.route("/proposal", methods=["GET", "POST"])
def proposal_form():
    c = load_content()
    default_pkg = request.args.get("paket") or c["packages"][1]["id"]
    form = {"package_id": default_pkg, "qty": "1", "discount": "0"}
    errors = {}
    if request.method == "POST":
        fields = ("client_company", "client_name", "client_email", "package_id", "qty",
                  "start_date", "needs", "discount")
        form = {k: request.form.get(k, "").strip() for k in fields}
        pkg = find_package(c, form["package_id"])

        if not form["client_company"]:
            errors["client_company"] = "Nama usaha atau akun wajib diisi."
        if not form["client_name"]:
            errors["client_name"] = "Nama penanggung jawab wajib diisi."
        if form["client_email"] and not EMAIL_RE.match(form["client_email"]):
            errors["client_email"] = "Format email tidak valid."
        if pkg is None:
            errors["package_id"] = "Pilih salah satu paket."
        try:
            qty = int(form["qty"])
            if not 1 <= qty <= MAX_QTY:
                raise ValueError
        except ValueError:
            qty = 0
            errors["qty"] = f"Isi angka 1 sampai {MAX_QTY}."
        discount = 0
        if session.get("admin"):
            try:
                discount = int(form["discount"] or 0)
                if not 0 <= discount <= MAX_DISCOUNT:
                    raise ValueError
            except ValueError:
                errors["discount"] = f"Diskon 0 sampai {MAX_DISCOUNT} persen."
        if form["start_date"]:
            try:
                date.fromisoformat(form["start_date"])
            except ValueError:
                errors["start_date"] = "Tanggal tidak valid."

        if not errors:
            code = insert_proposal(get_db(), form, pkg, qty, discount)
            flash("Proposal berhasil dibuat. Unduh PDF atau salin link untuk dikirim.", "success")
            return redirect(url_for("proposal_view", code=code))
    return render_template("proposal_form.html", packages=c["packages"], form=form, errors=errors,
                           max_qty=MAX_QTY, max_discount=MAX_DISCOUNT)


@app.route("/proposal/<code>")
def proposal_view(code):
    c = load_content()
    p = get_proposal_or_404(code)
    return render_template("proposal_view.html", p=p, pkg=find_package(c, p["package_id"]),
                           process=c["process"], terms=c["proposal_terms"],
                           subtotal=p["unit_price"] * p["qty"],
                           valid_until=valid_until(p["created_at"]),
                           share_url=url_for("proposal_view", code=code, _external=True))


@app.route("/proposal/<code>/pdf")
def proposal_pdf(code):
    c = load_content()
    p = get_proposal_or_404(code)
    pdf = build_proposal_pdf(p, find_package(c, p["package_id"]), c)
    return send_file(pdf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"Proposal-{code}-Editory-Studio.pdf")


# ---------------------------------------------------------------- target Rp1 miliar

def monthly_schedule(content):
    """Daftar omzet rencana untuk tiap bulan selama periode target."""
    prices = {pkg["id"]: pkg["price"] for pkg in content["packages"]}
    schedule = []
    for phase in content["target"]["plan"]:
        monthly = sum(prices[pid] * n for pid, n in phase["clients"].items())
        schedule += [monthly] * phase["months"]
    return schedule


def build_plan(content):
    t = content["target"]
    packages = {pkg["id"]: pkg for pkg in content["packages"]}
    start = date.fromisoformat(t["start"])
    rows, cumulative, cursor = [], 0, 0
    for phase in t["plan"]:
        clients = phase["clients"].items()
        monthly = sum(packages[pid]["price"] * n for pid, n in clients)
        videos = sum(packages[pid]["videos_per_unit"] * n for pid, n in clients)
        total = monthly * phase["months"]
        cumulative += total
        first, last = add_months(start, cursor), add_months(start, cursor + phase["months"] - 1)
        cursor += phase["months"]
        rows.append({
            "phase": phase["phase"],
            "period": f"{bulan_singkat(first)} \u2013 {bulan_singkat(last)}",
            "clients": [(packages[pid]["name"], n) for pid, n in clients],
            "monthly": monthly, "total": total, "cumulative": cumulative,
            "cumulative_pct": min(cumulative / t["amount"] * 100, 100),
            "videos": videos, "editors": math.ceil(videos / t["editor_capacity"]),
            "focus": phase["focus"],
        })
    return rows


def target_progress(content):
    t = content["target"]
    amount, months = t["amount"], t["months"]
    start, today = date.fromisoformat(t["start"]), date.today()
    elapsed = 0 if today < start else min(
        (today.year - start.year) * 12 + today.month - start.month + 1, months)

    db = get_db()
    achieved = db.execute("SELECT COALESCE(SUM(total), 0) FROM proposals WHERE status = 'deal'").fetchone()[0]
    pipeline = db.execute("SELECT COALESCE(SUM(total), 0) FROM proposals WHERE status = 'dikirim'").fetchone()[0]
    planned_to_date = sum(monthly_schedule(content)[:elapsed])
    months_left = months - max(elapsed - 1, 0)  # termasuk bulan berjalan
    remaining = max(amount - achieved, 0)
    return {
        "amount": amount, "achieved": achieved, "pipeline": pipeline,
        "percent": min(achieved / amount * 100, 100) if amount else 0,
        "planned_to_date": planned_to_date,
        "planned_pct": min(planned_to_date / amount * 100, 100) if amount else 0,
        "gap": planned_to_date - achieved,
        "remaining": remaining, "months": months, "elapsed": elapsed,
        "months_left": months_left,
        "needed_per_month": remaining / months_left if months_left else remaining,
        "start_label": bulan_tahun(start),
        "end_label": bulan_tahun(add_months(start, months - 1)),
    }


# ---------------------------------------------------------------- admin

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password", "") == ADMIN_PASSWORD:
            session["admin"] = True
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("admin"))
        error = "Kata sandi salah."
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    flash("Kamu sudah keluar dari dashboard.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin():
    db = get_db()
    return render_template(
        "admin.html",
        proposals=db.execute("SELECT * FROM proposals ORDER BY id DESC").fetchall(),
        messages=db.execute("SELECT * FROM messages ORDER BY id DESC").fetchall(),
        progress=target_progress(load_content()))


@app.route("/admin/proposal/<code>/status", methods=["POST"])
@admin_required
def update_status(code):
    status = request.form.get("status", "")
    if status not in STATUSES:
        abort(400)
    get_proposal_or_404(code)
    db = get_db()
    db.execute("UPDATE proposals SET status = ? WHERE code = ?", (status, code))
    db.commit()
    flash(f"Status {code} diubah menjadi {STATUSES[status]}.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/target")
@admin_required
def admin_target():
    c = load_content()
    t = c["target"]
    assumptions = [
        "Harga paket tetap selama dua tahun.",
        "Klien aktif adalah klien yang membayar pada bulan tersebut. Klien paket bulanan diasumsikan memperpanjang kontrak.",
        f"Satu editor mampu menangani sekitar {t['editor_capacity']} video per bulan.",
        "Target dihitung sebagai omzet (pendapatan kotor), belum dikurangi gaji, iklan, software, dan biaya operasional lain.",
        "Progres di dashboard memakai nilai kontrak proposal berstatus Deal.",
    ]
    return render_template("admin_target.html", progress=target_progress(c), plan=build_plan(c),
                           assumptions=assumptions)


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.cli.command("seed-demo")
def seed_demo():
    """Isi database dengan proposal dan pesan contoh untuk keperluan demo."""
    c = load_content()
    db = get_db()
    samples = [
        ("Kedai Kopi Contoh", "Rina", "content-creator", 6, 0, "deal"),
        ("Toko Hijab Contoh", "Dewi", "brand-partner", 3, 10, "deal"),
        ("Kreator Travel Contoh", "Bima", "reels-starter", 5, 0, "dikirim"),
        ("Klinik Kecantikan Contoh", "Sari", "content-creator", 3, 0, "draft"),
    ]
    for company, name, pid, qty, discount, status in samples:
        insert_proposal(db, {"client_company": company, "client_name": name,
                             "needs": "Data contoh untuk demo dashboard."},
                        find_package(c, pid), qty, discount, status)
    db.execute("INSERT INTO messages (name, email, service, message, created_at) VALUES (?, ?, ?, ?, ?)",
               ("Andi (contoh)", "andi@example.com", "Reels Starter",
                "Halo, saya ingin tanya untuk 3 video promo produk bulan depan.", now_iso()))
    db.commit()
    print("Data contoh ditambahkan.")


init_db()

if __name__ == "__main__":
    app.run(debug=True)
