"""
streamlit_app.py
================
Dashboard interaktif CHT-LCC Glasswool — Panci Listrik Mini Q2-8012
Penelitian Hibah Internal LPPM UMB 2026 · Bakti Alpihuda

Jalankan lokal:
  pip install streamlit numpy scipy matplotlib pandas
  streamlit run streamlit_app.py

Deploy ke Streamlit Community Cloud:
  1. Push repo ke GitHub
  2. share.streamlit.io -> New app -> pilih file ini
  3. URL publik gratis

Arsitektur 4 panel (proposal §2.5.6):
  A. Input parameter ekonomi (sidebar slider)
  B. Kurva Q(L) + titik simulasi CHT
  C. Kurva LCC dekomposisi (investasi vs NPV energi vs total)
  D. Ringkasan eksekutif (L*, LCC minimum, payback period, rekomendasi IF-THEN)
  + Sensitivitas OAT (tornado) & Monte Carlo distribusi L*

CATATAN AUDIT 8 Agu 2026: script diselaraskan dgn lcc_optimizer.py yang sudah
diaudit — parameter ekonomi terverifikasi, model regresi resistansi seri (bukan
polinomial), harga glasswool per m2/mm (bukan per mm), biaya pasang markup 1,2x.
Nilai default data CHT = hasil simulasi NYATA K0-K4 (bukan data demo).
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch
from scipy.optimize import minimize_scalar
from scipy.stats import norm
import streamlit as st
from io import BytesIO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from lcc_optimizer import (
    regresi_cht, lcc_total, biaya_investasi, npv_energi, luas_selimut,
    biaya_energi_tahunan,
    TARIF_KWH, DISCOUNT_RATE, INFLASI_TARIF, UMUR_ANALISIS,
    JAM_OPERASI, HARI_TAHUN, HARGA_GW_PER_M2_MM, MARKUP_PASANG,
    L_MIN, L_MAX,
)

# ─────────────────────────────────────────────────────────────────────────────
# DATA SIMULASI CHT NYATA (SolidWorks Flow Simulation, 8 Agu 2026)
# Setting baku: semua komponen include, material eksplisit (AISI 304 / ABS PC /
# Glasswool k=0,036), Default solid AISI 304, initial solid 27 C, mesh Level 6
# + Local Refinement 3. Konservasi energi 0,0000-0,0147% (kriteria proposal <1%).
# ─────────────────────────────────────────────────────────────────────────────
DATA_CHT_DEFAULT = [
    ("K0", "K0 — tanpa glasswool (L=0 mm)",  0,  23.192),
    ("K1", "K1 — glasswool 5 mm",            5,   9.439),
    ("K2", "K2 — glasswool 10 mm",           10,  7.654),
    ("K3", "K3 — glasswool 15 mm",           15,  6.830),
    ("K4", "K4 — glasswool 20 mm",           20,  6.808),
]

# Kontribusi tutup per konfigurasi (W) — utk panel temuan bottleneck
Q_TUTUP = {0: 2.801, 5: 3.983, 10: 4.820, 15: 5.017, 20: 5.503}

st.set_page_config(
    page_title="CHT-LCC Glasswool — UMB 2026",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 Dashboard CHT-LCC Glasswool")
st.caption(
    "**Optimasi Ketebalan Glasswool Panci Listrik Mini Q2-8012** — "
    "Penelitian Hibah Internal LPPM UMB 2026 · Bakti Alpihuda · Teknik Mesin UMB"
)

# ─────────────────────────────────────────────────────────────────────────────
# PANEL A — SIDEBAR INPUT
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Parameter")

    st.subheader("Data Simulasi CHT")
    st.caption(
        "Nilai bawaan = hasil simulasi SolidWorks Flow Simulation "
        "(8 Agu 2026). Ubah untuk menguji data lain."
    )

    L_vals, Q_vals, kode_vals = [], [], []
    for kode, label, L, q_default in DATA_CHT_DEFAULT:
        q = st.number_input(label, min_value=0.1, max_value=500.0,
                            value=float(q_default), step=0.001, format="%.3f")
        kode_vals.append(kode)
        L_vals.append(L)
        Q_vals.append(q)

    st.markdown("---")
    st.subheader("Asumsi Ekonomi")
    st.caption("Nilai bawaan terverifikasi — lihat keterangan di bawah dashboard.")

    tarif = st.number_input("Tarif listrik (Rp/kWh)", 500.0, 5000.0,
                            float(TARIF_KWH), step=10.0, format="%.2f")
    rate = st.slider("Suku bunga diskonto (%/tahun)", 1.0, 15.0,
                     DISCOUNT_RATE * 100, 0.25) / 100
    inflasi = st.slider("Inflasi tarif (%/tahun)", 0.5, 10.0,
                        INFLASI_TARIF * 100, 0.25) / 100
    n_tahun = st.slider("Umur analisis (tahun)", 1, 15, UMUR_ANALISIS, 1)
    jam = st.slider("Jam operasi/hari", 0.5, 12.0, JAM_OPERASI, 0.25)
    st.caption(f"→ {jam * HARI_TAHUN:,.0f} jam/tahun")

    st.markdown("---")
    st.subheader("Biaya Glasswool")
    harga_gw = st.number_input("Harga glasswool (Rp/m²/mm)", 500.0, 20000.0,
                               float(HARGA_GW_PER_M2_MM), step=100.0)
    markup = st.slider("Faktor markup pemasangan (× biaya material)",
                       1.0, 2.0, float(MARKUP_PASANG), 0.05)

    st.markdown("---")
    n_mc = st.select_slider("Skenario Monte Carlo",
                            options=[1000, 5000, 10000, 20000], value=10000)
    seed_mc = st.number_input("Random seed", 0, 9999, 42, 1)

# ─────────────────────────────────────────────────────────────────────────────
# PERHITUNGAN
# ─────────────────────────────────────────────────────────────────────────────
df_input = pd.DataFrame({
    "Konfigurasi": kode_vals,
    "L_mm": L_vals,
    "Q_Watt": Q_vals,
})

koef, fQ, R2 = regresi_cht(df_input)
Q_inf, A_fit, B_fit = koef


def lcc_fn(L):
    return lcc_total(L, fQ, rate=rate, inflasi=inflasi, n_tahun=n_tahun,
                     tarif=tarif, jam=jam, harga_per_m2_mm=harga_gw)


res = minimize_scalar(lcc_fn, bounds=(L_MIN, L_MAX), method="bounded",
                      options={"xatol": 1e-4})
L_opt, LCC_opt = res.x, res.fun
lcc_k0 = lcc_fn(0.0)

L_range = np.linspace(L_MIN, L_MAX, 300)
Q_curve = np.maximum(fQ(L_range), 0)
LCC_curve = np.array([lcc_fn(l) for l in L_range])
inv_curve = np.array([biaya_investasi(l, harga_per_m2_mm=harga_gw, markup=markup)
                      for l in L_range])
npv_curve = np.array([npv_energi(float(max(fQ(l), 0.1)), rate=rate,
                                 inflasi=inflasi, n_tahun=n_tahun,
                                 tarif=tarif, jam=jam)
                      for l in L_range])

# Rentang praktis: L yang LCC-nya dalam +1% dari optimum
L_fine = np.linspace(0.05, L_MAX, 2000)
lcc_fine = np.array([lcc_fn(l) for l in L_fine])
mask_1pct = lcc_fine <= LCC_opt * 1.01
L_lo, L_hi = (L_fine[mask_1pct].min(), L_fine[mask_1pct].max()) if mask_1pct.any() else (L_opt, L_opt)

# Payback period: investasi dibagi penghematan energi tahunan (tahun ke-1)
Q_k0 = float(fQ(0.0))
Q_at_opt = float(fQ(L_opt))
hemat_energi_thn1 = (biaya_energi_tahunan(Q_k0, tarif=tarif, jam=jam)
                     - biaya_energi_tahunan(Q_at_opt, tarif=tarif, jam=jam))
inv_opt = biaya_investasi(L_opt, harga_per_m2_mm=harga_gw, markup=markup)
payback = inv_opt / hemat_energi_thn1 if hemat_energi_thn1 > 0 else float("inf")

# ─────────────────────────────────────────────────────────────────────────────
# PANEL D — RINGKASAN EKSEKUTIF (metrics)
# ─────────────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("L* Optimal", f"{L_opt:.2f} mm",
          help="Ketebalan glasswool yang meminimalkan LCC total")
c2.metric("LCC Minimum", f"Rp {LCC_opt:,.0f}",
          help=f"Life Cycle Cost pada L* selama {n_tahun} tahun")
c3.metric("Penghematan vs K0", f"Rp {lcc_k0 - LCC_opt:,.0f}",
          f"{(lcc_k0 - LCC_opt) / lcc_k0 * 100:.1f}%")
c4.metric("Payback Period", f"{payback:.2f} thn" if np.isfinite(payback) else "—",
          help="Investasi glasswool dibagi penghematan biaya energi tahun ke-1")
c5.metric("R² Regresi", f"{R2:.4f}",
          help="Goodness-of-fit Q(L) model resistansi seri — target ≥ 0,99")

if R2 < 0.99:
    st.warning("⚠️ R² < 0,99 — kualitas data simulasi perlu diperiksa.")

# Rekomendasi IF-THEN (proposal §2.5.6)
L_praktis = round(L_opt / 5) * 5 or 5   # bulatkan ke kelipatan 5 mm terdekat
st.info(
    f"**Rekomendasi:** ketebalan optimal secara matematis **{L_opt:.2f} mm**. "
    f"Namun kurva LCC sangat landai — seluruh rentang **{L_lo:.1f}–{L_hi:.1f} mm** "
    f"berada dalam +1% dari LCC minimum. "
    f"Untuk penerapan praktis gunakan **{L_praktis:.0f} mm** "
    f"(ukuran komersial standar, selisih biaya "
    f"Rp {abs(lcc_fn(L_praktis) - LCC_opt):,.0f} atau "
    f"{abs(lcc_fn(L_praktis) - LCC_opt) / LCC_opt * 100:.2f}% dari optimum). "
    f"Jika jam operasi meningkat, L* bergeser lebih tebal; jika harga glasswool "
    f"naik, L* bergeser lebih tipis — lihat panel sensitivitas."
)

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# GRAFIK 4 PANEL
# ─────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 11))
fig.suptitle(
    "CHT-LCC Analysis — Optimasi Glasswool Panci Listrik Mini Q2-8012\n"
    "Penelitian Hibah Internal LPPM UMB 2026",
    fontsize=13, fontweight="bold",
)
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.38)

# Panel B: Q(L)
ax1 = fig.add_subplot(gs[0, 0])
ax1.scatter(L_vals, Q_vals, color="red", s=70, zorder=5,
            label="Simulasi CHT (SolidWorks)")
ax1.plot(L_range, Q_curve, "b-", linewidth=2,
         label=f"Resistansi seri (R²={R2:.4f})")
ax1.axhline(Q_inf, color="gray", linestyle=":", linewidth=1.5,
            label=f"Asimtot Q∞ = {Q_inf:.2f} W")
ax1.axvline(L_opt, color="green", linestyle="--", label=f"L* = {L_opt:.2f} mm")
ax1.scatter([L_opt], [Q_at_opt], color="green", s=110, zorder=6, marker="*")
ax1.set_xlabel("Ketebalan glasswool L (mm)")
ax1.set_ylabel("Heat Transfer Rate Q (W)")
ax1.set_title("A. Kurva Q(L) — Regresi Data CHT")
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.3)

# Panel C: LCC dekomposisi
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(L_range, LCC_curve / 1000, "purple", linewidth=2.5, label="LCC Total")
ax2.plot(L_range, inv_curve / 1000, "g--", linewidth=1.5, label="Investasi glasswool")
ax2.plot(L_range, npv_curve / 1000, "r--", linewidth=1.5, label="NPV energi terbuang")
ax2.axvspan(L_lo, L_hi, color="gold", alpha=0.20,
            label=f"Rentang +1%: {L_lo:.1f}–{L_hi:.1f} mm")
ax2.axvline(L_opt, color="black", linestyle=":", linewidth=2)
ax2.scatter([L_opt], [LCC_opt / 1000], color="black", s=110, zorder=6, marker="D",
            label=f"L*={L_opt:.2f} mm · Rp {LCC_opt:,.0f}")
ax2.set_xlabel("Ketebalan glasswool L (mm)")
ax2.set_ylabel("Biaya (× Rp 1.000)")
ax2.set_title(f"B. Life Cycle Cost (n={n_tahun} tahun)")
ax2.legend(fontsize=8)
ax2.grid(True, alpha=0.3)

# Panel: Sensitivitas OAT (tornado)
ax3 = fig.add_subplot(gs[1, 0])
sens_params = [
    ("Tarif Listrik",   "tarif",           tarif,    0.20),
    ("Suku Bunga",      "rate",            rate,     0.02),
    ("Inflasi Tarif",   "inflasi",         inflasi,  0.015),
    ("Harga Glasswool", "harga_per_m2_mm", harga_gw, 0.20),
    ("Jam Operasi",     "jam",             jam,      0.50),
]
sens_rows = []
for label, key, base_val, delta in sens_params:
    for sign in (+1, -1):
        new_val = (base_val + sign * delta) if key in ("rate", "inflasi") \
            else base_val * (1 + sign * delta)
        kw = dict(rate=rate, inflasi=inflasi, n_tahun=n_tahun,
                  tarif=tarif, jam=jam, harga_per_m2_mm=harga_gw)
        kw[key] = new_val
        r_s = minimize_scalar(lambda L: lcc_total(L, fQ, **kw),
                              bounds=(L_MIN, L_MAX), method="bounded")
        sens_rows.append({
            "Parameter": label, "Arah": "Naik" if sign > 0 else "Turun",
            "Nilai Baru": round(new_val, 4),
            "L* (mm)": round(r_s.x, 2),
            "dLCC (%)": round((r_s.fun - LCC_opt) / LCC_opt * 100, 2),
        })
df_sens = pd.DataFrame(sens_rows)

labels_uniq = [s[0] for s in sens_params]
for i, label in enumerate(labels_uniq):
    up = df_sens[(df_sens["Parameter"] == label) & (df_sens["Arah"] == "Naik")]["dLCC (%)"].iloc[0]
    dn = df_sens[(df_sens["Parameter"] == label) & (df_sens["Arah"] == "Turun")]["dLCC (%)"].iloc[0]
    ax3.barh(i + 0.20, up, height=0.38, color="salmon")
    ax3.barh(i - 0.20, dn, height=0.38, color="lightblue")
ax3.set_yticks(np.arange(len(labels_uniq)))
ax3.set_yticklabels(labels_uniq, fontsize=9)
ax3.axvline(0, color="black", lw=1)
ax3.set_xlabel("Perubahan LCC* (%)")
ax3.set_title("C. Sensitivitas OAT")
ax3.grid(True, axis="x", alpha=0.3)
ax3.legend(handles=[Patch(color="salmon", label="Parameter naik"),
                    Patch(color="lightblue", label="Parameter turun")],
           fontsize=8, loc="lower right")

# Panel: Monte Carlo
ax4 = fig.add_subplot(gs[1, 1])
with st.spinner(f"Menjalankan Monte Carlo {int(n_mc):,} skenario..."):
    rng = np.random.default_rng(int(seed_mc))
    mc_n = int(n_mc)
    t_mc = np.clip(rng.normal(tarif, tarif * 0.10, mc_n), 500, 5000)
    r_mc = np.clip(rng.normal(rate, 0.01, mc_n), 0.01, 0.15)
    i_mc = np.clip(rng.normal(inflasi, 0.0075, mc_n), 0.001, 0.10)
    h_mc = np.clip(rng.normal(harga_gw, harga_gw * 0.10, mc_n), 1000, 12000)
    j_mc = np.clip(rng.normal(jam, jam * 0.25, mc_n), 0.25, 12)

    L_mc = np.zeros(mc_n)
    for idx in range(mc_n):
        kw = dict(rate=float(r_mc[idx]), inflasi=float(i_mc[idx]),
                  n_tahun=n_tahun, tarif=float(t_mc[idx]),
                  jam=float(j_mc[idx]), harga_per_m2_mm=float(h_mc[idx]))
        L_mc[idx] = minimize_scalar(lambda L: lcc_total(L, fQ, **kw),
                                    bounds=(L_MIN, L_MAX),
                                    method="bounded").x

L_mean, L_std = L_mc.mean(), L_mc.std()
L_p5, L_p95 = np.percentile(L_mc, 5), np.percentile(L_mc, 95)

ax4.hist(L_mc, bins=60, color="steelblue", edgecolor="white", alpha=0.75, density=True)
ax4.axvline(L_mean, color="red", lw=2, label=f"Mean = {L_mean:.2f} mm")
ax4.axvline(L_p5, color="orange", lw=1.5, ls="--", label=f"P5 = {L_p5:.2f} mm")
ax4.axvline(L_p95, color="orange", lw=1.5, ls="--", label=f"P95 = {L_p95:.2f} mm")
x_n = np.linspace(L_mc.min(), L_mc.max(), 200)
ax4.plot(x_n, norm.pdf(x_n, L_mean, L_std), "r-", lw=1.5, alpha=0.6)
ax4.set_xlabel("L* Optimal (mm)")
ax4.set_ylabel("Densitas probabilitas")
ax4.set_title(f"D. Monte Carlo L* (n={mc_n:,})")
ax4.legend(fontsize=8)
ax4.grid(True, alpha=0.3)

buf = BytesIO()
plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
buf.seek(0)
st.image(buf, use_container_width=True)
plt.close()

st.download_button("⬇️ Download Grafik PNG", data=buf.getvalue(),
                   file_name="CHT_LCC_Analysis.png", mime="image/png")

# ─────────────────────────────────────────────────────────────────────────────
# TABEL RINGKASAN
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📋 Ringkasan Hasil")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Data CHT & Regresi", "Sensitivitas OAT", "Monte Carlo", "Temuan Utama"]
)

with tab1:
    df_disp = df_input.copy()
    df_disp["Q_fit (W)"] = np.round(fQ(df_input["L_mm"].values), 3)
    df_disp["Error (W)"] = (df_disp["Q_Watt"] - df_disp["Q_fit (W)"]).round(3)
    df_disp["Error (%)"] = (df_disp["Error (W)"] / df_disp["Q_Watt"] * 100).round(2)
    st.dataframe(df_disp, hide_index=True, use_container_width=True)
    st.caption(
        f"Model regresi: **Q(L) = Q∞ + A/(B+L)** dengan "
        f"Q∞ = {Q_inf:.4f} W, A = {A_fit:.4f}, B = {B_fit:.4f} · R² = {R2:.6f}. "
        f"Q∞ adalah asimtot — batas bawah rugi panas yang tidak dapat dikurangi "
        f"dengan menebalkan insulasi dinding, karena panas tetap lolos lewat tutup."
    )
    st.download_button("⬇️ Download data CSV",
                       data=df_disp.to_csv(index=False).encode("utf-8"),
                       file_name="data_CHT_regresi.csv", mime="text/csv")

with tab2:
    st.dataframe(df_sens, hide_index=True, use_container_width=True)
    st.download_button("⬇️ Download sensitivitas CSV",
                       data=df_sens.to_csv(index=False).encode("utf-8"),
                       file_name="sensitivitas_OAT.csv", mime="text/csv")

with tab3:
    mc_summary = pd.DataFrame({
        "Statistik": ["Mean", "Std", "P5", "P25", "Median", "P75", "P95"],
        "L* (mm)": [round(L_mean, 2), round(L_std, 2),
                    round(np.percentile(L_mc, 5), 2),
                    round(np.percentile(L_mc, 25), 2),
                    round(np.percentile(L_mc, 50), 2),
                    round(np.percentile(L_mc, 75), 2),
                    round(np.percentile(L_mc, 95), 2)],
    })
    st.dataframe(mc_summary, hide_index=True, use_container_width=True)
    st.caption(
        f"Interval kepercayaan 90% untuk L*: **{L_p5:.2f}–{L_p95:.2f} mm** "
        f"(n = {mc_n:,} skenario, seed = {int(seed_mc)})."
    )

with tab4:
    st.markdown(
        f"""
**1. Kurva Q(L) jenuh cepat.** Penambahan glasswool dari 15 mm ke 20 mm hanya
menurunkan rugi panas **0,022 W** — praktis nol. Penurunan total mentok pada
70,6% dibanding kondisi tanpa insulasi.

**2. Tutup menjadi bottleneck.** Kontribusi tutup terhadap total rugi panas naik
dari 12,1% (tanpa insulasi) menjadi **80,8%** pada glasswool 20 mm. Panas yang
tertahan di dinding berpindah jalur ke tutup yang tidak diinsulasi.

**3. Insulasi tutup jauh lebih efektif.** Estimasi analitik (model resistansi
seri 1-D, tervalidasi 0,4% terhadap simulasi tanpa insulasi): memasang glasswool
5 mm pada tutup menghemat **2,66 W** — sekitar **120× lebih besar** daripada
menebalkan dinding dari 15 ke 20 mm. *Status: proyeksi analitik, belum
diverifikasi simulasi CHT.*

**4. Kurva LCC sangat landai.** Rentang **{L_lo:.1f}–{L_hi:.1f} mm** semuanya
berada dalam +1% dari LCC minimum, sehingga pemilihan ketebalan komersial standar
tidak merugikan secara ekonomi.
        """
    )
    st.dataframe(
        pd.DataFrame({
            "L (mm)": list(Q_TUTUP.keys()),
            "Q total (W)": [q for _, _, _, q in DATA_CHT_DEFAULT],
            "Q tutup (W)": list(Q_TUTUP.values()),
            "Kontribusi tutup (%)": [
                round(Q_TUTUP[L] / q * 100, 1)
                for (_, _, L, q) in DATA_CHT_DEFAULT
            ],
        }),
        hide_index=True, use_container_width=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# SUMBER PARAMETER & KETERBATASAN
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📌 Sumber parameter & keterbatasan penelitian"):
    st.markdown(
        f"""
**Parameter ekonomi (terverifikasi 8 Agustus 2026)**

| Parameter | Nilai | Sumber |
|---|---|---|
| Tarif listrik | Rp {TARIF_KWH:,.2f}/kWh | PLN R-1/TR 1.300 VA, Triwulan III 2026 |
| Suku bunga diskonto | {DISCOUNT_RATE * 100:.2f}% | BI-Rate resmi per 22 Juli 2026 (bi.go.id) |
| Inflasi tarif | {INFLASI_TARIF * 100:.1f}% | Proposal Tabel 9 (inflasi umum BPS Juli 2026: 2,88% y-o-y) |
| Jam operasi | {JAM_OPERASI:.0f} jam/hari ({JAM_OPERASI * HARI_TAHUN:,.0f} jam/tahun) | Survei pola pakai 20 penghuni kos, Mei 2026 |
| Harga glasswool | Rp {HARGA_GW_PER_M2_MM:,.0f}/m²/mm | Survei 5 toko/marketplace Tasikmalaya, Mei 2026 |
| Markup pemasangan | {MARKUP_PASANG:.1f}× biaya material | Proposal Tabel 9 |
| Umur analisis | {UMUR_ANALISIS} tahun | Garansi produsen + ekstensi empiris |

Catatan: proposal mencantumkan suku bunga 4,5% sebagai proksi BI-Rate Q1 2026.
Nilai tersebut telah berubah — BI menaikkan suku bunga bertahap hingga 5,75%
(Juli 2026). Analisis sensitivitas menunjukkan perbedaan ini menggeser L* kurang
dari 0,3 mm, sehingga tidak mengubah kesimpulan.

**Keterbatasan**

1. **Mesh independence study tidak dilaksanakan.** Seluruh simulasi memakai satu
   konfigurasi mesh (Global Level 6 + Local Refinement 3, 222.190 sel).
   Kredibilitas hasil didukung oleh validasi K0 terhadap korelasi Churchill-Chu
   (selisih 3,14%, memenuhi kriteria ≤10%), konservasi energi global
   0,0000–0,0147% (kriteria <1%), dan reprodusibilitas pada pengulangan run.
2. **Validasi Churchill-Chu tidak terpenuhi pada K1–K4** (selisih 15,18–50,04%).
   Gap membesar secara sistematis seiring ketebalan insulasi; penyebabnya belum
   teridentifikasi. Faktor yang telah diuji dan tereliminasi: radiasi, kehalusan
   mesh, pemilihan permukaan, kelengkungan silinder, panjang karakteristik,
   konvensi evaluasi sifat udara, dan keseragaman suhu permukaan.
3. **Tidak ada validasi eksperimental langsung** pada Tahap 1. Validasi
   kalorimetrik direncanakan Tahap 2 (2027).
4. **Kondisi steady-state.** Dinamika transien (pemanasan awal, siklus on-off
   termostat) tidak dimodelkan.
5. **Casing dan pegangan plastik** (ABS PC) dimodelkan sebagai solid namun tidak
   dianalisis sebagai jalur rugi panas utama karena konduktivitasnya rendah.
        """
    )

st.markdown("---")
st.caption(
    "Penelitian Hibah Internal LPPM UMB 2026 · Bakti Alpihuda · Teknik Mesin UMB · "
    "Metodologi: SolidWorks Flow Simulation (FVM, k-ε Lam-Bremhorst), "
    "Churchill & Chu (1975), ISO 15686-5:2017 · "
    "Data simulasi 8 Agustus 2026"
)
