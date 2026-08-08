"""
lcc_optimizer.py
================
Analisis CHT-LCC Glasswool untuk Panci Listrik Mini Q2-8012
Penelitian Hibah Internal LPPM UMB 2026
Dosen: Bakti Alpihuda

Alur kerja:
  1. Baca data simulasi CHT dari SolidWorks (data_CHT_hasil.csv)
  2. Regresi Q(L) model resistansi seri — kurva perpindahan kalor vs tebal glasswool
  3. Hitung Life Cycle Cost (LCC) per tahun operasi (ISO 15686-5)
  4. Optimasi: cari L* yang meminimalkan LCC_total(L)
  5. Analisis sensitivitas (OAT ±20%)
  6. Monte Carlo 10.000 skenario
  7. Output: tabel ringkasan + grafik PNG

Jalankan:
  pip install numpy scipy matplotlib pandas
  python lcc_optimizer.py
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import minimize_scalar, brentq, curve_fit
from scipy.stats import norm

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER TETAP — SEMUA TERVERIFIKASI (diaudit & diperbarui 8 Agu 2026)
# ─────────────────────────────────────────────────────────────────────────────
#
# CATATAN AUDIT 8 Agu 2026: nilai lama di script ini TIDAK cocok dgn proposal
# Tabel 9 dan sebagian sudah usang. Semua diganti dgn nilai terverifikasi:
#   - Tarif: script lama Rp1.699,53 (R-2 2024) -> Rp1.444,70 (R-1/1300VA, TW-III 2026)
#   - Jam operasi: script lama 4 jam/hari -> 1 jam/hari (365 jam/thn, proposal §2.5.2)
#   - Diskonto: proposal 4,5% (proksi Q1 2026) -> 5,75% (BI-Rate resmi 22 Jul 2026)
#   - Inflasi tarif: script lama 3,5% -> 3,0% (proposal; inflasi umum BPS Jul 2026 = 2,88%)
#   - Harga glasswool: script lama Rp3.500/mm/unit -> Rp4.500/m2/mm (proposal, survei pasar)
#   - Biaya pasang: script lama Rp15.000 tetap -> markup 1,2 x C_inv (proposal Tabel 9)

# Tarif & Operasi
TARIF_KWH    = 1_444.70   # Rp/kWh — R-1/TR 1.300 VA, PLN Triwulan III 2026 (Permen ESDM 8/2025)
JAM_OPERASI  = 1.0        # jam/hari — proposal §2.5.2: t_op = 365 jam/tahun
HARI_TAHUN   = 365        # hari

# LCC Finansial (ISO 15686-5)
DISCOUNT_RATE = 0.0575    # 5,75 % — BI-Rate resmi per 22 Jul 2026 (bi.go.id, TERVERIFIKASI)
                          # Proposal menulis 4,5% (proksi Q1 2026) — sudah usang, BI naik
                          # bertahap: 4,75% (Mar-Apr) -> 5,25% (Mei) -> 5,50% -> 5,75% (Jun-Jul)
                          # Nilai 4,5% tetap diuji di analisis sensitivitas.
INFLASI_TARIF = 0.030     # 3,0 %/tahun — proposal Tabel 9 (inflasi umum BPS Jul 2026: 2,88% y-o-y)
UMUR_ANALISIS = 5         # tahun — proposal

# Biaya Investasi Glasswool — proposal Tabel 9 (survei 3 toko Tasikmalaya + 2 marketplace, Mei 2026)
HARGA_GW_PER_M2_MM = 4_500  # Rp per m2 per mm ketebalan
MARKUP_PASANG      = 1.2    # faktor markup biaya pemasangan (1,2 x C_inv material)

# Geometri selimut glasswool (untuk hitung luas material) — geometri koreksi 2026-08-06
R_LUAR_WADAH = 0.060      # m — radius luar wadah SS (tempat glasswool menempel)
TINGGI_WADAH = 0.110      # m — tinggi selimut glasswool

# Daya pemanas (dari proposal — label produk, PERLU VERIFIKASI fisik)
Q_HEATER_W = 330.0        # Watt

# Rentang variasi ketebalan glasswool
L_MIN = 0.0               # mm
L_MAX = 20.0              # mm

# File paths (relatif terhadap script ini)
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_FILE  = os.path.join(BASE_DIR, "data_CHT_hasil.csv")
OUT_DIR    = os.path.join(BASE_DIR, "output")

os.makedirs(OUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# 1. BACA DATA CHT
# ─────────────────────────────────────────────────────────────────────────────

def baca_data_cht(filepath: str) -> pd.DataFrame:
    """Baca CSV hasil simulasi; validasi tidak ada TBD."""
    df = pd.read_csv(filepath)

    if "TBD" in df["Q_Watt"].astype(str).values:
        print("\n" + "="*60)
        print("PERINGATAN: Data simulasi belum lengkap!")
        print("Beberapa nilai Q masih 'TBD'.")
        print()
        print("Cara mengisi:")
        print("  1. Jalankan Macro 03 di SolidWorks untuk tiap konfigurasi K0-K4")
        print("  2. Catat nilai 'Heat Transfer Rate [W]' dari Goals")
        print("  3. Jalankan Macro 04 untuk auto-export ke CSV ini")
        print("  4. ATAU edit manual: buka data_CHT_hasil.csv, ganti TBD")
        print()
        print("Contoh isi CSV yang benar:")
        print("  K0_NoInsulation,0,45.23,terverifikasi")
        print("  K1_GW5mm,5,28.71,terverifikasi")
        print("  ...")
        print()
        print("Menjalankan mode DEMO dengan data estimasi...")
        print("="*60 + "\n")

        # Mode demo dengan data estimasi (JANGAN dipakai sebagai data penelitian)
        df = pd.DataFrame({
            "Konfigurasi": ["K0_NoInsulation","K1_GW5mm","K2_GW10mm","K3_GW15mm","K4_GW20mm"],
            "L_mm":        [0, 5, 10, 15, 20],
            "Q_Watt":      [45.5, 28.3, 19.1, 14.2, 11.0],   # ESTIMASI — bukan data nyata
            "Catatan":     ["DEMO"]*5
        })
        df._demo_mode = True
    else:
        df["Q_Watt"] = pd.to_numeric(df["Q_Watt"], errors="coerce")
        if df["Q_Watt"].isna().any():
            raise ValueError("Ada nilai Q tidak bisa dikonversi ke angka. Periksa CSV.")
        df._demo_mode = False

    df["L_mm"] = pd.to_numeric(df["L_mm"])
    df = df.sort_values("L_mm").reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. REGRESI Q(L) — MODEL RESISTANSI SERI
# ─────────────────────────────────────────────────────────────────────────────

def model_resistansi(L, Q_inf, A, B):
    """Model resistansi seri: Q(L) = Q_inf + A/(B+L).

    Q_inf = asimtot (batas bawah rugi panas) — secara fisis = rugi panas lewat
    TUTUP yang tidak diinsulasi, tidak bisa dikurangi berapa pun tebal glasswool
    dinding. A/(B+L) = komponen dinding yang menurun seiring tebal insulasi.
    """
    return Q_inf + A / (B + L)


def regresi_cht(df: pd.DataFrame, derajat: int = 2):
    """
    Fit Q(L) dengan model RESISTANSI SERI (bukan polinomial).

    CATATAN AUDIT 8 Agu 2026 — model diganti dari polinomial derajat 2:
    Perbandingan pada data K0-K4 aktual (23,192 / 9,439 / 7,654 / 6,830 / 6,808 W):

      Model                          R2        R2adj    RMSE    Perilaku fisis
      Polinomial derajat 2        0,9282    0,8564    1,682   NAIK setelah L=14,36mm
      Polinomial derajat 3        0,9915    0,9659    0,580   NEGATIF di L=25mm
      Resistansi seri Qinf+A/(B+L) 0,9997   0,9988    0,109   monoton turun -> asimtot
      Eksponensial Qinf+A*exp(-kL) 0,9993   0,9970    0,171   asimtot terlalu tinggi

    Polinomial derajat 2 TIDAK dipakai: selain R2 terendah, kurvanya berbalik NAIK
    setelah 14,36mm (mencapai 58,6 W di L=40mm) — tidak fisis & membuat optimasi LCC
    keliru. Model resistansi seri sesuai fisika (resistansi termal seri konduksi-konveksi)
    dan cocok dgn temuan bahwa tutup tanpa insulasi jadi bottleneck (asimtot).

    Parameter `derajat` dipertahankan utk kompatibilitas API, tidak dipakai.
    Kembalikan (koef, fungsi_Q, R2) — `fungsi_Q` callable seperti np.poly1d.
    """
    L = df["L_mm"].values.astype(float)
    Q = df["Q_Watt"].values.astype(float)

    popt, _ = curve_fit(model_resistansi, L, Q,
                        p0=[Q.min() * 0.9, (Q.max() - Q.min()) * 5.0, 1.5],
                        maxfev=50000)

    fungsi_Q = lambda x: model_resistansi(np.asarray(x, dtype=float), *popt)

    Q_pred = fungsi_Q(L)
    SS_res = np.sum((Q - Q_pred) ** 2)
    SS_tot = np.sum((Q - Q.mean()) ** 2)
    R2 = 1 - SS_res / SS_tot if SS_tot > 0 else 0.0

    return popt, fungsi_Q, R2


# ─────────────────────────────────────────────────────────────────────────────
# 3. MODEL LCC (ISO 15686-5)
# ─────────────────────────────────────────────────────────────────────────────

def biaya_energi_tahunan(Q_loss_W: float,
                          tarif: float = TARIF_KWH,
                          jam: float = JAM_OPERASI,
                          hari: float = HARI_TAHUN) -> float:
    """
    Konversi heat loss (W) → biaya energi per tahun (Rp).
    Asumsi: Q_loss adalah daya terbuang yang seharusnya bisa dihemat.
    Energi terbuang = Q_loss_W × jam/hari × hari/tahun → kWh/tahun
    """
    energi_kwh = Q_loss_W * jam * hari / 1000.0
    return energi_kwh * tarif


def npv_energi(Q_loss_W: float,
               rate: float = DISCOUNT_RATE,
               inflasi: float = INFLASI_TARIF,
               n_tahun: int = UMUR_ANALISIS,
               tarif: float = TARIF_KWH,
               jam: float = JAM_OPERASI) -> float:
    """
    NPV biaya energi selama n_tahun dengan pertumbuhan tarif = inflasi.
    NPV = Σ_{t=1}^{n} [Biaya_t / (1+r)^t]
    Biaya_t = Biaya_0 × (1+g)^{t-1}
    """
    biaya_0 = biaya_energi_tahunan(Q_loss_W, tarif=tarif, jam=jam)
    total = 0.0
    for t in range(1, n_tahun + 1):
        biaya_t = biaya_0 * ((1 + inflasi) ** (t - 1))
        total += biaya_t / ((1 + rate) ** t)
    return total


def luas_selimut(L_mm: float) -> float:
    """Luas selimut glasswool (m2) — silinder pd radius rata-rata + 2 cincin annulus.

    Glasswool membungkus dinding samping saja (bukan alas/tutup) — sesuai keputusan
    metodologi §2.6 poin 7. Radius dalam = radius luar wadah (60mm), radius luar
    = 60mm + L. Luas dihitung pd radius rata-rata (representasi volume material).
    """
    if L_mm <= 0:
        return 0.0
    L_m = L_mm / 1000.0
    r_in, r_out = R_LUAR_WADAH, R_LUAR_WADAH + L_m
    r_avg = 0.5 * (r_in + r_out)
    A_sisi = 2 * np.pi * r_avg * TINGGI_WADAH          # selimut silinder
    A_cincin = 2 * np.pi * (r_out**2 - r_in**2)        # 2 annulus (atas + bawah)
    return A_sisi + A_cincin


def biaya_investasi(L_mm: float,
                     harga_per_m2_mm: float = HARGA_GW_PER_M2_MM,
                     markup: float = MARKUP_PASANG) -> float:
    """Biaya investasi glasswool (Rp) = material x markup pemasangan.

    Material: luas selimut (m2) x tebal (mm) x harga (Rp/m2/mm) — proposal Tabel 9.
    Pemasangan: faktor markup 1,2 x biaya material (proposal Tabel 9).
    """
    if L_mm <= 0:
        return 0.0
    c_material = luas_selimut(L_mm) * L_mm * harga_per_m2_mm
    return c_material * markup


def lcc_total(L_mm: float,
               poly,
               rate: float = DISCOUNT_RATE,
               inflasi: float = INFLASI_TARIF,
               n_tahun: int = UMUR_ANALISIS,
               tarif: float = TARIF_KWH,
               jam: float = JAM_OPERASI,
               harga_per_m2_mm: float = HARGA_GW_PER_M2_MM) -> float:
    """
    LCC_total(L) = Investasi(L) + NPV_Energi(Q(L))
    Minimal di L* (titik optimum).
    """
    Q = float(poly(L_mm))
    Q = max(Q, 0.1)   # cegah negatif dari ekstrapolasi

    invest = biaya_investasi(L_mm, harga_per_m2_mm=harga_per_m2_mm)
    npv_e  = npv_energi(Q, rate=rate, inflasi=inflasi, n_tahun=n_tahun,
                         tarif=tarif, jam=jam)
    return invest + npv_e


# ─────────────────────────────────────────────────────────────────────────────
# 4. OPTIMASI L*
# ─────────────────────────────────────────────────────────────────────────────

def optimasi_lcc(poly,
                  rate=DISCOUNT_RATE, inflasi=INFLASI_TARIF, n_tahun=UMUR_ANALISIS,
                  tarif=TARIF_KWH, jam=JAM_OPERASI, harga_per_m2_mm=HARGA_GW_PER_M2_MM):
    """
    Cari L* dengan scipy.optimize.minimize_scalar (bounded).
    Cross-check dengan brentq pada turunan numerik.
    """
    f = lambda L: lcc_total(L, poly, rate, inflasi, n_tahun, tarif, jam, harga_per_m2_mm)

    # Metode 1: minimize_scalar
    res = minimize_scalar(f, bounds=(L_MIN, L_MAX), method="bounded",
                          options={"xatol": 1e-4})
    L_opt_ms   = res.x
    LCC_opt_ms = res.fun

    # Metode 2: brentq pada turunan numerik (cross-check)
    dL = 0.01
    dfdL = lambda L: (f(L + dL) - f(L - dL)) / (2 * dL)

    try:
        f_lo = dfdL(L_MIN + dL)
        f_hi = dfdL(L_MAX - dL)
        if f_lo * f_hi < 0:   # tanda berbeda → ada akar di dalam
            L_opt_bq = brentq(dfdL, L_MIN + dL, L_MAX - dL, xtol=1e-4)
        else:
            L_opt_bq = L_opt_ms   # fallback ke minimize_scalar
    except Exception:
        L_opt_bq = L_opt_ms

    return L_opt_ms, LCC_opt_ms, L_opt_bq


# ─────────────────────────────────────────────────────────────────────────────
# 5. ANALISIS SENSITIVITAS (OAT)
# ─────────────────────────────────────────────────────────────────────────────

SENSITIVITY_PARAMS = {
    "Tarif Listrik":   ("tarif",       TARIF_KWH,    0.20),
    "Discount Rate":   ("rate",        DISCOUNT_RATE, 0.02),   # ±2 pp absolut
    "Inflasi Tarif":   ("inflasi",     INFLASI_TARIF, 0.015),  # ±1.5 pp absolut
    "Harga Glasswool": ("harga_per_m2_mm",HARGA_GW_PER_M2_MM, 0.20),
    "Jam Operasi":     ("jam",         JAM_OPERASI,  0.50),    # ±50%
}

def analisis_sensitivitas(poly) -> pd.DataFrame:
    """
    One-At-a-Time (OAT): variasikan setiap parameter ±variasi,
    catat perubahan L* dan LCC*.
    """
    base_params = {
        "rate": DISCOUNT_RATE, "inflasi": INFLASI_TARIF,
        "n_tahun": UMUR_ANALISIS, "tarif": TARIF_KWH,
        "jam": JAM_OPERASI, "harga_per_m2_mm": HARGA_GW_PER_M2_MM
    }

    L_base, LCC_base, _ = optimasi_lcc(poly, **base_params)

    rows = []
    for label, (key, base_val, delta) in SENSITIVITY_PARAMS.items():
        for sign, tag in [(+1, "Naik"), (-1, "Turun")]:
            if key in ("rate", "inflasi"):
                # ±pp absolut
                new_val = base_val + sign * delta
            else:
                new_val = base_val * (1 + sign * delta)

            params = {**base_params, key: new_val}
            L_opt, LCC_opt, _ = optimasi_lcc(poly, **params)
            delta_L   = L_opt   - L_base
            delta_LCC = (LCC_opt - LCC_base) / LCC_base * 100

            rows.append({
                "Parameter":    label,
                "Arah":         tag,
                "Nilai Baru":   round(new_val, 4),
                "L* (mm)":      round(L_opt, 2),
                "dLCC (%)":     round(delta_LCC, 2),
                "dL* (mm)":     round(delta_L, 2),
            })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 6. MONTE CARLO
# ─────────────────────────────────────────────────────────────────────────────

def monte_carlo(poly, n_sim: int = 10_000, seed: int = 42) -> dict:
    """
    10.000 skenario dengan distribusi normal ±1σ untuk setiap parameter.
    σ dipilih = ½ × range variasi OAT (konsisten).
    """
    rng = np.random.default_rng(seed)

    tarif_mc     = rng.normal(TARIF_KWH,    TARIF_KWH * 0.10,      n_sim)
    rate_mc      = rng.normal(DISCOUNT_RATE, 0.01,                  n_sim)
    inflasi_mc   = rng.normal(INFLASI_TARIF, 0.0075,                n_sim)
    harga_mc     = rng.normal(HARGA_GW_PER_M2_MM, HARGA_GW_PER_M2_MM*0.10, n_sim)
    jam_mc       = rng.normal(JAM_OPERASI,    JAM_OPERASI * 0.25,   n_sim)

    # Clamp supaya tidak negatif
    tarif_mc   = np.clip(tarif_mc,   500,   5000)
    rate_mc    = np.clip(rate_mc,    0.01,  0.15)
    inflasi_mc = np.clip(inflasi_mc, 0.001, 0.10)
    harga_mc   = np.clip(harga_mc,   1000,  12000)
    jam_mc     = np.clip(jam_mc,     0.5,   12)

    L_opts   = np.zeros(n_sim)
    LCC_opts = np.zeros(n_sim)

    for i in range(n_sim):
        L_opt, LCC_opt, _ = optimasi_lcc(
            poly,
            rate=float(rate_mc[i]),
            inflasi=float(inflasi_mc[i]),
            tarif=float(tarif_mc[i]),
            jam=float(jam_mc[i]),
            harga_per_m2_mm=float(harga_mc[i])
        )
        L_opts[i]   = L_opt
        LCC_opts[i] = LCC_opt

    return {
        "L_opts":        L_opts,
        "LCC_opts":      LCC_opts,
        "L_mean":        np.mean(L_opts),
        "L_std":         np.std(L_opts),
        "L_p5":          np.percentile(L_opts, 5),
        "L_p95":         np.percentile(L_opts, 95),
        "LCC_mean":      np.mean(LCC_opts),
        "LCC_std":       np.std(LCC_opts),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. VISUALISASI
# ─────────────────────────────────────────────────────────────────────────────

def buat_grafik(df, poly, R2, L_opt, LCC_opt, df_sens, mc_result):
    """Buat 4-panel figure dan simpan ke output/."""
    L_range = np.linspace(L_MIN, L_MAX, 200)
    Q_curve = poly(L_range)
    Q_curve = np.maximum(Q_curve, 0)

    LCC_curve = np.array([
        lcc_total(l, poly) for l in L_range
    ])

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(
        "CHT-LCC Glasswool — Panci Listrik Mini Q2-8012\n"
        "Penelitian Hibah Internal LPPM UMB 2026",
        fontsize=14, fontweight="bold", y=0.98
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.35)

    # Panel 1: Q(L) regresi
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(df["L_mm"], df["Q_Watt"], color="red", zorder=5, s=60,
                label="Data simulasi CHT")
    ax1.plot(L_range, Q_curve, "b-", linewidth=2,
             label=f"Regresi resistansi seri (R²={R2:.4f})")
    ax1.axvline(L_opt, color="green", linestyle="--", linewidth=1.5,
                label=f"L* = {L_opt:.1f} mm")
    ax1.set_xlabel("Ketebalan Glasswool L (mm)")
    ax1.set_ylabel("Heat Transfer Rate Q (W)")
    ax1.set_title("Panel 1: Kurva Q vs L")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Panel 2: LCC(L)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(L_range, LCC_curve / 1000, "purple", linewidth=2,
             label="LCC total")
    invest_curve = np.array([biaya_investasi(l) for l in L_range])
    npv_curve    = np.array([
        npv_energi(float(max(poly(l), 0.1))) for l in L_range
    ])
    ax2.plot(L_range, invest_curve / 1000, "g--", linewidth=1.5,
             label="Investasi glasswool")
    ax2.plot(L_range, npv_curve / 1000, "r--", linewidth=1.5,
             label="NPV energi")
    ax2.axvline(L_opt, color="black", linestyle=":", linewidth=2,
                label=f"L* = {L_opt:.1f} mm\nLCC* = Rp {LCC_opt/1000:.1f}k")
    ax2.set_xlabel("Ketebalan Glasswool L (mm)")
    ax2.set_ylabel("Biaya (×Rp 1.000)")
    ax2.set_title("Panel 2: Life Cycle Cost vs L")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Panel 3: Tornado chart sensitivitas
    ax3 = fig.add_subplot(gs[1, 0])
    df_naik  = df_sens[df_sens["Arah"] == "Naik"].set_index("Parameter")
    df_turun = df_sens[df_sens["Arah"] == "Turun"].set_index("Parameter")
    params_list = list(SENSITIVITY_PARAMS.keys())
    y_pos = np.arange(len(params_list))

    for idx, param in enumerate(params_list):
        delta_up   = df_naik.loc[param, "dLCC (%)"]   if param in df_naik.index   else 0
        delta_down = df_turun.loc[param, "dLCC (%)"] if param in df_turun.index else 0
        color_up   = "salmon"  if delta_up   > 0 else "lightblue"
        color_down = "lightblue" if delta_down < 0 else "salmon"
        ax3.barh(idx + 0.2, delta_up,   height=0.4, color=color_up,   label="_")
        ax3.barh(idx - 0.2, delta_down, height=0.4, color=color_down, label="_")

    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(params_list, fontsize=9)
    ax3.axvline(0, color="black", linewidth=1)
    ax3.set_xlabel("Delta LCC (%)")
    ax3.set_title("Panel 3: Sensitivitas OAT (Delta LCC %)")
    ax3.grid(True, axis="x", alpha=0.3)
    from matplotlib.patches import Patch
    ax3.legend(handles=[Patch(color="salmon", label="Naik"),
                         Patch(color="lightblue", label="Turun")],
               fontsize=8, loc="lower right")

    # Panel 4: Distribusi Monte Carlo L*
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.hist(mc_result["L_opts"], bins=50, color="steelblue", edgecolor="white",
             alpha=0.75, density=True)
    ax4.axvline(mc_result["L_mean"], color="red", linewidth=2,
                label=f"Mean = {mc_result['L_mean']:.2f} mm")
    ax4.axvline(mc_result["L_p5"],  color="orange", linestyle="--",
                label=f"P5 = {mc_result['L_p5']:.2f} mm")
    ax4.axvline(mc_result["L_p95"], color="orange", linestyle="--",
                label=f"P95 = {mc_result['L_p95']:.2f} mm")

    # overlay distribusi normal
    x_norm = np.linspace(mc_result["L_opts"].min(), mc_result["L_opts"].max(), 200)
    ax4.plot(x_norm,
             norm.pdf(x_norm, mc_result["L_mean"], mc_result["L_std"]),
             "r-", linewidth=1.5, alpha=0.7)

    ax4.set_xlabel("L* Optimal (mm)")
    ax4.set_ylabel("Densitas")
    ax4.set_title(f"Panel 4: Monte Carlo (n={len(mc_result['L_opts']):,})")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    out_path = os.path.join(OUT_DIR, "CHT_LCC_Analysis.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Grafik disimpan: {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# 8. MAIN
# ─────────────────────────────────────────────────────────────────────────────

def cetak_ringkasan(df, R2, L_opt, LCC_opt, L_bq, df_sens, mc):
    """Cetak ringkasan lengkap ke konsol."""
    demo_note = ""
    try:
        if df._demo_mode:
            demo_note = " *** MODE DEMO — bukan data nyata ***"
    except AttributeError:
        pass

    print()
    print("=" * 65)
    print(f"  CHT-LCC GLASSWOOL — HASIL ANALISIS{demo_note}")
    print("=" * 65)

    print("\n[1] DATA SIMULASI CHT")
    print(df[["Konfigurasi","L_mm","Q_Watt"]].to_string(index=False))

    print(f"\n[2] REGRESI Q(L) - Model Resistansi Seri Q = Q_inf + A/(B+L)")
    print(f"    R² = {R2:.5f}")
    if R2 < 0.99:
        print("    PERINGATAN: R² < 0.99 — periksa kualitas data simulasi")

    print(f"\n[3] OPTIMASI LCC")
    print(f"    L* (minimize_scalar) = {L_opt:.2f} mm")
    print(f"    L* (brentq cross-chk)= {L_bq:.2f} mm")
    print(f"    LCC*(L*) total       = Rp {LCC_opt:,.0f}")

    _, fQ_tmp, _ = regresi_cht(df)
    LCC_K0 = lcc_total(0.0, fQ_tmp)
    penghematan = LCC_K0 - LCC_opt
    print(f"    LCC K0 (tanpa insulasi)= Rp {LCC_K0:,.0f}")
    print(f"    Penghematan LCC       = Rp {penghematan:,.0f} "
          f"({penghematan/LCC_K0*100:.1f}%)")

    print(f"\n[4] SENSITIVITAS OAT")
    print(df_sens.to_string(index=False))

    print(f"\n[5] MONTE CARLO (n=10.000, seed=42)")
    print(f"    L* mean  = {mc['L_mean']:.2f} mm")
    print(f"    L* std   = {mc['L_std']:.2f} mm")
    print(f"    L* P5–P95= [{mc['L_p5']:.2f}, {mc['L_p95']:.2f}] mm")
    print(f"    LCC mean = Rp {mc['LCC_mean']:,.0f}")
    print(f"    LCC std  = Rp {mc['LCC_std']:,.0f}")

    print()


def simpan_ringkasan_csv(df_sens, mc, L_opt, LCC_opt, R2):
    """Simpan ringkasan ke CSV untuk referensi laporan."""
    summary = {
        "R2_regresi":    [round(R2, 5)],
        "L_optimal_mm":  [round(L_opt, 2)],
        "LCC_optimal_Rp":[round(LCC_opt, 0)],
        "MC_L_mean":     [round(mc["L_mean"], 2)],
        "MC_L_std":      [round(mc["L_std"], 2)],
        "MC_L_P5":       [round(mc["L_p5"], 2)],
        "MC_L_P95":      [round(mc["L_p95"], 2)],
        "MC_LCC_mean":   [round(mc["LCC_mean"], 0)],
    }
    df_summary = pd.DataFrame(summary)
    out_csv = os.path.join(OUT_DIR, "ringkasan_LCC.csv")
    df_summary.to_csv(out_csv, index=False)

    out_sens = os.path.join(OUT_DIR, "sensitivitas_OAT.csv")
    df_sens.to_csv(out_sens, index=False)

    print(f"  Ringkasan CSV : {out_csv}")
    print(f"  Sensitivitas  : {out_sens}")


def main():
    print("\nMembaca data CHT dari:", DATA_FILE)
    df = baca_data_cht(DATA_FILE)

    print("Menghitung regresi (model resistansi seri)...")
    koef, poly, R2 = regresi_cht(df)

    print("Optimasi LCC...")
    L_opt, LCC_opt, L_bq = optimasi_lcc(poly)

    print("Analisis sensitivitas OAT...")
    df_sens = analisis_sensitivitas(poly)

    print("Monte Carlo 10.000 skenario...")
    mc = monte_carlo(poly)

    cetak_ringkasan(df, R2, L_opt, LCC_opt, L_bq, df_sens, mc)

    print("Membuat grafik...")
    buat_grafik(df, poly, R2, L_opt, LCC_opt, df_sens, mc)

    print("Menyimpan CSV ringkasan...")
    simpan_ringkasan_csv(df_sens, mc, L_opt, LCC_opt, R2)

    print("\nSELESAI. Semua output ada di folder: output/")
    print("Grafik utama: output/CHT_LCC_Analysis.png")
    print()

    if hasattr(df, "_demo_mode") and df._demo_mode:
        print("PENTING: Jalankan ulang setelah data CHT nyata diisi ke:")
        print(f"  {DATA_FILE}")
    print()


if __name__ == "__main__":
    main()
