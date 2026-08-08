"""
app_visual.py
=============
Gambar visual bentuk panci untuk dashboard — potongan melintang berskala
yang menunjukkan tebal glasswool dan ke mana panas lolos.

Dibuat dengan SVG (st.html) karena bentuk geometri panci tidak bisa
digambarkan oleh elemen grafik bawaan Streamlit.
"""

import numpy as np
import streamlit as st

from app_core import Q_DINDING, Q_TUTUP, Q_CINCIN, T_DINDING, T_TUTUP, WARNA


def _warna_suhu(t_celsius):
    """Warna permukaan mengikuti suhu: makin panas makin merah."""
    t = float(np.clip((t_celsius - 27) / (95 - 27), 0, 1))
    r = int(70 + t * 185)
    g = int(130 - t * 60)
    b = int(200 - t * 160)
    return f"rgb({r},{g},{b})"


def diagram_panci(L_mm, Q_dinding=None, Q_tutup=None, T_din=None, T_tut=None,
                  tinggi_px=340):
    """Potongan melintang panci dengan selimut glasswool setebal L_mm.

    Panah menunjukkan arah dan besar rugi panas: makin tebal panah,
    makin besar rugi panas lewat jalur itu.
    """
    # Interpolasi bila L bukan salah satu titik simulasi
    Lk = np.array([0, 5, 10, 15, 20], dtype=float)
    if Q_dinding is None:
        Q_dinding = float(np.interp(L_mm, Lk, [Q_DINDING[k] for k in [0, 5, 10, 15, 20]]))
    if Q_tutup is None:
        Q_tutup = float(np.interp(L_mm, Lk, [Q_TUTUP[k] for k in [0, 5, 10, 15, 20]]))
    if T_din is None:
        T_din = float(np.interp(L_mm, Lk, [T_DINDING[k] for k in [0, 5, 10, 15, 20]]))
    if T_tut is None:
        T_tut = float(np.interp(L_mm, Lk, [T_TUTUP[k] for k in [0, 5, 10, 15, 20]]))

    # Skala: wadah radius 60 mm, tinggi 110 mm -> piksel
    SK = 2.0
    r_wadah = 60 * SK / 2      # setengah lebar (potongan simetris)
    h_wadah = 110 * SK / 2
    t_gw = L_mm * SK / 2
    cx, cy = 260, 190

    x_kiri_in = cx - r_wadah
    x_kanan_in = cx + r_wadah
    y_atas = cy - h_wadah
    y_bawah = cy + h_wadah

    w_din = 3
    c_din = _warna_suhu(T_din)
    c_tut = _warna_suhu(T_tut)

    # Ketebalan panah sebanding akar rugi panas (biar proporsi terlihat wajar)
    def tebal_panah(q):
        return float(np.clip(1.5 + np.sqrt(max(q, 0)) * 2.2, 1.5, 13))

    tp_din = tebal_panah(Q_dinding)
    tp_tut = tebal_panah(Q_tutup)

    gw_kiri = f"""
      <rect x="{x_kiri_in - t_gw:.1f}" y="{y_atas:.1f}"
            width="{t_gw:.1f}" height="{h_wadah * 2:.1f}"
            fill="#F2C94C" fill-opacity="0.55" stroke="#C9A227" stroke-width="1"/>
    """ if L_mm > 0.05 else ""
    gw_kanan = f"""
      <rect x="{x_kanan_in:.1f}" y="{y_atas:.1f}"
            width="{t_gw:.1f}" height="{h_wadah * 2:.1f}"
            fill="#F2C94C" fill-opacity="0.55" stroke="#C9A227" stroke-width="1"/>
    """ if L_mm > 0.05 else ""

    label_gw = f"""
      <text x="{x_kanan_in + t_gw + 8:.1f}" y="{cy + 4:.1f}"
            font-size="12" fill="#8A6D1B" font-family="sans-serif">
        glasswool {L_mm:.0f} mm
      </text>
    """ if L_mm > 0.05 else f"""
      <text x="{x_kanan_in + 10:.1f}" y="{cy + 4:.1f}"
            font-size="12" fill="#B44" font-family="sans-serif">
        tanpa glasswool
      </text>
    """

    svg = f"""
<div style="width:100%;display:flex;justify-content:center;">
<svg viewBox="0 0 520 {tinggi_px}" width="100%" style="max-width:520px;height:auto;"
     xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Potongan melintang panci dengan glasswool {L_mm:.0f} mm">

  <!-- air di dalam -->
  <rect x="{x_kiri_in:.1f}" y="{y_atas + 10:.1f}"
        width="{r_wadah * 2:.1f}" height="{h_wadah * 2 - 10:.1f}"
        fill="#CDE3F5" fill-opacity="0.75"/>
  <text x="{cx}" y="{cy + 30:.1f}" font-size="13" fill="#33637F"
        text-anchor="middle" font-family="sans-serif">air 95 °C</text>

  {gw_kiri}{gw_kanan}

  <!-- dinding stainless -->
  <line x1="{x_kiri_in:.1f}" y1="{y_atas:.1f}" x2="{x_kiri_in:.1f}" y2="{y_bawah:.1f}"
        stroke="{c_din}" stroke-width="{w_din}"/>
  <line x1="{x_kanan_in:.1f}" y1="{y_atas:.1f}" x2="{x_kanan_in:.1f}" y2="{y_bawah:.1f}"
        stroke="{c_din}" stroke-width="{w_din}"/>
  <line x1="{x_kiri_in:.1f}" y1="{y_bawah:.1f}" x2="{x_kanan_in:.1f}" y2="{y_bawah:.1f}"
        stroke="{c_din}" stroke-width="{w_din}"/>

  <!-- tutup (tidak diinsulasi) -->
  <rect x="{x_kiri_in - 6:.1f}" y="{y_atas - 9:.1f}"
        width="{r_wadah * 2 + 12:.1f}" height="9"
        fill="{c_tut}" stroke="#8B3A2E" stroke-width="1"/>

  <!-- panah rugi panas lewat TUTUP -->
  <line x1="{cx:.1f}" y1="{y_atas - 12:.1f}" x2="{cx:.1f}" y2="{y_atas - 52:.1f}"
        stroke="{WARNA['tutup']}" stroke-width="{tp_tut:.1f}"
        marker-end="url(#kepala_tutup)"/>
  <text x="{cx + 14:.1f}" y="{y_atas - 34:.1f}" font-size="13"
        fill="{WARNA['tutup']}" font-weight="bold" font-family="sans-serif">
    tutup {Q_tutup:.2f} W
  </text>

  <!-- panah rugi panas lewat DINDING -->
  <line x1="{x_kanan_in + t_gw + 4:.1f}" y1="{cy - 40:.1f}"
        x2="{x_kanan_in + t_gw + 48:.1f}" y2="{cy - 40:.1f}"
        stroke="{WARNA['dinding']}" stroke-width="{tp_din:.1f}"
        marker-end="url(#kepala_dinding)"/>
  <text x="{x_kanan_in + t_gw + 8:.1f}" y="{cy - 50:.1f}" font-size="13"
        fill="{WARNA['dinding']}" font-weight="bold" font-family="sans-serif">
    dinding {Q_dinding:.2f} W
  </text>

  {label_gw}

  <!-- suhu permukaan -->
  <text x="{x_kiri_in - t_gw - 12:.1f}" y="{cy - 40:.1f}" font-size="11"
        fill="#555" text-anchor="end" font-family="sans-serif">
    {T_din:.0f} °C
  </text>
  <text x="{x_kiri_in - 10:.1f}" y="{y_atas - 14:.1f}" font-size="11"
        fill="#555" text-anchor="end" font-family="sans-serif">
    {T_tut:.0f} °C
  </text>

  <defs>
    <marker id="kepala_tutup" markerWidth="7" markerHeight="7"
            refX="5" refY="3.5" orient="auto">
      <polygon points="0 0, 7 3.5, 0 7" fill="{WARNA['tutup']}"/>
    </marker>
    <marker id="kepala_dinding" markerWidth="7" markerHeight="7"
            refX="5" refY="3.5" orient="auto">
      <polygon points="0 0, 7 3.5, 0 7" fill="{WARNA['dinding']}"/>
    </marker>
  </defs>
</svg>
</div>
"""
    st.html(svg)
    return Q_dinding, Q_tutup
