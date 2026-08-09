"""
app_visual3d.py
===============
Visual 3D interaktif panci — bisa diputar, di-zoom, dilihat dari segala sudut
dengan mouse. Dibangun dengan Plotly (go.Surface / go.Cone), dirender lewat
st.plotly_chart.

Geometri mengikuti parameter nyata di lcc_optimizer.py:
  R_LUAR_WADAH = 60 mm, TINGGI_WADAH = 110 mm.
Ini gambar skematik proporsional untuk komunikasi, BUKAN model CAD presisi
(model CAD asli ada di folder 'File 3d Solidwork').
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from app_core import Q_DINDING, Q_TUTUP, T_DINDING, T_TUTUP, WARNA

R_WADAH = 60.0     # mm — radius luar wadah stainless
TINGGI = 110.0     # mm — tinggi wadah
N_THETA = 48        # resolusi keliling


def _silinder(r, z_bawah, z_atas, warna, opacity=1.0, n_theta=N_THETA,
             showscale=False, hover=None):
    """Permukaan silinder (selubung) sebagai go.Surface, satu warna rata."""
    theta = np.linspace(0, 2 * np.pi, n_theta)
    z = np.linspace(z_bawah, z_atas, 2)
    theta_grid, z_grid = np.meshgrid(theta, z)
    x = r * np.cos(theta_grid)
    y = r * np.sin(theta_grid)
    warna_grid = np.zeros_like(x)
    return go.Surface(
        x=x, y=y, z=z_grid, surfacecolor=warna_grid,
        colorscale=[[0, warna], [1, warna]],
        showscale=showscale, opacity=opacity,
        hoverinfo="text" if hover else "skip",
        text=hover, lighting=dict(diffuse=0.85, ambient=0.55, specular=0.15),
        name="",
    )


def _cakram(r_dalam, r_luar, z, warna, opacity=1.0, n_theta=N_THETA, hover=None):
    """Cakram datar (dipakai untuk alas, tutup, cincin atas glasswool)."""
    theta = np.linspace(0, 2 * np.pi, n_theta)
    r_arr = np.linspace(r_dalam, r_luar, 2)
    r_grid, theta_grid = np.meshgrid(r_arr, theta)
    x = (r_grid * np.cos(theta_grid)).T
    y = (r_grid * np.sin(theta_grid)).T
    z_grid = np.full_like(x, z)
    warna_grid = np.zeros_like(x)
    return go.Surface(
        x=x, y=y, z=z_grid, surfacecolor=warna_grid,
        colorscale=[[0, warna], [1, warna]],
        showscale=False, opacity=opacity, hoverinfo="text" if hover else "skip",
        text=hover, lighting=dict(diffuse=0.85, ambient=0.55, specular=0.15),
        name="",
    )


def _warna_suhu(t_celsius):
    t = float(np.clip((t_celsius - 27) / (95 - 27), 0, 1))
    r = int(70 + t * 185)
    g = int(130 - t * 60)
    b = int(200 - t * 160)
    return f"rgb({r},{g},{b})"


def _panah_3d(fig, titik_awal, arah, panjang, tebal_batang, warna, teks,
             label=None, label_posisi="atas"):
    """Panah 3D = garis tebal + kerucut (go.Cone) di ujungnya.

    label: jika diisi, teks ini ditampilkan PERMANEN (tidak perlu hover)
    menempel di ujung panah — mis. "Tutup\\n7.02 W". label_posisi menggeser
    posisi teks relatif ujung panah supaya tidak menimpa kerucut ("atas"
    menggeser ke +z, "samping" menggeser menjauhi sumbu z).
    """
    arah = np.array(arah, dtype=float)
    arah = arah / np.linalg.norm(arah)
    ujung = np.array(titik_awal) + arah * panjang

    fig.add_trace(go.Scatter3d(
        x=[titik_awal[0], ujung[0]], y=[titik_awal[1], ujung[1]],
        z=[titik_awal[2], ujung[2]],
        mode="lines", line=dict(color=warna, width=tebal_batang),
        hoverinfo="text", text=teks, showlegend=False,
    ))
    fig.add_trace(go.Cone(
        x=[ujung[0]], y=[ujung[1]], z=[ujung[2]],
        u=[arah[0]], v=[arah[1]], w=[arah[2]],
        sizemode="absolute", sizeref=panjang * 0.28,
        anchor="tip", colorscale=[[0, warna], [1, warna]],
        showscale=False, hoverinfo="text", text=teks,
    ))

    if label:
        geser = panjang * 0.16
        if label_posisi == "atas":
            titik_label = ujung + np.array([0, 0, geser])
        else:  # "samping" — geser searah arah panah, menjauhi panci
            titik_label = ujung + arah * geser
        fig.add_trace(go.Scatter3d(
            x=[titik_label[0]], y=[titik_label[1]], z=[titik_label[2]],
            mode="text", text=[label],
            textfont=dict(color=warna, size=15, family="sans-serif"),
            hoverinfo="skip", showlegend=False,
        ))


def diagram_panci_3d(L_mm, Q_dinding=None, Q_tutup=None, T_din=None, T_tut=None,
                     r_wadah=R_WADAH, tinggi=TINGGI, tinggi_px=560, key=None):
    """Render panci 3D interaktif dengan panah rugi panas dan tampilan potong
    (setengah selubung dibuang) supaya lapisan glasswool terlihat dari dalam.

    r_wadah, tinggi (mm): dimensi panci yang digambar. Default = Q2-8012
    (60 mm / 110 mm). Skala visual (kamera, panjang panah) menyesuaikan
    otomatis bila diberi dimensi lain.
    """
    Lk = np.array([0, 5, 10, 15, 20], dtype=float)
    if Q_dinding is None:
        Q_dinding = float(np.interp(L_mm, Lk, [Q_DINDING[k] for k in [0, 5, 10, 15, 20]]))
    if Q_tutup is None:
        Q_tutup = float(np.interp(L_mm, Lk, [Q_TUTUP[k] for k in [0, 5, 10, 15, 20]]))
    if T_din is None:
        T_din = float(np.interp(L_mm, Lk, [T_DINDING[k] for k in [0, 5, 10, 15, 20]]))
    if T_tut is None:
        T_tut = float(np.interp(L_mm, Lk, [T_TUTUP[k] for k in [0, 5, 10, 15, 20]]))

    # Potong 100 derajat dari selubung supaya bagian dalam & lapisan
    # glasswool terlihat (tampilan "cutaway")
    theta_potong = np.linspace(np.radians(50), np.radians(360), N_THETA)

    def selubung_potong(r, z_bawah, z_atas, warna, opacity, hover):
        theta_grid, z_grid = np.meshgrid(theta_potong, np.linspace(z_bawah, z_atas, 2))
        x = r * np.cos(theta_grid)
        y = r * np.sin(theta_grid)
        return go.Surface(
            x=x, y=y, z=z_grid, surfacecolor=np.zeros_like(x),
            colorscale=[[0, warna], [1, warna]], showscale=False,
            opacity=opacity, hoverinfo="text", text=hover,
            lighting=dict(diffuse=0.85, ambient=0.55, specular=0.15), name="",
        )

    def cakram_potong(r_dalam, r_luar, z, warna, opacity, hover):
        r_arr = np.linspace(r_dalam, r_luar, 2)
        r_grid, theta_grid = np.meshgrid(r_arr, theta_potong)
        x = (r_grid * np.cos(theta_grid)).T
        y = (r_grid * np.sin(theta_grid)).T
        z_grid = np.full_like(x, z)
        return go.Surface(
            x=x, y=y, z=z_grid, surfacecolor=np.zeros_like(x),
            colorscale=[[0, warna], [1, warna]], showscale=False,
            opacity=opacity, hoverinfo="text", text=hover,
            lighting=dict(diffuse=0.85, ambient=0.55, specular=0.15), name="",
        )

    fig = go.Figure()

    c_din = _warna_suhu(T_din)
    c_tut = _warna_suhu(T_tut)

    # Panjang panah & jarak label proporsional terhadap ukuran panci, supaya
    # panci kecil (mis. cangkir 20mm) dan besar (mis. panci 200mm) sama-sama
    # terbaca jelas
    skala = max(r_wadah, tinggi) / 60.0   # 1.0 pada dimensi Q2-8012
    panjang_panah = 45 * skala

    # Air di dalam wadah
    tebal_dinding_visual = max(3.0, r_wadah * 0.05)
    fig.add_trace(cakram_potong(0, r_wadah - tebal_dinding_visual, tinggi - tinggi * 0.11,
                                "#CDE3F5", 0.85, f"Air 95 °C"))
    fig.add_trace(selubung_potong(r_wadah - tebal_dinding_visual, tinggi * 0.07,
                                  tinggi - tinggi * 0.11, "#CDE3F5", 0.55, "Air 95 °C"))

    # Dinding wadah stainless (selubung, dipotong)
    fig.add_trace(selubung_potong(
        r_wadah, 0, tinggi, c_din, 0.95,
        f"Dinding stainless<br>Suhu permukaan: {T_din:.1f} °C<br>"
        f"Rugi panas: {Q_dinding:.2f} W"))

    # Alas wadah
    fig.add_trace(cakram_potong(0, r_wadah, 0, "#B8BEC4", 1.0, "Alas wadah"))

    # Lapisan glasswool (selubung, di luar dinding) — hanya jika L > 0
    if L_mm > 0.05:
        r_luar_gw = r_wadah + L_mm
        fig.add_trace(selubung_potong(
            r_luar_gw, 0, tinggi, "#F2C94C", 0.68,
            f"Glasswool {L_mm:.0f} mm"))
        # cincin atas & bawah glasswool (tampak sisi potongan)
        fig.add_trace(cakram_potong(r_wadah, r_luar_gw, tinggi,
                                    "#E3B33D", 0.9, f"Glasswool {L_mm:.0f} mm"))
        fig.add_trace(cakram_potong(r_wadah, r_luar_gw, 0,
                                    "#E3B33D", 0.9, f"Glasswool {L_mm:.0f} mm"))
        r_luar_total = r_luar_gw
    else:
        r_luar_total = r_wadah

    # Tutup (tidak diinsulasi) — selalu utuh (tidak dipotong) supaya jelas
    # sebagai satu benda tunggal yang tidak berlapis
    theta_full = np.linspace(0, 2 * np.pi, N_THETA)
    r_arr = np.linspace(0, r_wadah * 1.04, 2)
    r_grid, theta_grid = np.meshgrid(r_arr, theta_full)
    x_tutup = (r_grid * np.cos(theta_grid)).T
    y_tutup = (r_grid * np.sin(theta_grid)).T
    z_tutup = np.full_like(x_tutup, tinggi + tinggi * 0.05)
    fig.add_trace(go.Surface(
        x=x_tutup, y=y_tutup, z=z_tutup, surfacecolor=np.zeros_like(x_tutup),
        colorscale=[[0, c_tut], [1, c_tut]], showscale=False, opacity=0.97,
        hoverinfo="text",
        text=f"Tutup (tidak diinsulasi)<br>Suhu permukaan: {T_tut:.1f} °C<br>"
             f"Rugi panas: {Q_tutup:.2f} W",
        lighting=dict(diffuse=0.85, ambient=0.55, specular=0.15), name="",
    ))

    # Panah rugi panas — tebal proporsional akar(Q), arah menjauhi panci
    def tebal(q):
        return float(np.clip(4 + np.sqrt(max(q, 0)) * 5.5, 4, 26))

    _panah_3d(fig, [r_luar_total + 6, 0, tinggi * 0.5], [1, 0, 0],
             panjang=panjang_panah, tebal_batang=tebal(Q_dinding),
             warna=WARNA["dinding"],
             teks=f"Rugi lewat dinding: {Q_dinding:.2f} W",
             label=f"Dinding<br>{Q_dinding:.2f} W", label_posisi="samping")
    _panah_3d(fig, [0, 0, tinggi + tinggi * 0.09], [0, 0, 1],
             panjang=panjang_panah, tebal_batang=tebal(Q_tutup),
             warna=WARNA["tutup"],
             teks=f"Rugi lewat tutup: {Q_tutup:.2f} W",
             label=f"Tutup<br>{Q_tutup:.2f} W", label_posisi="atas")

    # +0.16*panjang_panah krn label teks digeser sejauh itu dari ujung panah
    # (lihat _panah_3d) -- margin ekstra supaya teks tidak terpotong tepi
    batas = r_wadah + 20 + panjang_panah * 1.16 + 10
    fig.update_layout(
        height=tinggi_px,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        scene=dict(
            xaxis=dict(visible=False, range=[-batas, batas]),
            yaxis=dict(visible=False, range=[-batas, batas]),
            zaxis=dict(visible=False, range=[-10, tinggi + panjang_panah * 1.16 + 20]),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=1.05),
            camera=dict(eye=dict(x=1.55, y=-1.35, z=0.9)),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, width="stretch", key=key,
                    config={"displaylogo": False,
                            "modeBarButtonsToRemove": ["toImage"]})
    return Q_dinding, Q_tutup
