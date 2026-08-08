"""Halaman 4 — Metode, sumber parameter, dan keterbatasan."""

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from app_core import (
    sidebar_parameter, hitung_semua, WARNA, rupiah,
    TARIF_KWH, DISCOUNT_RATE, INFLASI_TARIF, UMUR_ANALISIS,
    JAM_OPERASI, HARI_TAHUN, HARGA_GW_PER_M2_MM, MARKUP_PASANG,
)

p = sidebar_parameter()
h = hitung_semua(p)
Q_inf, A_fit, B_fit = h["koef"]

st.title("Metode dan sumber data")
st.caption("Untuk keperluan verifikasi dan penulisan laporan")

# ── Regresi ──────────────────────────────────────────────────────────────────
st.subheader("Model regresi")

kiri, kanan = st.columns([2, 3], vertical_alignment="center")
with kiri:
    with st.container(border=True):
        st.markdown("**Persamaan yang dipakai**")
        st.latex(r"Q(L) = Q_\infty + \frac{A}{B + L}")
        st.markdown(
            f"- $Q_\\infty$ = {Q_inf:.4f} W\n"
            f"- $A$ = {A_fit:.4f}\n"
            f"- $B$ = {B_fit:.4f}\n"
            f"- $R^2$ = **{h['R2']:.6f}**"
        )
with kanan:
    st.markdown(
        f"$Q_\\infty$ adalah **asimtot** — batas bawah rugi panas yang tidak "
        f"dapat dikurangi berapa pun tebal glasswool dinding, karena panas "
        f"tetap lolos lewat tutup yang tidak diinsulasi.\n\n"
        f"Model ini dipilih menggantikan polinomial derajat 2. Selain "
        f"$R^2$ lebih tinggi, polinomial berbalik **naik** setelah 14,36 mm — "
        f"secara fisika mustahil, sebab menambah insulasi tidak mungkin "
        f"menambah rugi panas."
    )

with st.container(border=True):
    st.markdown("**Perbandingan model yang diuji**")
    st.dataframe(
        pd.DataFrame({
            "Model": ["Resistansi seri (dipakai)", "Eksponensial",
                      "Polinomial derajat 3", "Polinomial derajat 2"],
            "R²": [0.9997, 0.9993, 0.9915, 0.9282],
            "RMSE": [0.109, 0.171, 0.580, 1.682],
            "Perilaku fisis": [
                "Monoton turun menuju asimtot — sesuai fisika",
                "Asimtot terlalu tinggi",
                "Bernilai negatif pada L = 25 mm",
                "Berbalik naik setelah L = 14,36 mm",
            ],
        }),
        hide_index=True, width="stretch",
        column_config={
            "R²": st.column_config.NumberColumn(format="%.4f"),
            "RMSE": st.column_config.NumberColumn(format="%.3f"),
        },
    )

# ── Kualitas fit ─────────────────────────────────────────────────────────────
st.subheader("Ketepatan model terhadap data simulasi")

df_fit = h["df"].copy()
df_fit["Q model (W)"] = np.round(h["fQ"](df_fit["L_mm"].values), 3)
df_fit["Selisih (W)"] = (df_fit["Q_Watt"] - df_fit["Q model (W)"]).round(3)
df_fit["Selisih (%)"] = (df_fit["Selisih (W)"] / df_fit["Q_Watt"] * 100).round(2)
df_fit = df_fit.rename(columns={"L_mm": "Tebal (mm)", "Q_Watt": "Q simulasi (W)"})

kiri, kanan = st.columns([3, 2])
with kiri:
    L_grid = np.linspace(0, 20, 200)
    kurva = pd.DataFrame({"L": L_grid, "Q": h["fQ"](L_grid)})
    titik = pd.DataFrame({"L": h["df"]["L_mm"], "Q": h["df"]["Q_Watt"]})

    c = (
        alt.Chart(kurva).mark_line(color=WARNA["lcc"], strokeWidth=2.5)
        .encode(x=alt.X("L:Q", title="Tebal glasswool (mm)"),
                y=alt.Y("Q:Q", title="Rugi panas (W)"))
        + alt.Chart(titik).mark_point(size=120, filled=True,
                                      color=WARNA["energi"])
        .encode(x="L:Q", y="Q:Q",
                tooltip=[alt.Tooltip("L:Q", title="Tebal (mm)"),
                         alt.Tooltip("Q:Q", title="Q simulasi (W)",
                                     format=".3f")])
        + alt.Chart(pd.DataFrame({"y": [Q_inf]}))
        .mark_rule(color=WARNA["cincin"], strokeDash=[5, 4], strokeWidth=2)
        .encode(y="y:Q")
    )
    st.altair_chart(c.properties(height=320), width="stretch")
    st.caption(
        f"Titik merah = hasil simulasi, garis ungu = model, "
        f"garis abu putus-putus = asimtot {Q_inf:.2f} W."
    )

with kanan:
    st.dataframe(
        df_fit[["Konfigurasi", "Tebal (mm)", "Q simulasi (W)",
                "Q model (W)", "Selisih (%)"]],
        hide_index=True, width="stretch",
    )
    st.download_button(
        "Unduh data (CSV)",
        data=df_fit.to_csv(index=False).encode("utf-8"),
        file_name="data_CHT_regresi.csv", mime="text/csv",
        icon=":material/download:",
    )

# ── Sumber parameter ─────────────────────────────────────────────────────────
st.subheader("Sumber parameter ekonomi")
st.caption("Seluruh nilai bawaan terverifikasi per 8 Agustus 2026")

st.dataframe(
    pd.DataFrame({
        "Parameter": ["Tarif listrik", "Suku bunga diskonto", "Inflasi tarif",
                      "Lama pakai", "Harga glasswool", "Markup pemasangan",
                      "Umur analisis", "Radius luar wadah", "Tinggi wadah"],
        "Nilai bawaan": [
            f"Rp {TARIF_KWH:,.2f}/kWh",
            f"{DISCOUNT_RATE * 100:.2f}%",
            f"{INFLASI_TARIF * 100:.1f}%",
            f"{JAM_OPERASI:.0f} jam/hari ({JAM_OPERASI * HARI_TAHUN:,.0f} jam/tahun)",
            f"Rp {HARGA_GW_PER_M2_MM:,.0f}/m²/mm",
            f"{MARKUP_PASANG:.1f}× biaya material",
            f"{UMUR_ANALISIS} tahun",
            f"{p['r_luar_mm']:.0f} mm",
            f"{p['tinggi_mm']:.0f} mm",
        ],
        "Sumber": [
            "PLN R-1/TR 1.300 VA, Triwulan III 2026 (Permen ESDM 8/2025)",
            "BI-Rate resmi per 22 Juli 2026 (bi.go.id)",
            "Proposal Tabel 9 (inflasi umum BPS Juli 2026: 2,88% y-o-y)",
            "Survei pola pakai 20 penghuni kos, Mei 2026",
            "Survei 5 toko/marketplace Tasikmalaya, Mei 2026",
            "Proposal Tabel 9",
            "Garansi produsen + ekstensi empiris",
            "Geometri Q2-8012, diukur langsung dari SolidWorks",
            "Geometri Q2-8012, diukur langsung dari SolidWorks",
        ],
    }),
    hide_index=True, width="stretch",
)

if p.get("dimensi_diubah"):
    st.warning(
        "**Dimensi diubah dari panci Q2-8012.** Biaya glasswool (baris "
        "'Harga glasswool' di atas dikalikan luas selimut baru) valid untuk "
        "ukuran ini. Namun kurva rugi panas Q(L) di atas tetap dari "
        "**simulasi CHT Q2-8012 asli** dan belum disimulasikan ulang untuk "
        "geometri baru — perlakukan sebagai perkiraan, bukan hasil "
        "tervalidasi, sampai simulasi CHT untuk ukuran ini tersedia.",
        icon=":material/report:",
    )

st.warning(
    "**Perbedaan dengan proposal.** Proposal mencantumkan suku bunga 4,5% "
    "sebagai proksi BI-Rate Q1 2026. Nilai tersebut sudah berubah — BI "
    "menaikkan suku bunga bertahap hingga 5,75% (Juli 2026). Dashboard "
    "memakai nilai terbaru. Analisis sensitivitas menunjukkan perbedaan ini "
    "menggeser ketebalan optimal kurang dari 0,3 mm, sehingga **tidak "
    "mengubah kesimpulan** — namun perlu dijelaskan di laporan.",
    icon=":material/report:",
)

# ── Keterbatasan ─────────────────────────────────────────────────────────────
st.subheader("Keterbatasan penelitian")
st.caption("Disampaikan terbuka untuk menjaga integritas ilmiah")

batas = [
    ("Mesh independence study tidak dilaksanakan",
     "Seluruh simulasi memakai satu konfigurasi mesh (Global Level 6 + Local "
     "Refinement 3, 222.190 sel). Kredibilitas didukung validasi K0 terhadap "
     "korelasi Churchill-Chu (galat 3,71%, kriteria ≤10%) dan reprodusibilitas "
     "hasil pada pengulangan simulasi."),
    ("Validasi Churchill-Chu tidak terpenuhi pada K1–K4",
     "Selisih 15,18–50,04%, membesar sistematis seiring ketebalan insulasi. "
     "Penyebab belum teridentifikasi. Faktor yang telah diuji dan tereliminasi: "
     "radiasi, kehalusan mesh, pemilihan permukaan, kelengkungan silinder, "
     "panjang karakteristik, konvensi evaluasi sifat udara, dan keseragaman "
     "suhu permukaan."),
    ("Tidak ada validasi eksperimental langsung",
     "Tahap 1 sepenuhnya berbasis simulasi. Validasi kalorimetrik "
     "direncanakan pada Tahap 2 (2027)."),
    ("Kondisi steady-state",
     "Dinamika transien — pemanasan awal dan siklus on-off termostat — "
     "tidak dimodelkan."),
    ("Casing dan pegangan plastik",
     "Komponen ABS PC dimodelkan sebagai solid namun tidak dianalisis sebagai "
     "jalur rugi panas utama karena konduktivitasnya rendah."),
    ("Daya pemanas belum diverifikasi fisik",
     "Nilai 330 W diambil dari label produk. Parameter ini tidak dipakai dalam "
     "perhitungan LCC sehingga tidak memengaruhi hasil optimasi."),
]
for judul, isi in batas:
    with st.expander(judul, icon=":material/error_outline:"):
        st.write(isi)

st.subheader("Rujukan metodologi")
st.markdown(
    "- Simulasi CHT: SolidWorks Flow Simulation (metode volume hingga, "
    "model turbulensi k-ε Lam-Bremhorst)\n"
    "- Validasi konveksi alami: Churchill & Chu (1975)\n"
    "- Kerangka biaya siklus hidup: ISO 15686-5:2017\n"
    "- Data simulasi: 8 Agustus 2026, konfigurasi K0–K4"
)

st.caption(
    "Angka resmi untuk laporan sebaiknya diambil dari lcc_optimizer.py "
    "(jalankan 1_Jalankan_Analisis_LCC.bat). Dashboard ini memakai fungsi "
    "yang sama, tetapi nilainya ikut berubah saat penggeser digeser."
)
