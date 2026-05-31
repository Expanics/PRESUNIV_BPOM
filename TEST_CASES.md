# 📋 Panduan Pengujian Input Data (Raw Text)

Dokumen ini menyediakan **tiga contoh data uji dalam format teks manual** untuk sistem **BPOM Compliance AI**. Anda dapat langsung menyalin (copy) teks di bawah ini dan menempelkannya (paste) ke area **"Atau Masukkan Teks Manual"** pada **Tab 1: Input Dokumen** di antarmuka Gradio.

Semua pengujian di bawah dirancang untuk kategori produk **SUPLEMEN KESEHATAN**.

---

## 1. Kasus Uji 1: Lolos Penuh (Full Approve)
*Semua parameter mikroba, logam berat, dan klaim produk sepenuhnya mematuhi standar regulasi BPOM yang berlaku.*

```text
=== INFORMASI PRODUK ===

Nama Produk:
HerbaGuard Premium

Produsen:
PT Sehat Herbal Indonesia

Kategori Produk:
Suplemen Kesehatan

Bentuk Sediaan:
Kapsul

Netto:
60 Kapsul

=== KOMPOSISI ===

Ekstrak Jahe Merah ........... 300 mg
Ekstrak Temulawak ............ 150 mg
Zinc Picolinate .............. 10 mg

=== HASIL UJI LABORATORIUM ===

Total Plate Count ............ 4.5 x 10^3 CFU/g
Coliform ..................... < 3 APM/g
E.coli ....................... negatif
Salmonella ................... negatif
Staphylococcus aureus ........ negatif
Kapang dan Khamir ............ 250 CFU/g
Bacillus cereus .............. 100 CFU/g

Kadar Timbal (Pb) ............ 0.12 mg/kg
Kadar Kadmium (Cd) ........... 0.05 mg/kg
Kadar Merkuri (Hg) ........... 0.005 mg/kg
Kadar Arsen (As) ............. 0.15 mg/kg

Tanggal Pengujian:
20 Mei 2026

=== CPPOB ===

Fasilitas memenuhi standar sanitasi .......... ya
Higiene personel terjaga ..................... ya
Penyimpanan pada suhu sesuai ................. ya
Sumber air memenuhi standar .................. ya
Pengendalian hama terdokumentasi ............. ya
Transportasi memenuhi syarat ................. ya

=== KLAIM PRODUK ===

- Membantu memelihara daya tahan tubuh
- Membantu menghangatkan badan
- Membantu meredakan pegal linu
```

---

## 2. Kasus Uji 2: Pelanggaran Sebagian (Zat Terlalu Tinggi / Partial Violations)
*Sebagian besar parameter lolos, namun beberapa cemaran mikroba dan logam berat melebihi ambang batas maksimal BPOM.*

```text
=== INFORMASI PRODUK ===

Nama Produk:
VitaBoost Active

Produsen:
PT Multi Nutrisi Nusantara

Kategori Produk:
Suplemen Kesehatan

Bentuk Sediaan:
Tablet

Netto:
30 Tablet

=== KOMPOSISI ===

Vitamin C .................... 500 mg
Zinc ......................... 15 mg
Ekstrak Ginseng .............. 100 mg

=== HASIL UJI LABORATORIUM ===

Total Plate Count ............ 2.5 x 10^4 CFU/g
Coliform ..................... 35 APM/g
E.coli ....................... negatif
Salmonella ................... negatif
Staphylococcus aureus ........ negatif
Kapang dan Khamir ............ 1.8 x 10^3 CFU/g
Bacillus cereus .............. 150 CFU/g

Kadar Timbal (Pb) ............ 4.2 mg/kg
Kadar Kadmium (Cd) ........... 0.15 mg/kg
Kadar Merkuri (Hg) ........... 0.008 mg/kg
Kadar Arsen (As) ............. 1.85 mg/kg

Tanggal Pengujian:
22 Mei 2026

=== CPPOB ===

Fasilitas memenuhi standar sanitasi .......... ya
Higiene personel terjaga ..................... ya
Penyimpanan pada suhu sesuai ................. ya
Sumber air memenuhi standar .................. ya
Pengendalian hama terdokumentasi ............. ya
Transportasi memenuhi syarat ................. ya

=== KLAIM PRODUK ===

- Membantu menjaga stamina tubuh
- Membantu memelihara kesehatan tubuh
```

### 🔍 Analisis Pelanggaran pada Kasus 2:
* **Coliform**: **35 APM/g** ❌ (Batas Maksimal BPOM: **10 APM/g**)
* **Kapang dan Khamir**: **1.800 CFU/g** ❌ (Batas Maksimal BPOM: **1.000 CFU/g**)
* **Timbal (Pb)**: **4.2 mg/kg** ❌ (Batas Maksimal BPOM: **2.0 mg/kg**)
* **Arsen (As)**: **1.85 mg/kg** ❌ (Batas Maksimal BPOM: **1.0 mg/kg**)

---

## 3. Kasus Uji 3: Gagal Total (Full Warning / Full Fail)
*Semua parameter cemaran mikroba dan logam berat melebihi batas aman, dan klaim produk mengandung klaim pengobatan medis/kuratif yang dilarang keras oleh BPOM.*

```text
=== INFORMASI PRODUK ===

Nama Produk:
MaxiCure Miracle Drop

Produsen:
PT Rahasia Alam Perkasa

Kategori Produk:
Suplemen Kesehatan

Bentuk Sediaan:
Cairan Obat Dalam

Netto:
15 ml

=== KOMPOSISI ===

Madu Hutan ................... 90%
Royal Jelly .................. 5%
Propolis Extract ............. 5%

=== HASIL UJI LABORATORIUM ===

Total Plate Count ............ 8.5 x 10^5 CFU/g
Coliform ..................... 120 APM/g
E.coli ....................... positif
Salmonella ................... positif
Staphylococcus aureus ........ 4.5 x 10^2 CFU/g
Kapang dan Khamir ............ 8.2 x 10^3 CFU/g
Bacillus cereus .............. 1.2 x 10^4 CFU/g

Kadar Timbal (Pb) ............ 8.5 mg/kg
Kadar Kadmium (Cd) ........... 3.2 mg/kg
Kadar Merkuri (Hg) ........... 0.85 mg/kg
Kadar Arsen (As) ............. 4.2 mg/kg

Tanggal Pengujian:
25 Mei 2026

=== CPPOB ===

Fasilitas memenuhi standar sanitasi .......... tidak
Higiene personel terjaga ..................... tidak
Penyimpanan pada suhu sesuai ................. tidak
Sumber air memenuhi standar .................. tidak
Pengendalian hama terdokumentasi ............. tidak
Transportasi memenuhi syarat ................. tidak

=== KLAIM PRODUK ===

- Menyembuhkan diabetes secara alami dan permanen
- Mengobati kanker payudara tanpa operasi
- Mencegah stroke dan membersihkan plak pembuluh darah
```

### 🔍 Analisis Pelanggaran pada Kasus 3:
* **Cemaran Mikroba**: **SEMUA PARAMETER GAGAL** ❌ (ALT, Coliform, E.coli positif, Salmonella positif, S.aureus, Kapang/Khamir, dan B.cereus semuanya jauh melebihi batas BPOM).
* **Cemaran Logam Berat**: **SEMUA PARAMETER GAGAL** ❌ (Pb, Cd, Hg, dan As semuanya sangat tinggi di atas ambang batas aman).
* **Klaim Pengobatan (Curative Claims)**: **DILARANG KERAS** ❌ (Suplemen dilarang memiliki klaim medis/kuratif seperti *"menyembuhkan diabetes"*, *"mengobati kanker"*, dan *"mencegah stroke"*).
