"""Halaman 2 — Temuan utama: tutup menjadi penghambat."""

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

from app_core import (
    sidebar_parameter, hitung_semua, WARNA,
    DATA_CHT_DEFAULT, Q_DINDING, Q_TUTUP, Q_CINCIN, T_DINDING, T_TUTUP,
)
from app_visual3d import diagram_panci_3d

p = sidebar_parameter()
h = hitung_semua(p)

st.title("Temuan utama")
st.caption("Mengapa menambah glasswool ada batasnya")

Lk = [0, 5, 10, 15, 20]
df_pecah = pd.DataFrame({
    "L": Lk,
    "Konfigurasi": [f"K{i}" for i in range(5)],
    "Dinding": [Q_DINDING[k] for k in Lk],
    "Tutup": [Q_TUTUP[k] for k in Lk],
    "Cincin": [Q_CINCIN[k] for k in Lk],
})
df_pecah["Total"] = df_pecah[["Dinding", "Tutup", "Cincin"]].sum(axis=1)
df_pecah["Porsi tutup (%)"] = df_pecah["Tutup"] / df_pecah["Total"] * 100

# ── Inti temuan ──────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("#### Inti temuan")
    st.markdown(
        f"Glasswool berhasil menekan rugi panas lewat **dinding** dari "
        f"**{Q_DINDING[0]:.2f} W** menjadi **{Q_DINDING[20]:.2f} W** "
        f"(turun {(1 - Q_DINDING[20] / Q_DINDING[0]) * 100:.0f}%).\n\n"
        f"Tetapi rugi panas lewat **tutup justru naik** dari "
        f"**{Q_TUTUP[0]:.2f} W** menjadi **{Q_TUTUP[20]:.2f} W**. "
        f"Panas yang tertahan di dinding berpindah jalur ke tutup yang "
        f"tidak diinsulasi.\n\n"
        f"Akibatnya porsi rugi panas lewat tutup melonjak dari "
        f"**{df_pecah['Porsi tutup (%)'].iloc[0]:.0f}%** menjadi "
        f"**{df_pecah['Porsi tutup (%)'].iloc[-1]:.0f}%**."
    )

with st.container(horizontal=True):
    st.metric("Rugi lewat dinding (K0 → K4)",
              f"{Q_DINDING[20]:.2f} W",
              f"-{(1 - Q_DINDING[20] / Q_DINDING[0]) * 100:.0f}%",
              border=True)
    st.metric("Rugi lewat tutup (K0 → K4)",
              f"{Q_TUTUP[20]:.2f} W",
              f"+{(Q_TUTUP[20] / Q_TUTUP[0] - 1) * 100:.0f}%",
              delta_color="inverse", border=True)
    st.metric("Porsi tutup pada K4",
              f"{df_pecah['Porsi tutup (%)'].iloc[-1]:.0f}%",
              border=True,
              help="Bagian rugi panas yang keluar lewat tutup")
    st.metric("Batas bawah rugi panas",
              f"{h['koef'][0]:.2f} W", border=True,
              help="Asimtot Q∞ — tidak bisa ditembus hanya dengan "
                   "menebalkan glasswool dinding")

# ── Perbandingan visual dua kondisi ──────────────────────────────────────────
st.subheader("Perbandingan visual 3D")
st.caption(
    "Putar tiap model dengan mouse untuk melihat lapisan glasswool. "
    "Perhatikan pergeseran ketebalan panah: dinding menipis, tutup menebal."
)
if p.get("dimensi_diubah"):
    st.caption(
        ":material/info: Bentuk mengikuti dimensi baru di panel kiri, tapi "
        "angka rugi panas (W) tetap dari simulasi CHT Q2-8012 asli — "
        "belum disimulasikan ulang untuk ukuran ini."
    )

kiri, kanan = st.columns(2)
with kiri:
    with st.container(border=True):
        st.markdown("**Tanpa glasswool (K0)**")
        diagram_panci_3d(0, Q_DINDING[0], Q_TUTUP[0], T_DINDING[0], T_TUTUP[0],
                         r_wadah=p["r_luar_mm"], tinggi=p["tinggi_mm"],
                         tinggi_px=420, key="panci3d_k0")
        st.caption(
            f"Dinding {Q_DINDING[0]:.2f} W · tutup {Q_TUTUP[0]:.2f} W. "
            f"Dinding jadi jalur utama."
        )
with kanan:
    with st.container(border=True):
        st.markdown("**Glasswool 20 mm (K4)**")
        diagram_panci_3d(20, Q_DINDING[20], Q_TUTUP[20], T_DINDING[20], T_TUTUP[20],
                         r_wadah=p["r_luar_mm"], tinggi=p["tinggi_mm"],
                         tinggi_px=420, key="panci3d_k4")
        st.caption(
            f"Dinding {Q_DINDING[20]:.2f} W · tutup {Q_TUTUP[20]:.2f} W. "
            f"Sekarang tutup yang dominan."
        )

# ── Grafik ───────────────────────────────────────────────────────────────────
st.subheader("Rugi panas dipecah per jalur")

kiri, kanan = st.columns(2)

with kiri:
    with st.container(border=True):
        st.markdown("**Besar rugi panas (Watt)**")
        panjang = df_pecah.melt(
            id_vars=["Konfigurasi", "L"],
            value_vars=["Dinding", "Tutup", "Cincin"],
            var_name="Jalur", value_name="Watt")
        c = (
            alt.Chart(panjang)
            .mark_bar()
            .encode(
                x=alt.X("Konfigurasi:N", title=None, sort=None),
                y=alt.Y("Watt:Q", title="Rugi panas (W)"),
                color=alt.Color("Jalur:N", title=None, scale=alt.Scale(
                    domain=["Dinding", "Tutup", "Cincin"],
                    range=[WARNA["dinding"], WARNA["tutup"], WARNA["cincin"]])),
                tooltip=["Konfigurasi:N", "Jalur:N",
                         alt.Tooltip("Watt:Q", format=".3f")],
            )
            .properties(height=320)
        )
        st.altair_chart(c, width="stretch")

with kanan:
    with st.container(border=True):
        st.markdown("**Porsi rugi panas lewat tutup (%)**")
        c2 = (
            alt.Chart(df_pecah)
            .mark_line(point=alt.OverlayMarkDef(size=90, filled=True),
                       strokeWidth=3, color=WARNA["tutup"])
            .encode(
                x=alt.X("Konfigurasi:N", title=None, sort=None),
                y=alt.Y("Porsi tutup (%):Q", title="Porsi tutup (%)",
                        scale=alt.Scale(domain=[0, 100])),
                tooltip=["Konfigurasi:N",
                         alt.Tooltip("Porsi tutup (%):Q", format=".1f")],
            )
            .properties(height=320)
        )
        st.altair_chart(c2, width="stretch")

# ── Suhu permukaan ───────────────────────────────────────────────────────────
st.subheader("Suhu permukaan luar")
st.caption(
    "Dinding menjadi jauh lebih dingin karena terlindungi glasswool — "
    "sekaligus lebih aman disentuh. Tutup tetap panas hampir 95 °C."
)

df_suhu = pd.DataFrame({
    "Konfigurasi": [f"K{i}" for i in range(5)],
    "Dinding": [T_DINDING[k] for k in Lk],
    "Tutup": [T_TUTUP[k] for k in Lk],
}).melt(id_vars="Konfigurasi", var_name="Permukaan", value_name="Suhu")

c3 = (
    alt.Chart(df_suhu)
    .mark_line(point=alt.OverlayMarkDef(size=80, filled=True), strokeWidth=2.5)
    .encode(
        x=alt.X("Konfigurasi:N", title=None, sort=None),
        y=alt.Y("Suhu:Q", title="Suhu permukaan (°C)"),
        color=alt.Color("Permukaan:N", title=None, scale=alt.Scale(
            domain=["Dinding", "Tutup"],
            range=[WARNA["dinding"], WARNA["tutup"]])),
        tooltip=["Konfigurasi:N", "Permukaan:N",
                 alt.Tooltip("Suhu:Q", format=".2f")],
    )
    .properties(height=300)
)
st.altair_chart(c3, width="stretch")

# ── Tabel & implikasi ────────────────────────────────────────────────────────
with st.expander("Tabel rinci per konfigurasi", icon=":material/table_chart:"):
    tampil = df_pecah[["Konfigurasi", "L", "Dinding", "Tutup", "Cincin",
                       "Total", "Porsi tutup (%)"]].copy()
    tampil = tampil.rename(columns={"L": "Tebal (mm)"})
    st.dataframe(
        tampil, hide_index=True, width="stretch",
        column_config={
            "Dinding": st.column_config.NumberColumn(format="%.3f W"),
            "Tutup": st.column_config.NumberColumn(format="%.3f W"),
            "Cincin": st.column_config.NumberColumn(format="%.3f W"),
            "Total": st.column_config.NumberColumn(format="%.3f W"),
            "Porsi tutup (%)": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0, max_value=100),
        },
    )

st.subheader("Arah penelitian lanjutan")
st.info(
    "Karena tutup kini menjadi penghambat utama, **menginsulasi tutup** "
    "berpotensi jauh lebih efektif daripada terus menebalkan dinding. "
    "Estimasi analitik menunjukkan glasswool 5 mm pada tutup menghemat "
    "sekitar **2,66 W** — jauh lebih besar dibanding menebalkan dinding "
    "dari 15 ke 20 mm yang hanya menghemat 0,022 W.",
    icon=":material/lightbulb:",
)
st.caption(
    "Status: proyeksi analitik berbasis model resistansi seri 1-D, "
    "**belum diverifikasi simulasi CHT**. Perlu diuji pada Tahap 2."
)
