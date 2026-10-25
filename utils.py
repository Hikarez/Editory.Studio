"""Fungsi bantu format yang dipakai di template dan PDF."""
from datetime import date, datetime, timedelta

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
MASA_BERLAKU_HARI = 14


def rupiah(value):
    """1200000 -> 'Rp1.200.000'."""
    return "Rp" + f"{int(round(value or 0)):,}".replace(",", ".")


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value).date()
    return None


def tanggal(value):
    """'2026-10-25T11:04:00' -> '25 Oktober 2026'."""
    d = to_date(value)
    return f"{d.day} {BULAN[d.month - 1]} {d.year}" if d else ""


def bulan_singkat(d):
    return f"{BULAN[d.month - 1][:3]} {d.year}"


def bulan_tahun(d):
    return f"{BULAN[d.month - 1]} {d.year}"


def add_months(d, n):
    """Tanggal 1 pada bulan ke-n setelah d."""
    year, month = divmod(d.month - 1 + n, 12)
    return date(d.year + year, month + 1, 1)


def valid_until(created_at):
    return to_date(created_at) + timedelta(days=MASA_BERLAKU_HARI)
