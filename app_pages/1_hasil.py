"""Halaman 1 — Hasil utama: jawaban ringkas + visual bentuk panci."""

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from app_core import (
    sidebar_parameter, hitung_semua, buat_lcc_fn, tebal_komersial, rupiah,
    biaya_investasi, WARNA, HARI_TAHUN,
)
from app_visual3d import diagram_panci_3d

p = sidebar_parameter()
h = hitung_semua(p)
lcc_fn = buat_lcc_fn(h["fQ"], p)

L_opt, LCC_opt, LCC_K0 = h["L_opt"], h["LCC_opt"], h["LCC_K0"]
L_pasar = tebal_komersial(L_opt)
hemat = LCC_K0 - LCC_opt

st.title("Hasil analisis")
st.caption(
    "Optimasi ketebalan glasswool panci listrik mini Q2-8012 · "
    "Hibah Internal LPPM UMB 2026 · Bakti Alpihuda"
)

# ── Jawaban utama ────────────────────────────────────────────────────────────
with st.container(border=True):
    kiri, kanan = st.columns([2, 3], vertical_alignment="center")

    with kiri:
        st.markdown("#### Rekomendasi")
        st.markdown(
            f"# :green[{L_pasar} mm]",
        )
        st.caption(
            f"Perhitungan menghasilkan optimum {L_opt:.2f} mm. "
            f"Ukuran {L_pasar} mm dipilih karena tersedia di pasaran, "
            f"dengan selisih biaya hanya "
            f"{abs(lcc_fn(L_pasar) - LCC_opt) / LCC_opt * 100:.2f}% dari optimum."
        )

    with kanan:
        st.markdown("#### Yang Anda dapat dengan memasangnya")
        teks_payback = (f"**{h['payback']:.1f} tahun**"
                        if np.isfinite(h["payback"]) else "—")
        st.markdown(
            f"- Biaya 5 tahun turun dari **{rupiah(LCC_K0)}** "
            f"menjadi **{rupiah(LCC_opt)}**\n"
            f"- Hemat **{rupiah(hemat)}** "
            f"(**{hemat / LCC_K0 * 100:.0f}%**)\n"
            f"- Modal kembali dalam {teks_payback}"
        )

# ── Angka ringkas ────────────────────────────────────────────────────────────
with st.container(horizontal=True):
    st.metric("Ketebalan optimal", f"{L_opt:.2f} mm", border=True,
              help="Ketebalan yang membuat total biaya paling rendah")
    st.metric("Total biaya 5 tahun", rupiah(LCC_opt), border=True,
              help="Investasi glasswool + biaya listrik terbuang, nilai sekarang")
    st.metric("Penghematan", rupiah(hemat),
              f"{hemat / LCC_K0 * 100:.1f}%", border=True,
              help="Dibanding tanpa glasswool sama sekali")
    st.metric("Balik modal",
              f"{h['payback']:.1f} tahun" if np.isfinite(h["payback"]) else "—",
              border=True,
              help="Biaya pasang dibagi penghematan listrik tahun pertama")
    st.metric("Ketepatan model", f"{h['R2']:.4f}", border=True,
              help="R² regresi — target minimal 0,99")

if h["R2"] < 0.99:
    st.warning("Ketepatan model di bawah 0,99 — periksa kualitas data simulasi.",
               icon=":material/warning:")

# Optimum menempel di batas atas rentang pencarian (20 mm) — nilai yang
# ditampilkan bukan optimum sebenarnya, dan ekstrapolasi di luar rentang
# data simulasi (K0-K4 hanya sampai 20 mm) tidak dapat dipertanggungjawabkan.
if L_opt >= 19.95:
    st.warning(
        f"**Hasil menempel di batas 20 mm.** Dengan asumsi pemakaian "
        f"{p['jam']:.2f} jam/hari, ketebalan terbaik sebenarnya berada "
        f"**di atas 20 mm** — di luar rentang yang disimulasikan "
        f"(data K0–K4 hanya sampai 20 mm). Angka {L_opt:.2f} mm di atas "
        f"adalah batas pencarian, **bukan optimum sebenarnya**. "
        f"Untuk pemakaian seintensif ini diperlukan simulasi tambahan pada "
        f"ketebalan lebih besar.",
        icon=":material/warning:",
    )

# ── Visual bentuk panci ──────────────────────────────────────────────────────
st.subheader("Bentuk panci dan ke mana panas lolos")
st.caption(
    "Model 3D berskala — **klik dan seret untuk memutar**, gulir untuk "
    "zoom. Bagian selubung dipotong supaya lapisan glasswool terlihat dari "
    "dalam. Geser penggeser untuk melihat perubahan tebal, suhu permukaan, "
    "dan besar rugi panas. Panah lebih tebal berarti rugi panas lebih besar."
)

kiri, kanan = st.columns([3, 2], vertical_alignment="top")

with kiri:
    L_lihat = st.slider("Tebal glasswool yang ditampilkan (mm)",
                        0.0, 20.0, float(L_pasar), 1.0,
                        key="slider_visual")
    q_din, q_tut = diagram_panci_3d(
        L_lihat, r_wadah=p["r_luar_mm"], tinggi=p["tinggi_mm"],
        key="panci3d_hasil")

with kanan:
    st.markdown("##### Rugi panas pada tebal ini")
    q_total = q_din + q_tut
    st.metric("Total rugi panas", f"{q_total:.2f} W", border=True)

    porsi = pd.DataFrame({
        "Jalur": ["Lewat dinding", "Lewat tutup"],
        "Watt": [q_din, q_tut],
    })
    chart_porsi = (
        alt.Chart(porsi)
        .mark_bar(cornerRadius=4)
        .encode(
            x=alt.X("Watt:Q", title="Rugi panas (W)"),
            y=alt.Y("Jalur:N", title=None, sort="-x"),
            color=alt.Color("Jalur:N", scale=alt.Scale(
                domain=["Lewat dinding", "Lewat tutup"],
                range=[WARNA["dinding"], WARNA["tutup"]]), legend=None),
            tooltip=[alt.Tooltip("Jalur:N"), alt.Tooltip("Watt:Q", format=".2f")],
        )
        .properties(height=110)
    )
    st.altair_chart(chart_porsi, width="stretch")

    persen_tutup = q_tut / q_total * 100 if q_total > 0 else 0
    if persen_tutup > 60:
        st.warning(
            f"Pada ketebalan ini, **{persen_tutup:.0f}%** rugi panas keluar "
            f"lewat tutup yang tidak diinsulasi. Menambah tebal dinding "
            f"tidak banyak menolong lagi.",
            icon=":material/priority_high:",
        )
    else:
        st.info(
            f"Tutup menyumbang {persen_tutup:.0f}% rugi panas. "
            f"Dinding masih jalur utama.",
            icon=":material/info:",
        )

# ── Kurva biaya ──────────────────────────────────────────────────────────────
st.subheader("Mengapa ketebalan ini yang terbaik")
st.caption(
    "Menambah glasswool menaikkan biaya beli tapi menurunkan biaya listrik. "
    "Titik terendah kurva ungu adalah keseimbangan terbaik antara keduanya."
)

L_grid = np.linspace(0.0, 20.0, 160)
r_m, t_m = p["r_luar_mm"] / 1000.0, p["tinggi_mm"] / 1000.0
data_lcc = pd.DataFrame({
    "Tebal (mm)": np.tile(L_grid, 3),
    "Biaya (Rp)": np.concatenate([
        [lcc_fn(l) for l in L_grid],
        [biaya_investasi(l, harga_per_m2_mm=p["harga_gw"], markup=p["markup"],
                         r_luar_wadah=r_m, tinggi_wadah=t_m)
         for l in L_grid],
        [lcc_fn(l) - biaya_investasi(l, harga_per_m2_mm=p["harga_gw"],
                                     markup=p["markup"], r_luar_wadah=r_m,
                                     tinggi_wadah=t_m) for l in L_grid],
    ]),
    "Komponen": (["Total biaya"] * len(L_grid)
                 + ["Biaya beli glasswool"] * len(L_grid)
                 + ["Biaya listrik terbuang"] * len(L_grid)),
})

garis = (
    alt.Chart(data_lcc)
    .mark_line(strokeWidth=2.5)
    .encode(
        x=alt.X("Tebal (mm):Q", title="Tebal glasswool (mm)"),
        y=alt.Y("Biaya (Rp):Q", title="Biaya selama 5 tahun (Rp)",
                axis=alt.Axis(format="~s")),
        color=alt.Color("Komponen:N", title=None, scale=alt.Scale(
            domain=["Total biaya", "Biaya beli glasswool", "Biaya listrik terbuang"],
            range=[WARNA["lcc"], WARNA["invest"], WARNA["energi"]])),
        strokeDash=alt.StrokeDash("Komponen:N", scale=alt.Scale(
            domain=["Total biaya", "Biaya beli glasswool", "Biaya listrik terbuang"],
            range=[[1, 0], [6, 3], [6, 3]]), legend=None),
        tooltip=[alt.Tooltip("Tebal (mm):Q", format=".1f"),
                 alt.Tooltip("Komponen:N"),
                 alt.Tooltip("Biaya (Rp):Q", format=",.0f")],
    )
)

pita = (
    alt.Chart(pd.DataFrame({"lo": [h["L_lo"]], "hi": [h["L_hi"]]}))
    .mark_rect(opacity=0.13, fill=WARNA["aksen"])
    .encode(x="lo:Q", x2="hi:Q")
)

titik = (
    alt.Chart(pd.DataFrame({"x": [L_opt], "y": [LCC_opt]}))
    .mark_point(size=170, filled=True, shape="diamond",
                color=WARNA["optimum"])
    .encode(x="x:Q", y="y:Q",
            tooltip=[alt.Tooltip("x:Q", title="L* (mm)", format=".2f"),
                     alt.Tooltip("y:Q", title="LCC (Rp)", format=",.0f")])
)

st.altair_chart((pita + garis + titik).properties(height=380)
                .interactive(), width="stretch")

st.caption(
    f"Pita kuning = rentang **{h['L_lo']:.1f}–{h['L_hi']:.1f} mm**, semuanya "
    f"masih dalam 1% dari biaya minimum. Artinya pemilihan ukuran komersial "
    f"tidak merugikan secara ekonomi."
)

# ── Bandingkan ukuran pasaran ────────────────────────────────────────────────
st.subheader("Perbandingan ukuran yang dijual di pasaran")

baris = []
for Lp in [0, 5, 10, 15, 20]:
    b = lcc_fn(float(Lp))
    baris.append({
        "Pilihan": "Tanpa glasswool" if Lp == 0 else f"Glasswool {Lp} mm",
        "Total biaya 5 tahun": b,
        "Selisih dari optimum": b - LCC_opt,
        "Hemat dibanding tanpa insulasi": LCC_K0 - b,
    })
df_bandingan = pd.DataFrame(baris)

st.dataframe(
    df_bandingan, hide_index=True, width="stretch",
    column_config={
        "Total biaya 5 tahun": st.column_config.NumberColumn(format="Rp %d"),
        "Selisih dari optimum": st.column_config.NumberColumn(format="Rp %d"),
        "Hemat dibanding tanpa insulasi": st.column_config.NumberColumn(format="Rp %d"),
    },
)

st.caption(
    f"Dengan asumsi saat ini (pakai {p['jam']:.2f} jam/hari, "
    f"tarif {rupiah(p['tarif'])}/kWh), pilihan terbaik adalah "
    f"**glasswool {L_pasar} mm**."
)
