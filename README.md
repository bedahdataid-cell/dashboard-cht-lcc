# Dashboard CHT-LCC Glasswool — Panci Listrik Mini Q2-8012

Dashboard interaktif untuk optimasi ketebalan isolator glasswool pada panci listrik
mini berdaya rendah, mengintegrasikan hasil simulasi *Conjugate Heat Transfer* (CHT)
dengan model *Life Cycle Cost* (LCC) berbasis ISO 15686-5:2017.

**Penelitian Hibah Internal LPPM Universitas Mayasari Bakti (UMB) 2026**
Peneliti: Bakti Alpihuda, S.T., M.T. — Program Studi Teknik Mesin, UMB Tasikmalaya

**🔗 Dashboard live:** [dashboard-cht-lcc-mbuvycwgrfnuumvhexnriv.streamlit.app](https://dashboard-cht-lcc-mbuvycwgrfnuumvhexnriv.streamlit.app/)

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

Kontribusi tutup terhadap total rugi panas naik seiring penambahan glasswool
dinding — dinding berhasil ditekan tajam, tetapi rugi lewat tutup (tidak
diinsulasi) justru naik karena panas "dialihkan" ke sana. Estimasi analitik
menunjukkan insulasi 5 mm pada tutup jauh lebih efektif per-mm dibanding
menambah tebal dinding pada titik ini. Lihat halaman **Temuan utama** di
dashboard untuk rincian dan angka terverifikasi.

---

## Menjalankan Dashboard

### Lokal (Windows, cara termudah)

Klik dua kali `2_Buka_Dashboard.bat` — browser terbuka otomatis ke
`http://localhost:8501`. Jalankan `3_Install_Kebutuhan.bat` lebih dulu bila
dependensi belum terpasang.

### Lokal (manual / non-Windows)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Analisis tanpa dashboard (CLI)

```bash
python lcc_optimizer.py
```

Menghasilkan grafik PNG dan CSV ringkasan di folder `output/` (tidak masuk
repo — lihat `.gitignore`).

### Notebook langkah-demi-langkah

`Analisis_CHT_LCC.ipynb` (atau `.py` versi script) menjalankan analisis yang
sama secara bertahap dengan penjelasan tiap bagian — memanggil fungsi dari
`lcc_optimizer.py` yang sama, tidak menulis ulang rumus, supaya angkanya
identik. Cocok untuk dibahas saat monev.

### Deploy ke Streamlit Community Cloud

1. Repo ini sudah siap deploy — push ke `main` sudah otomatis memicu
   redeploy bila app sudah terhubung.
2. Buka [share.streamlit.io](https://share.streamlit.io) → login dengan akun
   GitHub yang memiliki repo ini.
3. **New app** → pilih repo `dashboard-cht-lcc`, branch `main`, file utama
   `streamlit_app.py`.
4. URL publik siap dibagikan (luaran diseminasi/HKI).

---

## Struktur Dashboard

Dashboard memakai navigasi multi-halaman (`st.navigation`), bukan satu file
tunggal — supaya tiap topik (panduan, hasil, temuan, dsb.) mudah dibaca dan
dinavigasi terpisah.

```text
streamlit_app.py         Entry point: konfigurasi halaman + navigasi
app_core.py               Parameter sidebar & seluruh perhitungan (di-cache),
                           dipanggil oleh semua halaman
app_visual.py              Visualisasi 2D (dekomposisi rugi panas per permukaan)
app_visual3d.py            Diagram 3D interaktif bentuk panci (plotly)
app_pages/
  0_panduan.py              Panduan singkat — bahasa awam, untuk pembaca umum
  1_hasil.py                Hasil utama: L*, LCC, kurva Q(L)/LCC, visual 3D
  2_temuan.py                Temuan utama: tutup sebagai bottleneck rugi panas
  3_ketahanan.py             Sensitivitas OAT (tornado) & Monte Carlo
  4_metode.py                 Metodologi simulasi CHT & model LCC, sumber data
  5_dampak_nasional.py         Skenario ilustratif skala nasional (bukan angka
                               pasti — lihat catatan integritas data di file)

lcc_optimizer.py          Mesin analisis: regresi Q(L), LCC, optimasi,
                           sensitivitas, Monte Carlo. Sumber tunggal rumus —
                           dipanggil oleh dashboard maupun notebook/CLI.
data_CHT_hasil.csv        Data hasil simulasi CHT K0–K4 (input)
requirements.txt          Dependensi Python (versi dipin ke versi teruji)
.streamlit/config.toml    Tema dashboard (warna, dsb.) — TIDAK menetapkan
                           server.address, supaya kompatibel dengan deploy cloud
*.bat                     Peluncur cepat untuk Windows (install/jalankan)
```

---

## Metodologi

**Simulasi CHT** — SolidWorks Flow Simulation, *steady-state external analysis*,
metode volume hingga (FVM), model turbulensi k-ε Lam-Bremhorst. Suhu dinding dalam
dijaga 95 °C (Model B), ambien 27 °C, gravitasi −9,81 m/s² arah Y, radiasi
*Discrete Transfer* aktif. Mesh Global Level 6 + Local Refinement 3 (222.190 sel).

**Regresi Q(L)** — model resistansi seri:

```text
Q(L) = Q∞ + A / (B + L)
```

dengan Q∞ = 5,4636 W, A = 25,3140, B = 1,4278 (R² = 0,9997). Q∞ merupakan asimtot
yang secara fisis merepresentasikan rugi panas lewat tutup yang tidak diinsulasi.

**Model LCC** — ISO 15686-5:2017, pendekatan *Net Present Value*:

```text
LCC(L) = C_inv(L) + Σ [E_loss(L) × tarif × (1+i)^t] / (1+r)^t
```

Biaya investasi (`biaya_investasi()`/`luas_selimut()` di `lcc_optimizer.py`)
bersifat parametrik terhadap dimensi panci (radius luar wadah, tinggi) — dapat
dihitung ulang untuk geometri lain, meski kurva Q(L) tetap spesifik untuk
Q2-8012 (perlu simulasi CHT baru untuk geometri berbeda).

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

Semua parameter dapat diubah lewat sidebar dashboard tanpa mengedit kode.

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
6. **Skenario dampak nasional (halaman 5) bersifat ilustratif** — tidak ada data
   terverifikasi jumlah unit Q2-8012 spesifik yang beredar di Indonesia; angka
   skala nasional selalu dapat diatur pengguna, bukan klaim pasti.

---

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
