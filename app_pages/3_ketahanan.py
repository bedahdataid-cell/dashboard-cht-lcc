"""Halaman 3 — Seberapa kokoh kesimpulan bila asumsi meleset."""

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from app_core import (
    sidebar_parameter, hitung_semua, sensitivitas, monte_carlo,
    tebal_komersial, WARNA,
)

p = sidebar_parameter()
h = hitung_semua(p)
L_opt, LCC_opt = h["L_opt"], h["LCC_opt"]
L_pasar = tebal_komersial(L_opt)

st.title("Ketahanan hasil")
st.caption(
    "Kesimpulan penelitian bergantung pada asumsi. Halaman ini menguji "
    "apa yang terjadi bila asumsi itu meleset."
)

if L_opt >= 19.95:
    st.warning(
        f"Pada asumsi saat ini ({p['jam']:.2f} jam/hari), ketebalan optimal "
        f"menempel di batas pencarian 20 mm — optimum sebenarnya ada di luar "
        f"rentang data simulasi. Angka di halaman ini menjadi kurang berarti; "
        f"turunkan lama pakai di panel kiri, atau tambahkan simulasi pada "
        f"ketebalan di atas 20 mm.",
        icon=":material/warning:",
    )

# ── Sensitivitas ─────────────────────────────────────────────────────────────
st.subheader("Parameter mana yang paling menentukan")
st.caption(
    "Tiap parameter diubah naik-turun satu per satu, lalu dilihat "
    "seberapa besar total biaya berubah. Batang makin panjang = makin berpengaruh."
)

with st.spinner("Menghitung sensitivitas..."):
    df_sens = sensitivitas(h["koef"], p, LCC_opt)

urutan = (df_sens.assign(abs_=df_sens["Perubahan LCC (%)"].abs())
          .groupby("Parameter")["abs_"].sum()
          .sort_values(ascending=False).index.tolist())

tornado = (
    alt.Chart(df_sens)
    .mark_bar()
    .encode(
        x=alt.X("Perubahan LCC (%):Q", title="Perubahan total biaya (%)"),
        y=alt.Y("Parameter:N", title=None, sort=urutan),
        color=alt.Color("Arah:N", title=None, scale=alt.Scale(
            domain=["Naik", "Turun"],
            range=[WARNA["energi"], WARNA["dinding"]])),
        tooltip=["Parameter:N", "Arah:N",
                 alt.Tooltip("Nilai baru:Q", format=",.4f"),
                 alt.Tooltip("L* (mm):Q", format=".2f"),
                 alt.Tooltip("Perubahan LCC (%):Q", format=".2f")],
    )
    .properties(height=260)
)
st.altair_chart(tornado, width="stretch")

paling = urutan[0]
st.info(
    f"Parameter paling berpengaruh: **{paling.lower()}**. "
    f"Inilah asumsi yang paling perlu dipertahankan dasarnya saat monev. "
    f"Sebaliknya, harga glasswool dan suku bunga hampir tidak menggeser "
    f"ketebalan optimal — kesimpulan tetap berlaku meski harga pasar berubah.",
    icon=":material/insights:",
)

with st.expander("Tabel sensitivitas", icon=":material/table_chart:"):
    st.dataframe(df_sens, hide_index=True, width="stretch")
    st.download_button(
        "Unduh tabel sensitivitas (CSV)",
        data=df_sens.to_csv(index=False).encode("utf-8"),
        file_name="sensitivitas_OAT.csv", mime="text/csv",
        icon=":material/download:",
    )

# ── Monte Carlo ──────────────────────────────────────────────────────────────
st.subheader("Uji 10.000 kemungkinan sekaligus")
st.caption(
    "Sensitivitas menguji satu parameter pada satu waktu. Kenyataannya semua "
    "bisa meleset bersamaan. Monte Carlo mengacak semuanya serentak."
)

with st.spinner(f"Menjalankan {p['n_mc']:,} skenario..."):
    L_mc = monte_carlo(h["koef"], p)

L_mean, L_std = float(L_mc.mean()), float(L_mc.std())
L_p5, L_p95 = float(np.percentile(L_mc, 5)), float(np.percentile(L_mc, 95))
dalam = float(((L_mc >= L_p5) & (L_mc <= L_p95)).mean() * 100)

with st.container(horizontal=True):
    st.metric("Ketebalan optimal rata-rata", f"{L_mean:.2f} mm", border=True)
    st.metric("Simpangan baku", f"{L_std:.2f} mm", border=True,
              help="Makin kecil, makin konsisten hasilnya")
    st.metric("Rentang 90% kemungkinan", f"{L_p5:.1f}–{L_p95:.1f} mm",
              border=True,
              help="9 dari 10 skenario menghasilkan optimum di rentang ini")
    st.metric("Jumlah skenario", f"{p['n_mc']:,}", border=True)

df_mc = pd.DataFrame({"L": L_mc})
hist = (
    alt.Chart(df_mc)
    .mark_bar(color=WARNA["dinding"], opacity=0.8)
    .encode(
        x=alt.X("L:Q", bin=alt.Bin(maxbins=60),
                title="Ketebalan optimal hasil tiap skenario (mm)"),
        y=alt.Y("count():Q", title="Jumlah skenario"),
        tooltip=[alt.Tooltip("count():Q", title="Skenario")],
    )
)
garis_pasar = (
    alt.Chart(pd.DataFrame({"x": [L_pasar]}))
    .mark_rule(color=WARNA["invest"], strokeWidth=3, strokeDash=[6, 3])
    .encode(x="x:Q", tooltip=[alt.Tooltip("x:Q", title="Rekomendasi (mm)")])
)
garis_mean = (
    alt.Chart(pd.DataFrame({"x": [L_mean]}))
    .mark_rule(color=WARNA["energi"], strokeWidth=2.5)
    .encode(x="x:Q", tooltip=[alt.Tooltip("x:Q", title="Rata-rata (mm)",
                                          format=".2f")])
)
st.altair_chart((hist + garis_mean + garis_pasar).properties(height=340),
                width="stretch")

st.caption(
    f"Garis merah = rata-rata ({L_mean:.2f} mm). "
    f"Garis hijau putus-putus = rekomendasi praktis ({L_pasar} mm)."
)

if L_p5 <= L_pasar <= L_p95:
    st.success(
        f"Rekomendasi **{L_pasar} mm** berada di dalam rentang 90% kemungkinan "
        f"({L_p5:.1f}–{L_p95:.1f} mm). Kesimpulan penelitian **kokoh** terhadap "
        f"ketidakpastian asumsi.",
        icon=":material/verified:",
    )
else:
    st.warning(
        f"Rekomendasi {L_pasar} mm berada di luar rentang 90% "
        f"({L_p5:.1f}–{L_p95:.1f} mm) pada asumsi saat ini. "
        f"Periksa kembali pengaturan di panel kiri.",
        icon=":material/warning:",
    )

with st.expander("Statistik rinci Monte Carlo", icon=":material/functions:"):
    ringkas = pd.DataFrame({
        "Statistik": ["Rata-rata", "Simpangan baku", "Persentil 5",
                      "Persentil 25", "Median", "Persentil 75", "Persentil 95"],
        "Ketebalan optimal (mm)": [
            round(L_mean, 2), round(L_std, 2),
            round(np.percentile(L_mc, 5), 2), round(np.percentile(L_mc, 25), 2),
            round(np.percentile(L_mc, 50), 2), round(np.percentile(L_mc, 75), 2),
            round(np.percentile(L_mc, 95), 2)],
    })
    st.dataframe(ringkas, hide_index=True, width="stretch")
    st.caption(f"n = {p['n_mc']:,} skenario · random seed = {p['seed_mc']}")
