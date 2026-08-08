"""
app_core.py
===========
Logika bersama untuk dashboard CHT-LCC Glasswool.

Semua halaman (app_pages/*.py) memakai modul ini supaya:
  - parameter sidebar hanya ditulis satu kali,
  - perhitungan berat (Monte Carlo, sensitivitas) di-cache,
  - angka di semua halaman dijamin konsisten.

Rumus TIDAK ditulis ulang di sini — semuanya diambil dari lcc_optimizer.py
supaya angka dashboard identik dengan angka laporan.
"""

import os
import sys
import numpy as np
import pandas as pd
import streamlit as st
from scipy.optimize import minimize_scalar

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from lcc_optimizer import (  # noqa: E402
    regresi_cht, lcc_total, biaya_investasi, npv_energi,
    biaya_energi_tahunan, luas_selimut,
    TARIF_KWH, DISCOUNT_RATE, INFLASI_TARIF, UMUR_ANALISIS,
    JAM_OPERASI, HARI_TAHUN, HARGA_GW_PER_M2_MM, MARKUP_PASANG,
    L_MIN, L_MAX, R_LUAR_WADAH, TINGGI_WADAH,
)

# Dimensi bawaan Q2-8012, dalam MILIMETER (lcc_optimizer pakai meter secara
# internal — konversi dilakukan di titik pemanggilan)
R_LUAR_WADAH_MM_DEFAULT = R_LUAR_WADAH * 1000   # 60 mm
TINGGI_WADAH_MM_DEFAULT = TINGGI_WADAH * 1000   # 110 mm

# ─────────────────────────────────────────────────────────────────────────────
# DATA SIMULASI NYATA — SolidWorks Flow Simulation, 8 Agustus 2026
# ─────────────────────────────────────────────────────────────────────────────
DATA_CHT_DEFAULT = [
    ("K0", "Tanpa glasswool (0 mm)",  0,  23.192),
    ("K1", "Glasswool 5 mm",          5,   9.439),
    ("K2", "Glasswool 10 mm",        10,   7.654),
    ("K3", "Glasswool 15 mm",        15,   6.830),
    ("K4", "Glasswool 20 mm",        20,   6.808),
]

Q_DINDING = {0: 20.390, 5: 5.308, 10: 2.695, 15: 1.672, 20: 1.072}
Q_TUTUP   = {0: 2.801,  5: 3.983, 10: 4.820, 15: 5.017, 20: 5.503}
Q_CINCIN  = {0: 0.000,  5: 0.149, 10: 0.138, 15: 0.141, 20: 0.232}
T_DINDING = {0: 94.83,  5: 52.91, 10: 43.86, 15: 39.75, 20: 37.16}
T_TUTUP   = {0: 94.92,  5: 94.90, 10: 94.89, 15: 94.89, 20: 94.88}

# ─────────────────────────────────────────────────────────────────────────────
# KONTEKS PASAR NASIONAL — untuk skala dampak, BUKAN populasi Q2-8012 sendiri
# ─────────────────────────────────────────────────────────────────────────────
# Angka berikut adalah pasar RICE COOKER RUMAH TANGGA (1-3 liter) se-Indonesia,
# BUKAN data penjualan/populasi panci listrik mini Q2-8012 secara spesifik —
# data itu tidak tersedia publik. Dicantumkan sebagai KONTEKS SKALA PASAR alat
# masak listrik rumah tangga, bukan sebagai jumlah unit Q2-8012 yang beredar.
# Sumber: CLASP, "Indonesia Rice Cooker Market Study and Policy Analysis"
# (2021), mengutip Kementerian ESDM & survei Ipsos untuk CLASP.
RICE_COOKER_TERJUAL_2018_JUTA = 13.0     # unit/tahun, data 2018
RICE_COOKER_TERPASANG_JUTA    = 56.0     # unit sedang dipakai, estimasi 2018/2020
RICE_COOKER_PROYEKSI_2030_JUTA = 19.6    # unit/tahun, proyeksi laporan
RICE_COOKER_SUMBER = (
    "CLASP, \"Indonesia Rice Cooker Market Study and Policy Analysis\" "
    "(2021), data Kementerian ESDM & survei Ipsos"
)

# Palet warna konsisten di seluruh dashboard
WARNA = {
    "lcc":      "#7B4FBF",   # ungu  — LCC total
    "invest":   "#2E9E5B",   # hijau — investasi
    "energi":   "#D9534F",   # merah — biaya energi
    "dinding":  "#4A7FB5",   # biru  — dinding
    "tutup":    "#E8735A",   # oranye— tutup
    "cincin":   "#B8B8B8",   # abu   — cincin
    "optimum":  "#1A1A1A",   # hitam — penanda optimum
    "aksen":    "#E8A33D",   # kuning— rentang toleransi
}


def set_page(judul, ikon):
    """Konfigurasi halaman — dipanggil di tiap file halaman."""
    st.set_page_config(
        page_title=f"{judul} — CHT-LCC UMB",
        page_icon=ikon,
        layout="wide",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — parameter global, dipakai semua halaman
# ─────────────────────────────────────────────────────────────────────────────
def sidebar_parameter():
    """Render sidebar dan kembalikan dict parameter.

    Dipanggil di setiap halaman supaya slider tetap muncul di mana pun
    pengguna berada. Nilai tersimpan di session_state, jadi tidak hilang
    saat berpindah halaman.
    """
    with st.sidebar:
        st.subheader("Asumsi ekonomi")

        preset = st.segmented_control(
            "Skenario cepat",
            options=["Hemat", "Baku", "Boros"],
            default="Baku",
            help="Pilihan cepat pola pemakaian. 'Baku' = asumsi resmi penelitian "
                 "(1 jam/hari). 'Hemat' = jarang dipakai. 'Boros' = pemakaian intens.",
        )
        jam_preset = {"Hemat": 0.5, "Baku": 1.0, "Boros": 3.0}

        jam = st.slider(
            "Lama pakai per hari (jam)", 0.25, 8.0,
            jam_preset.get(preset, JAM_OPERASI), 0.25,
            help="Parameter PALING berpengaruh terhadap hasil. "
                 "Asumsi resmi penelitian: 1 jam/hari.",
        )
        st.caption(f"Setara {jam * HARI_TAHUN:,.0f} jam per tahun")

        tarif = st.number_input(
            "Tarif listrik (Rp/kWh)", 500.0, 5000.0, float(TARIF_KWH),
            step=10.0, format="%.2f",
            help="Bawaan: PLN R-1/TR 1.300 VA, Triwulan III 2026",
        )

        with st.expander("Dimensi panci", icon=":material/straighten:"):
            st.caption(
                "Bawaan = panci listrik mini Q2-8012 (radius 60 mm, "
                "tinggi 110 mm) — dimensi yang benar-benar disimulasikan."
            )
            r_luar_mm = st.number_input(
                "Radius luar wadah (mm)", 20.0, 300.0,
                float(R_LUAR_WADAH_MM_DEFAULT), step=5.0,
                help="Radius wadah stainless, tempat glasswool menempel.",
            )
            tinggi_mm = st.number_input(
                "Tinggi wadah (mm)", 20.0, 400.0,
                float(TINGGI_WADAH_MM_DEFAULT), step=5.0,
                help="Tinggi selimut glasswool (sisi samping wadah).",
            )
            dimensi_diubah = (
                abs(r_luar_mm - R_LUAR_WADAH_MM_DEFAULT) > 0.01
                or abs(tinggi_mm - TINGGI_WADAH_MM_DEFAULT) > 0.01
            )
            if dimensi_diubah:
                st.warning(
                    "Dimensi diubah dari Q2-8012. **Biaya glasswool** "
                    "(luas selimut, jadi biaya investasi) ikut menyesuaikan "
                    "dan valid untuk ukuran baru ini. Tapi **kurva rugi "
                    "panas Q(L)** tetap dari simulasi CHT Q2-8012 — untuk "
                    "panci ukuran lain itu hanya perkiraan, belum "
                    "disimulasikan ulang.",
                    icon=":material/warning:",
                )

        with st.expander("Pengaturan lanjutan", icon=":material/tune:"):
            rate = st.slider("Suku bunga diskonto (%/tahun)", 1.0, 15.0,
                             DISCOUNT_RATE * 100, 0.25) / 100
            inflasi = st.slider("Inflasi tarif (%/tahun)", 0.5, 10.0,
                                INFLASI_TARIF * 100, 0.25) / 100
            n_tahun = st.slider("Umur analisis (tahun)", 1, 15, UMUR_ANALISIS, 1)
            harga_gw = st.number_input("Harga glasswool (Rp/m²/mm)",
                                       500.0, 20000.0, float(HARGA_GW_PER_M2_MM),
                                       step=100.0)
            markup = st.slider("Markup pemasangan (× material)",
                               1.0, 2.0, float(MARKUP_PASANG), 0.05)
            n_mc = st.select_slider("Jumlah skenario Monte Carlo",
                                    options=[1000, 5000, 10000, 20000],
                                    value=10000)
            seed_mc = st.number_input("Random seed", 0, 9999, 42, 1)

        with st.expander("Data simulasi CHT", icon=":material/science:"):
            st.caption(
                "Bawaan = hasil SolidWorks Flow Simulation 8 Agu 2026. "
                "Angka adalah **rugi panas dalam Watt** — makin kecil, "
                "makin hemat. Ubah hanya bila menguji data lain."
            )
            L_vals, Q_vals, kode_vals = [], [], []
            for kode, label, L, q_def in DATA_CHT_DEFAULT:
                q = st.number_input(f"{kode} — {label} (Watt)", 0.1, 500.0,
                                    float(q_def), step=0.001, format="%.3f",
                                    key=f"q_{kode}",
                                    help="Rugi panas (laju kebocoran energi), "
                                         "satuan Watt — sama seperti daya "
                                         "lampu atau alat listrik lain.")
                kode_vals.append(kode); L_vals.append(L); Q_vals.append(q)

        if st.button("Kembalikan ke nilai bawaan",
                     icon=":material/restart_alt:", width="stretch"):
            st.session_state.clear()
            st.rerun()

    return dict(jam=jam, tarif=tarif, rate=rate, inflasi=inflasi,
                n_tahun=n_tahun, harga_gw=harga_gw, markup=markup,
                n_mc=int(n_mc), seed_mc=int(seed_mc),
                L_vals=L_vals, Q_vals=Q_vals, kode_vals=kode_vals,
                r_luar_mm=r_luar_mm, tinggi_mm=tinggi_mm,
                dimensi_diubah=dimensi_diubah)


# ─────────────────────────────────────────────────────────────────────────────
# PERHITUNGAN — di-cache supaya pindah halaman terasa instan
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, max_entries=32)
def _regresi(L_tuple, Q_tuple, kode_tuple):
    df = pd.DataFrame({"Konfigurasi": list(kode_tuple),
                       "L_mm": list(L_tuple), "Q_Watt": list(Q_tuple)})
    koef, fQ, R2 = regresi_cht(df)
    return df, tuple(koef), R2


def regresi(p):
    """Regresi Q(L). Mengembalikan (df, fungsi_Q, koef, R2)."""
    df, koef, R2 = _regresi(tuple(p["L_vals"]), tuple(p["Q_vals"]),
                            tuple(p["kode_vals"]))
    Q_inf, A, B = koef
    fQ = lambda x: Q_inf + A / (B + np.asarray(x, dtype=float))
    return df, fQ, koef, R2


def buat_lcc_fn(fQ, p):
    """Fungsi LCC(L) dengan parameter dari sidebar (termasuk dimensi panci)."""
    return lambda L: lcc_total(
        L, fQ, rate=p["rate"], inflasi=p["inflasi"], n_tahun=p["n_tahun"],
        tarif=p["tarif"], jam=p["jam"], harga_per_m2_mm=p["harga_gw"],
        r_luar_wadah=p["r_luar_mm"] / 1000.0, tinggi_wadah=p["tinggi_mm"] / 1000.0)


@st.cache_data(show_spinner=False, max_entries=32)
def _optimasi(koef, rate, inflasi, n_tahun, tarif, jam, harga_gw,
             r_luar_mm, tinggi_mm):
    Q_inf, A, B = koef
    fQ = lambda x: Q_inf + A / (B + np.asarray(x, dtype=float))
    f = lambda L: lcc_total(L, fQ, rate=rate, inflasi=inflasi, n_tahun=n_tahun,
                            tarif=tarif, jam=jam, harga_per_m2_mm=harga_gw,
                            r_luar_wadah=r_luar_mm / 1000.0,
                            tinggi_wadah=tinggi_mm / 1000.0)
    r = minimize_scalar(f, bounds=(L_MIN, L_MAX), method="bounded",
                        options={"xatol": 1e-4})

    # Rentang toleransi: L yang LCC-nya masih dalam +1% dari optimum
    L_fine = np.linspace(0.05, L_MAX, 1500)
    lcc_fine = np.array([f(l) for l in L_fine])
    m = lcc_fine <= r.fun * 1.01
    L_lo, L_hi = (float(L_fine[m].min()), float(L_fine[m].max())) if m.any() \
        else (float(r.x), float(r.x))
    return float(r.x), float(r.fun), float(f(0.0)), L_lo, L_hi


def optimasi(koef, p):
    """Cari L* optimal. Mengembalikan (L_opt, LCC_opt, LCC_K0, L_lo, L_hi)."""
    return _optimasi(tuple(koef), p["rate"], p["inflasi"], p["n_tahun"],
                     p["tarif"], p["jam"], p["harga_gw"],
                     p["r_luar_mm"], p["tinggi_mm"])


@st.cache_data(show_spinner=False, max_entries=16)
def _sensitivitas(koef, rate, inflasi, n_tahun, tarif, jam, harga_gw, LCC_opt,
                  r_luar_mm, tinggi_mm):
    Q_inf, A, B = koef
    fQ = lambda x: Q_inf + A / (B + np.asarray(x, dtype=float))
    spec = [
        ("Lama pakai per hari", "jam",             jam,      0.50),
        ("Tarif listrik",       "tarif",           tarif,    0.20),
        ("Harga glasswool",     "harga_per_m2_mm", harga_gw, 0.20),
        ("Suku bunga",          "rate",            rate,     0.02),
        ("Inflasi tarif",       "inflasi",         inflasi,  0.015),
    ]
    r_m, t_m = r_luar_mm / 1000.0, tinggi_mm / 1000.0
    rows = []
    for label, key, base, delta in spec:
        for sign, tag in ((+1, "Naik"), (-1, "Turun")):
            nv = (base + sign * delta) if key in ("rate", "inflasi") \
                else base * (1 + sign * delta)
            kw = dict(rate=rate, inflasi=inflasi, n_tahun=n_tahun,
                      tarif=tarif, jam=jam, harga_per_m2_mm=harga_gw,
                      r_luar_wadah=r_m, tinggi_wadah=t_m)
            kw[key] = nv
            r = minimize_scalar(lambda L: lcc_total(L, fQ, **kw),
                                bounds=(L_MIN, L_MAX), method="bounded")
            rows.append({"Parameter": label, "Arah": tag,
                         "Nilai baru": round(nv, 4),
                         "L* (mm)": round(r.x, 2),
                         "Perubahan LCC (%)": round((r.fun - LCC_opt) / LCC_opt * 100, 2)})
    return pd.DataFrame(rows)


def sensitivitas(koef, p, LCC_opt):
    return _sensitivitas(tuple(koef), p["rate"], p["inflasi"], p["n_tahun"],
                         p["tarif"], p["jam"], p["harga_gw"], LCC_opt,
                         p["r_luar_mm"], p["tinggi_mm"])


@st.cache_data(show_spinner=False, max_entries=16)
def _monte_carlo(koef, rate, inflasi, n_tahun, tarif, jam, harga_gw, n_mc, seed,
                 r_luar_mm, tinggi_mm):
    Q_inf, A, B = koef
    fQ = lambda x: Q_inf + A / (B + np.asarray(x, dtype=float))
    r_m, t_m = r_luar_mm / 1000.0, tinggi_mm / 1000.0
    rng = np.random.default_rng(seed)
    t = np.clip(rng.normal(tarif, tarif * 0.10, n_mc), 500, 5000)
    r_ = np.clip(rng.normal(rate, 0.01, n_mc), 0.01, 0.15)
    i_ = np.clip(rng.normal(inflasi, 0.0075, n_mc), 0.001, 0.10)
    h = np.clip(rng.normal(harga_gw, harga_gw * 0.10, n_mc), 1000, 12000)
    j = np.clip(rng.normal(jam, jam * 0.25, n_mc), 0.25, 12)

    L = np.zeros(n_mc)
    for k in range(n_mc):
        kw = dict(rate=float(r_[k]), inflasi=float(i_[k]), n_tahun=n_tahun,
                  tarif=float(t[k]), jam=float(j[k]), harga_per_m2_mm=float(h[k]),
                  r_luar_wadah=r_m, tinggi_wadah=t_m)
        L[k] = minimize_scalar(lambda x: lcc_total(x, fQ, **kw),
                               bounds=(L_MIN, L_MAX), method="bounded").x
    return L


def monte_carlo(koef, p):
    return _monte_carlo(tuple(koef), p["rate"], p["inflasi"], p["n_tahun"],
                        p["tarif"], p["jam"], p["harga_gw"],
                        p["n_mc"], p["seed_mc"], p["r_luar_mm"], p["tinggi_mm"])


def hitung_semua(p):
    """Satu panggilan untuk seluruh perhitungan inti sebuah halaman."""
    df, fQ, koef, R2 = regresi(p)
    L_opt, LCC_opt, LCC_K0, L_lo, L_hi = optimasi(koef, p)

    Q_k0 = float(fQ(0.0))
    Q_opt = float(fQ(L_opt))
    hemat_thn1 = (biaya_energi_tahunan(Q_k0, tarif=p["tarif"], jam=p["jam"])
                  - biaya_energi_tahunan(Q_opt, tarif=p["tarif"], jam=p["jam"]))
    inv_opt = biaya_investasi(L_opt, harga_per_m2_mm=p["harga_gw"],
                              markup=p["markup"],
                              r_luar_wadah=p["r_luar_mm"] / 1000.0,
                              tinggi_wadah=p["tinggi_mm"] / 1000.0)
    payback = inv_opt / hemat_thn1 if hemat_thn1 > 0 else float("inf")

    return dict(df=df, fQ=fQ, koef=koef, R2=R2, L_opt=L_opt, LCC_opt=LCC_opt,
                LCC_K0=LCC_K0, L_lo=L_lo, L_hi=L_hi, Q_opt=Q_opt, Q_k0=Q_k0,
                payback=payback, inv_opt=inv_opt, hemat_thn1=hemat_thn1)


def tebal_komersial(L_opt):
    """Ketebalan yang benar-benar dijual di pasaran, terdekat ke L*."""
    opsi = [5, 10, 15, 20]
    return min(opsi, key=lambda x: abs(x - L_opt))


def rupiah(x):
    """Format rupiah ringkas, mudah dibaca."""
    if not np.isfinite(x):
        return "—"
    return f"Rp {x:,.0f}".replace(",", ".")
