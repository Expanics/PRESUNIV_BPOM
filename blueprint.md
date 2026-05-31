# Blueprint & Dokumentasi Teknis: BPOM Compliance AI System

Dokumen ini adalah cetak biru (*blueprint*) komprehensif dari sistem **BPOM Compliance AI**. Ditujukan untuk developer, *engineer*, atau pihak manapun yang ingin memahami arsitektur, struktur file, format data, dan logika pemrosesan secara mendalam tanpa harus membaca seluruh baris kode.

---

## 1. Arsitektur & Teknologi Utama
Sistem ini menggunakan arsitektur **Hybrid (Deterministic + AI)**.
* **Deterministic (Rule-Based)** digunakan untuk memastikan kepastian hukum yang mutlak dalam penentuan lulus/gagal.
* **AI (RAG & LLM)** digunakan hanya sebagai asisten untuk memahami konteks dokumen, mengklasifikasi produk (jika ambigu), dan menceritakan ulang hasil pelanggaran secara natural.

**Tech Stack:**
* **Antarmuka (UI):** Gradio
* **Ekstraksi Teks:** `pdfplumber` (PDF Teks), `python-docx` (Word), `pytesseract` & `pdf2image` (Fallback OCR untuk PDF gambar).
* **Klasifikasi & Narasi (Generative AI):** `google-generativeai` (Model: Gemini 1.5 Flash).
* **Vector Database (RAG):** `ChromaDB` (Persistent lokal).
* **Embedding Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
* **Pembuat Laporan:** `FPDF2` (PDF) & standar Markdown.

---

## 2. Struktur Direktori Proyek
Berikut adalah struktur lengkap proyek beserta fungsi detail tiap komponennya:

```text
bpom_compliance/
├── blueprint.md             # Dokumen teknis komprehensif ini
├── requirements.txt         # Daftar dependensi library Python
├── .env                     # Konfigurasi environment (API Key, path, dll)
├── src/                     # Folder utama *Source Code*
│   ├── app.py               # Entry point UI Gradio dan pengelola state antar modul
│   ├── extractor.py         # Ekstraktor teks ke JSON menggunakan Regex & OCR
│   ├── classifier.py        # Pengklasifikasi kategori produk (Hybrid Rule + LLM)
│   ├── rule_engine.py       # Core logika matematika penentuan PASS/FAIL
│   ├── ingest.py            # Skrip ingest regulasi PDF ke ChromaDB (Chunking)
│   ├── rag_query.py         # Modul Semantic Search mencari bukti ke ChromaDB
│   ├── llm_narrator.py      # Penyusun narasi bahasa Indonesia via Gemini
│   └── report_generator.py  # Pembangun laporan PDF menggunakan FPDF2
├── rules/                   # File JSON statis berisi ambang batas BPOM
│   ├── microba_rules.json
│   ├── logam_berat_rules.json
│   └── cppob_rules.json
├── data/regulations/        # Sumber dokumen hukum asli BPOM (PDF)
│   ├── SUPLEMEN/
│   ├── DAIRY/
│   ├── DAGING_OLAHAN/
│   └── BUAH_SAYUR/
├── chroma_db/               # (Auto-generated) Database vektor lokal Chroma
└── prompts/                 # Template prompt untuk dikirim ke LLM
    ├── classify_prompt.txt
    ├── compliance_llm_prompt.txt
    └── report_prompt.txt
```

---

## 3. Detail Workflow & Pemrosesan Modul

### A. Ekstraksi Data (`src/extractor.py`)
Menerima input PDF/DOCX/Teks, membersihkannya dari anomali format baris baru, dan menggunakan **Regular Expression (Regex)** untuk mencari parameter.
- Menangani berbagai format penulisan (misal separator titik `...`, strip `-`, atau kolon `:`).
- Otomatis memparsing angka yang menggunakan format saintifik (misal `1.2 x 10^5 CFU/g` diubah menjadi `120000.0`).
- Mendeteksi format kualitatif seperti `negatif`, `nd`, atau `< 3`.

### B. Klasifikasi Kategori (`src/classifier.py`)
Bertujuan menentukan apakah produk masuk ke kategori `SUPLEMEN`, `DAIRY`, `DAGING_OLAHAN`, atau `BUAH_SAYUR`.
1. **Tahap 1 (Rule-Based Matching)**: Teks dicocokkan dengan *Keyword Map* statis (misal: "kapsul", "vitamin" = Suplemen). Menghasilkan persentase kecocokan (*confidence score*).
2. **Tahap 2 (LLM Fallback)**: **Hanya jika** skor < 0.3 (sangat ambigu), teks dikirim ke Gemini 1.5 Flash untuk dinilai.

### C. Rule Engine & Deterministic Checking (`src/rule_engine.py`)
**Core System**. Berjalan 100% menggunakan operasi logika Python murni tanpa LLM. Mencegah AI salah menghitung angka atau berhalusinasi soal status hukum.
1. Mengekstrak ambang batas dari `rules/*.json`.
2. Jika tipe kuantitatif: membandingkan angka hasil `extractor` dengan `max` atau `min` di JSON.
3. Jika tipe kualitatif (wajib negatif): memverifikasi keberadaan kata-kata afirmatif negatif (seperti "tidak terdeteksi").
4. Mengembalikan status absolut: **PASS**, **FAIL**, atau **MISSING** (jika data lab tidak menyebutkan parameter tersebut).

### D. Data Ingestion & Chunking Regulasi (`src/ingest.py`)
Ini adalah sistem *Knowledge Base* untuk AI (RAG).
1. **Ekstraksi**: `pdfplumber` mengekstrak teks PDF regulasi.
2. **Pembersihan**: Menghapus *watermark* JDIH BPOM, memperbaiki typo OCR (contoh: "Pasa 5" -> "Pasal 5").
3. **Semantic Chunking**: Pemotongan teks **tidak sembarangan**. Sistem mendeteksi *header* `Pasal X` dan menjadikan satu pasal sebagai satu *chunk* mandiri.
4. **Overlap Size Limit**: Jika teks dalam satu pasal melampaui `500 karakter`, teks dipecah dengan `overlap 50 karakter` agar konteks kalimat tidak terputus.
5. **Penyimpanan**: Teks diubah menjadi vektor (via `MiniLM-L12-v2`) dan disimpan di `ChromaDB` dalam bentuk *collection* terpisah per kategori produk.

### E. Semantic Search RAG (`src/rag_query.py`)
Dipanggil **hanya jika** ada parameter yang "FAIL".
Sistem membangun kalimat *query* dari parameter yang melanggar (contoh: `"batas ALT Lampiran I Tabel 1"`), merubahnya menjadi vektor, dan mencari *cosine similarity* terdekat di ChromaDB untuk mengembalikan teks asli pasal tersebut sebagai referensi bukti.

### F. LLM Narrator (`src/llm_narrator.py`)
Mengambil hasil deterministik PASS/FAIL dan teks pasal hukum hasil RAG, lalu mengirimnya ke Gemini 1.5 Flash dengan `Temperature = 0.1` (Sangat Kaku). LLM dipaksa untuk **hanya merangkai kalimat penjelasan** dalam bahasa Indonesia formal, tanpa boleh mengubah kesimpulan "Lulus/Gagal".

---

## 4. Format Data (Schema)

Bagian ini krusial agar developer lain dapat memahami struktur data yang dioper antar fungsi.

### A. Format Output Extractor (JSON Dictionary)
Data mentah yang dihasilkan oleh `extractor.py` untuk dioper ke fungsi selanjutnya:
```json
{
  "nama_produk": "Vita-X Suplemen Vitamin C",
  "perusahaan": "PT Maju Sehat",
  "tanggal_uji": "2024-03-15",
  "komposisi": "Vitamin C 500mg, Zinc",
  "klaim": "Meningkatkan daya tahan tubuh",
  "proses": "Pencampuran mekanis",
  "mikroba": {
    "ALT": 2500000.0,
    "E_coli": "negatif",
    "Kapang": 500.0
  },
  "logam_berat": {
    "Timbal_Pb": 3.5,
    "Kadmium_Cd": 0.8
  },
  "cppob": {
    "sanitasi_fasilitas": true,
    "hygiene_personel": true
  }
}
```

### B. Format File Aturan (rules/*.json)
Blueprint dari aturan yang mendasari `rule_engine.py`. Harus dikembangkan sesuai format ini jika BPOM mengeluarkan regulasi baru.

**Contoh `microba_rules.json`:**
```json
{
  "regulation": "PerBPOM No. 13 Tahun 2019",
  "categories": {
    "SUPLEMEN": {
      "ALT": {"max": 100000.0, "unit": "CFU/g", "pasal": "Lampiran I Tabel 1"},
      "E_coli": {"required": "negatif", "unit": "/g", "pasal": "Lampiran I Tabel 1"}
    }
  }
}
```

**Contoh `cppob_rules.json`:**
```json
{
  "regulation": "Peraturan BPOM Nomor 22 Tahun 2021",
  "checklist": [
    {"id": "sanitasi_fasilitas", "label": "Fasilitas memenuhi standar sanitasi", "pasal": "Pasal 12"},
    {"id": "storage_suhu", "label": "Penyimpanan pada suhu sesuai", "pasal": "Pasal 14"}
  ]
}
```

### C. Format Output Rule Engine (Compliance Result)
Hasil pemrosesan deterministik yang akan dikonsumsi oleh UI dan LLM Narrator:
```json
{
  "overall_status": "FAIL",
  "total_checks": 15,
  "violation_count": 2,
  "violations": [
    {
      "param": "ALT",
      "status": "FAIL",
      "found": 2500000.0,
      "threshold_max": 100000.0,
      "unit": "CFU/g",
      "pasal": "Lampiran I Tabel 1",
      "regulation": "PerBPOM No. 13 Tahun 2019",
      "message": "ALT = 2500000.0 CFU/g MELEBIHI batas maksimum 100000.0 CFU/g ❌"
    }
  ],
  "passed": [ ... ],
  "missing": [ ... ]
}
```

### D. Format Schema Vector Database (ChromaDB Metadata)
Setiap chunk dokumen yang di-ingest membawa *metadata* tersembunyi sebagai berikut untuk pelacakan:
```json
{
  "source": "peraturan_bpom_13_2019.pdf",
  "pasal": "Pasal 14 Ayat 2",
  "halaman_start": 21,
  "halaman_end": 21,
  "kategori": "SUPLEMEN"
}
```

---

## 5. Panduan Cara Menjalankan Aplikasi

**A. Instalasi & Setup**
1. Pastikan Python 3.9+ terinstal.
2. Buat virtual environment dan install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Set API Key Gemini di `.env`: `GEMINI_API_KEY=AIzaSy...`

**B. (Opsional) Memperbarui Database Hukum BPOM**
Jika ada dokumen PDF hukum baru yang diletakkan di `data/regulations/`, jalankan script ini agar AI membaca dan menyimpannya:
```bash
python src/ingest.py
```

**C. Menjalankan Server Utama UI (Gradio)**
```bash
python src/app.py
```
Aplikasi akan berjalan pada alamat lokal `http://127.0.0.1:7860`.

---

## 6. Sumber Data & Provenance Aturan BPOM
Aplikasi ini secara ketat bergantung pada standar hukum yang berlaku di Indonesia.
- **Sumber Utama Dokumen Hukum**: Seluruh file PDF yang disimpan di dalam `data/regulations/` wajib diunduh secara resmi dari **JDIH BPOM** (Jaringan Dokumentasi dan Informasi Hukum Badan Pengawas Obat dan Makanan) melalui portal resmi: [https://jdih.pom.go.id/](https://jdih.pom.go.id/). Hal ini untuk menghindari masuknya pasal palsu ke dalam sistem RAG.
- **Validitas Rule Engine**: Angka ambang batas (`max`/`min`/`required`) yang tersimpan di `rules/*.json` disalin langsung secara presisi dari lampiran peraturan BPOM terbaru (seperti Lampiran I PerBPOM No. 13 Tahun 2019 tentang Cemaran Mikroba).

## 7. Skalabilitas & Cara Penambahan Kategori Baru
Sistem dirancang secara modular agar siap dikembangkan di masa depan tanpa harus merombak *core engine*. Jika ingin menambahkan kategori produk baru (misal: `KOSMETIK` atau `OBAT_TRADISIONAL`), *engineer* cukup melakukan 4 langkah ini:
1. **Memperbarui Classifier**: Menambahkan daftar *keyword* untuk kategori baru di file `src/classifier.py` pada *dictionary* `KEYWORD_MAP`.
2. **Memperbarui Aturan Batas**: Menambahkan blok konfigurasi JSON untuk kategori baru tersebut di dalam file `rules/microba_rules.json` dan `rules/logam_berat_rules.json`.
3. **Menyiapkan Regulasi PDF**: Membuat subfolder baru (misal: `data/regulations/KOSMETIK/`) dan memasukkan PDF aturan BPOM terkait ke dalamnya.
4. **Sinkronisasi Vector DB**: Menambahkan nama *collection* baru di `src/ingest.py` (pada bagian `CATEGORY_MAP`), lalu menjalankan `python src/ingest.py` agar ChromaDB melakukan *embedding* pada regulasi baru tersebut.

## 8. Penanganan Error & Fallback (Resiliensi Sistem)
Aplikasi ini bersifat *fault-tolerant*. Kegagalan pada satu komponen tidak akan mematikan seluruh sistem (*graceful degradation*):
- **Kegagalan Pembacaan PDF (PDF merupakan hasil scan/gambar)**: Jika modul pembaca *text layer* (`pdfplumber`) gagal atau tidak mendeteksi teks sama sekali, sistem secara otomatis mengaktifkan *pipeline* OCR (`pytesseract`).
- **API Gemini Down / Limit Kuota Tercapai**:
  - Pada tahap **Klasifikasi**: Sistem akan 100% mengandalkan *Rule-Based Keyword Matching*.
  - Pada tahap **Narasi/Laporan**: Modul `llm_narrator.py` akan menangkap error API dan secara otomatis mengeksekusi `_fallback_report()` atau `_fallback_narration()`. Fungsi fallback ini akan menyusun kalimat laporan kaku menggunakan *template string* statis berbahasa Indonesia tanpa bergantung pada AI.
- **Ketidaklengkapan Laporan Lab**: Jika laporan uji lab pengguna (input) tidak memuat parameter wajib, *Rule Engine* tidak akan langsung memberikan status FAIL yang menyesatkan, melainkan memisahkannya ke dalam status khusus **⚠️ MISSING**.

## 9. Batasan Sistem (Limitations) & Keamanan Data
- **Privasi Data (*Data Privacy*)**: Proses ekstraksi dan pengecekan lulus/gagal (*Rule-Based*) berjalan murni secara LOKAL di perangkat/server. Namun, data rangkuman tersebut tetap dilempar ke API eksternal (Google Gemini) jika fitur narasi LLM diaktifkan. Untuk skala *Enterprise* yang menangani kerahasiaan pabrik mutlak, direkomendasikan mengganti inisialisasi Gemini dengan LLM Open-Source (contoh: Llama-3 lokal) agar data tidak pernah keluar dari server.
- **Toleransi *Typo***: Karena logika ekstraktor mengandalkan *Regular Expression (Regex)*, kesalahan ketik (typo) yang sangat ekstrem akibat distorsi OCR parah pada kertas laporan (misal: "Sa1mon3lla" alih-alih "Salmonella") memiliki kemungkinan lolos alias gagal ditangkap oleh Regex. Ke depannya, ini bisa di-*improve* dengan menambahkan integrasi Fuzzy Matching.
