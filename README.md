# Editory Studio — Company Profile dan Generator Proposal (Flask)

Website company profile untuk **Editory Studio**, studio editing video dan konten media sosial, lengkap dengan generator proposal penawaran PDF dan dashboard target omzet Rp1 miliar dalam 2 tahun.

## Fitur

| Halaman | Fungsi |
|---|---|
| `/` | Beranda: hero, layanan, karya pilihan, alur kerja, paket |
| `/tentang` | Cerita, visi misi, prinsip kerja, tim |
| `/layanan` | Tiga paket lengkap, cakupan layanan, alur kerja, FAQ |
| `/portofolio` | Daftar karya dengan filter kategori |
| `/kontak` | Form kontak (tersimpan ke SQLite) |
| `/proposal` | Form generator proposal dengan estimasi harga langsung |
| `/proposal/<kode>` | Halaman proposal yang bisa dibagikan lewat link |
| `/proposal/<kode>/pdf` | Unduh proposal sebagai PDF |
| `/admin` | Dashboard: daftar proposal, ubah status, pesan masuk, progres target |
| `/admin/target` | Rencana target Rp1 miliar per kuartal |

Alur bisnisnya: calon klien membuat proposal (status **Draft**), admin mengirimkannya (**Dikirim**), lalu saat klien setuju statusnya diubah menjadi **Deal**. Nilai proposal berstatus Deal otomatis dihitung ke progres target.

## Cara menjalankan

Butuh Python 3.10 atau lebih baru.

```bash
cd editory_studio
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Buka http://127.0.0.1:5000

Database SQLite dibuat otomatis di `instance/editory.db`.

### Data contoh (opsional, untuk demo)

```bash
flask --app app seed-demo
```

Perintah ini menambahkan 4 proposal dan 1 pesan contoh agar dashboard tidak kosong saat presentasi. Untuk mengulang dari nol, hapus file `instance/editory.db`.

## Login admin

Buka `/admin`, kata sandi bawaan: **editory123**.

Ganti lewat environment variable sebelum menjalankan:

```bash
# macOS/Linux
export ADMIN_PASSWORD="sandi-baru"
export SECRET_KEY="kunci-acak-panjang"
# Windows (PowerShell)
$env:ADMIN_PASSWORD="sandi-baru"
```

Admin juga bisa memberi diskon (0 sampai 50%) saat membuat proposal; pengunjung biasa tidak.

## Mengubah isi website

Semua teks, harga paket, portofolio, tim, FAQ, ketentuan proposal, dan rencana target ada di **`data/content.json`**. Edit file itu lalu muat ulang halaman, tidak perlu mengubah template atau restart server.

Yang perlu diganti dengan data asli:

- `team[].name` masih berisi "Nama Anggota".
- `portfolio` berisi proyek contoh. Ganti dengan karya asli bila ada.

## Target Rp1 miliar dalam 2 tahun

Rata-rata yang dibutuhkan sekitar Rp41,7 juta per bulan. Rencananya naik bertahap, dari sekitar Rp10 juta per bulan di kuartal 1 sampai sekitar Rp68,6 juta per bulan di kuartal 8, dengan total proyeksi Rp1.004.250.000.

Asumsi: harga paket tetap, klien bulanan memperpanjang kontrak, satu editor menangani sekitar 45 video per bulan. Angka ini **omzet**, belum dikurangi biaya operasional. Jumlah klien per kuartal bisa diubah di `target.plan` pada `data/content.json`, dan tabel proyeksi akan menghitung ulang otomatis.

## Struktur folder

```
editory_studio/
├── app.py              # route, database, logika target
├── pdf_proposal.py     # pembuatan PDF proposal (ReportLab)
├── utils.py            # format rupiah dan tanggal
├── data/content.json   # seluruh konten website
├── templates/          # template Jinja2
├── static/css, js, img
└── requirements.txt
```

## Teknologi

Flask 3, Jinja2, SQLite (bawaan Python), ReportLab untuk PDF, CSS dan JavaScript tanpa framework.
