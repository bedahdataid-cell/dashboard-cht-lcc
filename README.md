# Dashboard CHT-LCC Glasswool — Panci Listrik Mini Q2-8012

Dashboard interaktif untuk optimasi ketebalan isolator glasswool pada panci listrik
mini berdaya rendah, mengintegrasikan hasil simulasi *Conjugate Heat Transfer* (CHT)
dengan model *Life Cycle Cost* (LCC) berbasis ISO 15686-5:2017.

**Penelitian Hibah Internal LPPM Universitas Mayasari Bakti (UMB) 2026**
Peneliti: Bakti Alpihuda, S.T., M.T. — Program Studi Teknik Mesin, UMB Tasikmalaya

---

## Latar Belakang

Panci listrik mini domestik umumnya dipasarkan tanpa lapisan insulasi termal.
Penelitian ini mengukur rugi panas pada lima konfigurasi ketebalan glasswool
(0–20 mm) melalui simulasi CHT, lalu mencari ketebalan yang meminimalkan biaya
siklus hidup selama 5 tahun.

## Hasil Utama

| Parameter | Nilai |
|---|---|
| Ketebalan optimal (L*) | 11,28 mm |
| Rekomendasi praktis | **10 mm** (ukuran komersial standar) |
| LCC minimum | Rp 20.977 |
| Penghematan vs tanpa insulasi | Rp 33.918 (61,8%) |
| *Payback period* | 0,40 tahun (~5 bulan) |
| Rugi panas: 0 mm → 10 mm | 23,192 W → 7,654 W (−67,0%) |

Kurva LCC sangat landai — seluruh rentang **9,1–13,9 mm** berada dalam +1% dari
biaya minimum, sehingga pemilihan ketebalan komersial standar tidak merugikan
secara ekonomi.

### Temuan penting: tutup menjadi *bottleneck*

Kontribusi tutup terhadap total rugi panas naik dari 12,1% (tanpa insulasi)
menjadi 80,8% (glasswool 20 mm). Penambahan glasswool dari 15 ke 20 mm hanya
menghemat 0,022 W, sedangkan estimasi analitik menunjukkan insulasi 5 mm pada
tutup menghemat 2,66 W — sekitar 120× lebih efektif.

---

## Menjalankan Dashboard

### Lokal

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Dashboard terbuka di `http://localhost:8501`.

### Analisis tanpa dashboard

```bash
python lcc_optimizer.py
```

Menghasilkan grafik PNG dan CSV ringkasan di folder `output/`.

---

## Isi Dashboard

- **Sidebar** — input data simulasi CHT dan parameter ekonomi (slider interaktif)
- **Metrik** — L*, LCC minimum, penghematan, *payback period*, R²
- **Kurva Q(L)** — data simulasi, regresi, dan garis asimtot
- **Kurva LCC** — dekomposisi investasi vs NPV energi, dengan rentang toleransi +1%
- **Sensitivitas OAT** — *tornado chart* lima parameter ekonomi
- **Monte Carlo** — distribusi L* dari 10.000 skenario
- **Tabel & unduhan** — data regresi, sensitivitas, statistik Monte Carlo (CSV/PNG)

---

## Metodologi

**Simulasi CHT** — SolidWorks Flow Simulation, *steady-state external analysis*,
metode volume hingga (FVM), model turbulensi k-ε Lam-Bremhorst. Suhu dinding dalam
dijaga 95 °C (Model B), ambien 27 °C, gravitasi −9,81 m/s² arah Y, radiasi
*Discrete Transfer* aktif. Mesh Global Level 6 + Local Refinement 3 (222.190 sel).

**Regresi Q(L)** — model resistansi seri:

```
Q(L) = Q∞ + A / (B + L)
```

dengan Q∞ = 5,4636 W, A = 25,3140, B = 1,4278 (R² = 0,9997). Q∞ merupakan asimtot
yang secara fisis merepresentasikan rugi panas lewat tutup yang tidak diinsulasi.

**Model LCC** — ISO 15686-5:2017, pendekatan *Net Present Value*:

```
LCC(L) = C_inv(L) + Σ [E_loss(L) × tarif × (1+i)^t] / (1+r)^t
```

**Optimasi** — `scipy.optimize.minimize_scalar` (*bounded*), diverifikasi silang
dengan `brentq` pada dLCC/dL = 0.

### Parameter ekonomi (terverifikasi Agustus 2026)

| Parameter | Nilai | Sumber |
|---|---|---|
| Tarif listrik | Rp 1.444,70/kWh | PLN R-1/TR 1.300 VA, Triwulan III 2026 |
| Suku bunga diskonto | 5,75% | BI-Rate resmi, 22 Juli 2026 |
| Inflasi tarif | 3,0%/tahun | Inflasi umum BPS Juli 2026: 2,88% y-o-y |
| Jam operasi | 365 jam/tahun | Survei pola pakai, Mei 2026 |
| Harga glasswool | Rp 4.500/m²/mm | Survei pasar Tasikmalaya, Mei 2026 |
| Umur analisis | 5 tahun | Garansi produsen + ekstensi empiris |

---

## Keterbatasan

1. **Mesh independence study tidak dilaksanakan** — seluruh simulasi memakai satu
   konfigurasi mesh. Kredibilitas didukung validasi K0 terhadap korelasi
   Churchill-Chu (galat 3,71%) dan reprodusibilitas hasil pada pengulangan
   simulasi.
2. **Validasi Churchill-Chu tidak terpenuhi pada K1–K4** (15,18–50,04%). Gap
   membesar sistematis seiring ketebalan; penyebabnya belum teridentifikasi.
   Faktor yang telah diuji dan tereliminasi: radiasi, mesh, pemilihan permukaan,
   kelengkungan silinder, panjang karakteristik, konvensi evaluasi sifat udara,
   dan keseragaman suhu permukaan.
3. **Tidak ada validasi eksperimental langsung** pada tahap ini; validasi
   kalorimetrik direncanakan Tahap 2 (2027).
4. **Kondisi *steady-state*** — dinamika transien tidak dimodelkan.
5. **Estimasi insulasi tutup bersifat analitik** (model resistansi seri 1-D),
   belum diverifikasi simulasi CHT.

---

## Struktur Berkas

```
streamlit_app.py      Dashboard interaktif
lcc_optimizer.py      Mesin analisis LCC (regresi, optimasi, sensitivitas, Monte Carlo)
data_CHT_hasil.csv    Data hasil simulasi CHT K0–K4
requirements.txt      Dependensi Python
```

## Sitasi

```bibtex
@software{alpihuda2026chtlcc,
  author  = {Alpihuda, Bakti},
  title   = {Dashboard CHT-LCC Glasswool: Optimasi Ketebalan Isolator
             Panci Listrik Mini},
  year    = {2026},
  note    = {Penelitian Hibah Internal LPPM Universitas Mayasari Bakti}
}
```

## Lisensi

[MIT](LICENSE) © 2026 Bakti Alpihuda
