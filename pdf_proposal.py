"""Membuat PDF proposal penawaran dengan ReportLab."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from utils import rupiah, tanggal, valid_until

BRAND = colors.HexColor("#4B3BA8")
TEAL = colors.HexColor("#2A9D8F")
AMBER = colors.HexColor("#E3A03A")
INK = colors.HexColor("#1B2030")
MUTE = colors.HexColor("#5B6275")
LINE = colors.HexColor("#DCDFE7")
SOFT = colors.HexColor("#ECE9FA")

BASE = ParagraphStyle("base", fontName="Helvetica", fontSize=10, leading=14.5, textColor=INK)
SMALL = ParagraphStyle("small", parent=BASE, fontSize=8.8, leading=12, textColor=MUTE)
BRAND_ST = ParagraphStyle("brand", parent=BASE, fontName="Helvetica-Bold", fontSize=15,
                          leading=18, textColor=BRAND)
META = ParagraphStyle("meta", parent=SMALL, alignment=TA_RIGHT, textColor=INK)
TITLE = ParagraphStyle("title", parent=BASE, fontName="Helvetica-Bold", fontSize=19,
                       leading=23, spaceBefore=2, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=BASE, fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                    textColor=BRAND, spaceBefore=14, spaceAfter=5)
TH = ParagraphStyle("th", parent=SMALL, fontName="Helvetica-Bold")
TH_R = ParagraphStyle("thr", parent=TH, alignment=TA_RIGHT)
RIGHT = ParagraphStyle("right", parent=BASE, alignment=TA_RIGHT)
RIGHT_B = ParagraphStyle("rightb", parent=RIGHT, fontName="Helvetica-Bold", fontSize=11)


def esc(value):
    """Amankan teks dari input pengguna sebelum masuk ke Paragraph ReportLab."""
    return escape(str(value or "")).replace("\n", "<br/>")


def logo():
    d = Drawing(22, 18)
    d.add(Rect(0, 14, 22, 4, rx=2, ry=2, fillColor=BRAND, strokeColor=None))
    d.add(Rect(4, 7, 14, 4, rx=2, ry=2, fillColor=TEAL, strokeColor=None))
    d.add(Rect(0, 0, 18, 4, rx=2, ry=2, fillColor=AMBER, strokeColor=None))
    return d


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(text, BASE), leftIndent=12) for text in items],
        bulletType="bullet", start="•", leftIndent=12, bulletFontSize=9, bulletColor=TEAL)


def numbered(items):
    return ListFlowable(
        [ListItem(Paragraph(text, BASE), leftIndent=16) for text in items],
        bulletType="1", leftIndent=16, bulletFontName="Helvetica-Bold", bulletColor=BRAND)


def unit_note(p):
    if p["unit"] == "bulan":
        return (f"Harga paket dihitung per bulan untuk masa kontrak {p['qty']} bulan. "
                "Pembayaran dilakukan di awal setiap bulan.")
    return f"Harga dihitung per video untuk {p['qty']} video."


def build_proposal_pdf(p, pkg, content):
    """Kembalikan BytesIO berisi PDF proposal untuk satu baris tabel proposals."""
    brand = content["brand"]
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm,
                            title=f"Proposal {p['code']}", author=brand["name"])
    width = A4[0] - 40 * mm
    story = []

    # Kop
    brand_par = Paragraph(
        esc(brand["name"]) + '<br/><font size="8.8" color="#5B6275">' + esc(brand["tagline"]) + "</font>",
        BRAND_ST)
    meta_par = Paragraph(
        f"Nomor <b>{esc(p['code'])}</b><br/>Tanggal <b>{tanggal(p['created_at'])}</b><br/>"
        f"Berlaku hingga <b>{tanggal(valid_until(p['created_at']))}</b>", META)
    head = Table([[logo(), brand_par, meta_par]],
                 colWidths=[9 * mm, width * 0.55, width - 9 * mm - width * 0.55])
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (0, 0), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINE),
    ]))
    story += [head, Spacer(1, 14)]

    recipient = f"Kepada: <b>{esc(p['client_name'])}</b>, {esc(p['client_company'])}"
    if p["client_email"]:
        recipient += f" ({esc(p['client_email'])})"
    story += [Paragraph(f"Proposal Penawaran Paket {esc(p['package_name'])}", TITLE),
              Paragraph(recipient, BASE)]

    # Pendahuluan
    story += [
        Paragraph("Pendahuluan", H2),
        Paragraph(f"Terima kasih atas ketertarikan {esc(p['client_company'])} untuk bekerja sama dengan "
                  f"{esc(brand['name'])}. Berdasarkan kebutuhan yang disampaikan, kami menawarkan paket "
                  f"<b>{esc(p['package_name'])}</b> dengan rincian lingkup pekerjaan, biaya, dan ketentuan "
                  "sebagai berikut.", BASE),
        Spacer(1, 5),
        Paragraph(esc(brand["short"]), BASE),
    ]

    # Rincian biaya
    subtotal = p["unit_price"] * p["qty"]
    rows = [
        [Paragraph("Layanan", TH), Paragraph("Jumlah", TH_R), Paragraph("Harga satuan", TH_R),
         Paragraph("Subtotal", TH_R)],
        [Paragraph(f"Paket {esc(p['package_name'])}", BASE), Paragraph(f"{p['qty']} {esc(p['unit'])}", RIGHT),
         Paragraph(rupiah(p["unit_price"]), RIGHT), Paragraph(rupiah(subtotal), RIGHT)],
    ]
    if p["discount"]:
        rows.append([Paragraph(f"Diskon {p['discount']}%", BASE), "", "",
                     Paragraph("- " + rupiah(subtotal - p["total"]), RIGHT)])
    rows.append([Paragraph("<b>Total</b>", BASE), "", "", Paragraph(rupiah(p["total"]), RIGHT_B)])
    last = len(rows) - 1
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, last - 1), 0.5, LINE),
        ("LINEABOVE", (0, last), (-1, last), 1.2, INK),
        ("BACKGROUND", (0, last), (-1, last), SOFT),
        ("SPAN", (0, last), (2, last)),
    ]
    if p["discount"]:
        style.append(("SPAN", (0, 2), (2, 2)))
    price_table = Table(rows, colWidths=[width * 0.46, width * 0.16, width * 0.19, width * 0.19])
    price_table.setStyle(TableStyle(style))
    story += [Paragraph("Rincian penawaran", H2), price_table, Spacer(1, 5),
              Paragraph(unit_note(p), SMALL)]

    # Lingkup pekerjaan
    if pkg:
        story += [Paragraph("Lingkup pekerjaan", H2), bullets([esc(f) for f in pkg["features"]]),
                  Spacer(1, 5),
                  Paragraph(f"Estimasi pengerjaan: {esc(pkg['timeline'])}. Revisi: {esc(pkg['revisions'])}.",
                            BASE)]

    # Kebutuhan klien
    if p["needs"] or p["start_date"]:
        story.append(Paragraph("Kebutuhan klien", H2))
        if p["start_date"]:
            story.append(Paragraph(f"Rencana mulai: {tanggal(p['start_date'])}", BASE))
        if p["needs"]:
            story.append(Paragraph(esc(p["needs"]), BASE))

    # Alur kerja dan ketentuan
    story += [Paragraph("Alur kerja", H2),
              numbered([f"<b>{esc(s['title'])}.</b> {esc(s['desc'])}" for s in content["process"]]),
              Paragraph("Ketentuan", H2),
              bullets([esc(t) for t in content["proposal_terms"]])]

    # Penutup dan tanda tangan
    signs = Table(
        [[Paragraph("Hormat kami,", SMALL), "", Paragraph("Disetujui oleh,", SMALL)],
         [Spacer(1, 42), "", Spacer(1, 42)],
         [Paragraph(f"<b>{esc(brand['name'])}</b>", BASE), "",
          Paragraph(f"<b>{esc(p['client_name'])}</b><br/>{esc(p['client_company'])}", BASE)]],
        colWidths=[width * 0.42, width * 0.16, width * 0.42])
    signs.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEABOVE", (0, 2), (0, 2), 0.8, INK), ("LINEABOVE", (2, 2), (2, 2), 0.8, INK),
    ]))
    story.append(KeepTogether([
        Paragraph("Penutup", H2),
        Paragraph(f"Kami siap menyesuaikan penawaran ini dengan kebutuhan {esc(p['client_company'])}. "
                  f"Untuk menyetujui atau berdiskusi, hubungi kami melalui email {esc(brand['email'])} "
                  f"atau Instagram @{esc(brand['instagram'])}.", BASE),
        Spacer(1, 18), signs,
    ]))

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTE)
        canvas.drawString(20 * mm, 11 * mm,
                          f"{brand['name']}  |  {brand['email']}  |  Instagram @{brand['instagram']}")
        canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, f"{p['code']}  |  Halaman {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buf.seek(0)
    return buf
