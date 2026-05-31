---
title: PRESUNI BPOM
emoji: 🏛️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.15.2
python_version: '3.13'
app_file: app.py
pinned: false
---

<div align="center">

# 🏛️ BPOM Compliance AI System

**Sistem Cerdas Pemeriksaan Kepatuhan Registrasi Produk Pangan Berbasis AI**

[![Hugging Face Space](https://img.shields.io/badge/🤗%20Demo-Hugging%20Face%20Space-blue)](https://huggingface.co/spaces/Expanic/PRESUNI_BPOM)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-UI-orange?logo=gradio)](https://gradio.app)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-4285F4?logo=google&logoColor=white)](https://ai.google.dev)

[**🚀 Coba Demo Langsung**](https://huggingface.co/spaces/Expanic/PRESUNI_BPOM) · [**📘 Blueprint Teknis**](./blueprint.md) · [**🧪 Contoh Test Case**](./TEST_CASES.md)

</div>

---

## 📋 Apa Itu Aplikasi Ini?

**BPOM Compliance AI** adalah aplikasi berbasis web yang secara otomatis memeriksa apakah produk pangan/suplemen memenuhi standar keamanan **BPOM (Badan Pengawas Obat dan Makanan)** Republik Indonesia.

Pengguna cukup meng-upload **laporan uji laboratorium** (PDF/DOCX) atau mengetik data hasil uji secara manual, lalu sistem akan:

1. 🔍 **Mengekstrak** data cemaran mikroba, logam berat, dan informasi produk secara otomatis
2. 🏷️ **Mengklasifikasi** kategori produk (Suplemen, Dairy, Daging Olahan, Buah & Sayur)
3. ⚖️ **Memeriksa kepatuhan** setiap parameter secara deterministik terhadap ambang batas resmi BPOM
4. 🤖 **Menjelaskan** hasil pelanggaran dalam bahasa Indonesia yang mudah dipahami menggunakan AI (Gemini)
5. 📄 **Menghasilkan laporan** final dalam format PDF yang siap cetak

### Arsitektur Hybrid: Rule-Based + AI

| Komponen | Metode | Kenapa? |
|---|---|---|
| Pengecekan Lulus/Gagal | **Rule-Based (Deterministik)** | Kepastian hukum mutlak — tidak boleh ada halusinasi AI |
| Klasifikasi Produk | **Hybrid (Keyword + LLM Fallback)** | Keyword matching cepat, LLM hanya dipanggil jika ambigu |
| Penjelasan Pelanggaran | **RAG + LLM (Gemini)** | Menjelaskan mengapa gagal, lengkap dengan pasal hukum |
| Referensi Hukum | **Vector DB (ChromaDB)** | Semantic search ke dokumen peraturan BPOM asli |

---

## 📚 Dasar Regulasi BPOM

Seluruh ambang batas dan aturan dalam sistem ini **bersumber langsung dari peraturan resmi BPOM** yang diunduh dari [JDIH BPOM](https://jdih.pom.go.id/):

| Peraturan | Ruang Lingkup | Digunakan Untuk |
|---|---|---|
| **PerBPOM No. 13 Tahun 2019** | Batas Maksimal Cemaran Mikroba dalam Pangan Olahan | Pengecekan ALT, Coliform, E.coli, Salmonella, S.aureus, Kapang/Khamir, B.cereus |
| **PerBPOM No. 9 Tahun 2022** | Persyaratan Cemaran Logam Berat dalam Pangan Olahan | Pengecekan Timbal (Pb), Kadmium (Cd), Merkuri (Hg), Arsen (As) |
| **PerBPOM No. 22 Tahun 2021** | Cara Produksi Pangan Olahan yang Baik (CPPOB) | Checklist sanitasi, higiene, penyimpanan, dan transportasi |

### Kategori Produk yang Didukung

| Kategori | Contoh Produk |
|---|---|
| `SUPLEMEN` | Suplemen kesehatan, multivitamin, herbal kapsul |
| `DAIRY` | Susu UHT, yoghurt, keju olahan |
| `DAGING_OLAHAN` | Sosis, nugget, kornet, bakso kemasan |
| `BUAH_SAYUR` | Jus buah kemasan, sayur beku, manisan buah |

---

## 🚀 Cara Menggunakan

### Opsi 1: Langsung Coba Online (Tanpa Install)

Buka demo yang sudah di-deploy di Hugging Face Spaces:

👉 **[https://huggingface.co/spaces/Expanic/PRESUNI_BPOM](https://huggingface.co/spaces/Expanic/PRESUNI_BPOM)**

---

### Opsi 2: Jalankan Sendiri di Lokal

#### Prasyarat
- Python 3.9 atau lebih baru
- API Key Google Gemini (gratis)

#### Step 1: Clone Repository

```bash
git clone https://github.com/Expanics/PRESUNIV_BPOM.git
cd PRESUNIV_BPOM
```

#### Step 2: Buat Virtual Environment & Install Dependencies

```bash
python -m venv venv
source venv/bin/activate        # Mac / Linux
# venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

#### Step 3: Dapatkan API Key dari Google AI Studio

1. Buka **[Google AI Studio](https://aistudio.google.com/apikey)**
2. Klik **"Create API Key"**
3. Copy API Key yang dihasilkan (format: `AIzaSy...`)

#### Step 4: Buat File `.env`

Buat file `.env` di root project:

```bash
echo "GEMINI_API_KEY=PASTE_API_KEY_KAMU_DISINI" > .env
```

Contoh isi `.env`:
```env
GEMINI_API_KEY=AIzaSyC1234567890abcdefghijklmnop
```

> ⚠️ **Jangan commit file `.env` ke GitHub!** File ini berisi API key pribadi kamu.

#### Step 5: (Opsional) Update Database Regulasi

Jika kamu menambahkan PDF regulasi BPOM baru ke folder `data/regulations/`, jalankan:

```bash
python src/ingest.py
```

#### Step 6: Jalankan Aplikasi

```bash
python src/app.py
```

Buka browser di **[http://127.0.0.1:7860](http://127.0.0.1:7860)** 🎉

---

## 🧪 Cara Mencoba / Test Case

Tersedia **3 skenario pengujian** di file [`TEST_CASES.md`](./TEST_CASES.md) yang bisa langsung di-copy-paste ke dalam aplikasi:

| No | Skenario | Deskripsi | Hasil yang Diharapkan |
|----|----------|-----------|----------------------|
| 1 | **Full Approve** ✅ | Semua parameter lolos | Semua PASS, narasi positif |
| 2 | **Partial Violations** ⚠️ | Coliform, Kapang, Timbal, Arsen melebihi batas | 4 parameter FAIL, sisanya PASS |
| 3 | **Full Fail** ❌ | Semua cemaran gagal + klaim obat ilegal | Semua FAIL + peringatan klaim terlarang |

### Cara Coba:
1. Buka aplikasi → Tab **"1. 📥 Input Dokumen"**
2. Buka file [`TEST_CASES.md`](./TEST_CASES.md), copy salah satu blok teks
3. Paste ke area **"Atau Masukkan Teks Manual"**
4. Klik **"🔍 Analisis Dokumen"**
5. Cek hasilnya di Tab **"2. 📋 Review Hasil AI"**
6. Klik **"✅ Setuju & Buat Laporan Final"** untuk generate laporan PDF

---

## 🏗️ Struktur Project

```
PRESUNIV_BPOM/
├── app.py                  # Entry point (untuk Hugging Face Spaces)
├── requirements.txt        # Daftar library Python
├── .env                    # API Key Gemini (JANGAN di-commit)
├── blueprint.md            # Dokumentasi teknis lengkap
├── TEST_CASES.md           # Contoh data input untuk pengujian
│
├── src/                    # Source code utama
│   ├── app.py              # UI Gradio & state management
│   ├── extractor.py        # Ekstraktor teks → JSON (Regex + OCR)
│   ├── classifier.py       # Klasifikasi kategori produk
│   ├── rule_engine.py      # Core: pengecekan PASS/FAIL deterministik
│   ├── rag_query.py        # Semantic search ke ChromaDB
│   ├── llm_narrator.py     # Narasi penjelasan AI (Gemini)
│   ├── report_generator.py # Generator laporan PDF & Markdown
│   └── ingest.py           # Ingest regulasi PDF ke vector DB
│
├── rules/                  # Ambang batas BPOM (JSON)
│   ├── microba_rules.json  # PerBPOM No. 13/2019 — Cemaran Mikroba
│   ├── logam_berat_rules.json  # PerBPOM No. 9/2022 — Logam Berat
│   └── cppob_rules.json    # PerBPOM No. 22/2021 — CPPOB
│
├── data/regulations/       # PDF peraturan BPOM asli (dari JDIH)
│   ├── SUPLEMEN/
│   ├── DAIRY/
│   ├── DAGING_OLAHAN/
│   └── BUAH_SAYUR/
│
├── chroma_db/              # Vector database (auto-generated)
└── prompts/                # Template prompt untuk LLM
```

---

## ⚙️ Tech Stack

| Komponen | Teknologi |
|---|---|
| **UI / Frontend** | Gradio |
| **Generative AI** | Google Gemini 1.5 Flash |
| **Vector Database** | ChromaDB (Persistent) |
| **Embedding** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| **Ekstraksi PDF** | pdfplumber + pytesseract (OCR fallback) |
| **Ekstraksi DOCX** | python-docx |
| **Laporan PDF** | FPDF2 |

---

## 🔒 Keamanan & Privasi Data

- **Proses Rule-Based** berjalan 100% lokal — data TIDAK dikirim ke server manapun
- **Proses AI (narasi)** mengirim ringkasan data ke Google Gemini API
- Untuk kebutuhan enterprise/rahasia: ganti Gemini dengan LLM open-source lokal (misal Llama 3)

---

## 📖 Dokumentasi Lengkap

Untuk memahami arsitektur, schema data, workflow tiap modul, dan cara menambahkan kategori produk baru, baca dokumentasi teknis lengkap di:

👉 [**blueprint.md**](./blueprint.md)

---

## 📝 Lisensi

Project ini dibuat untuk keperluan akademis Universitas Presiden (*President University*).

---

<div align="center">

**Dibuat dengan ❤️ untuk keamanan pangan Indonesia**

*Seluruh aturan bersumber dari [JDIH BPOM](https://jdih.pom.go.id/) — Badan Pengawas Obat dan Makanan Republik Indonesia*

</div>
