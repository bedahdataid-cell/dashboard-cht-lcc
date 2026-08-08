"""
streamlit_app.py
================
Dashboard CHT-LCC Glasswool — Panci Listrik Mini Q2-8012
Penelitian Hibah Internal LPPM UMB 2026 · Bakti Alpihuda

Jalankan:
  klik dua kali 2_Buka_Dashboard.bat
  atau: python -m streamlit run streamlit_app.py

Struktur:
  streamlit_app.py   -> navigasi (file ini)
  app_core.py        -> parameter sidebar + perhitungan (di-cache)
  app_visual3d.py    -> gambar 3D interaktif panci
  app_pages/         -> 5 halaman (0_panduan untuk pembaca umum, 1-4 detail)

Semua rumus diambil dari lcc_optimizer.py — tidak ditulis ulang, supaya
angka dashboard selalu identik dengan angka laporan.

Versi lama (satu halaman) disimpan sebagai streamlit_app_LAMA.py.bak
"""

import streamlit as st

st.set_page_config(
    page_title="CHT-LCC Glasswool — UMB 2026",
    page_icon=":material/science:",
    layout="wide",
    initial_sidebar_state="expanded",
)

halaman = st.navigation([
    st.Page("app_pages/0_panduan.py", title="Panduan singkat",
            icon=":material/school:", default=True),
    st.Page("app_pages/1_hasil.py", title="Hasil analisis",
            icon=":material/insights:"),
    st.Page("app_pages/2_temuan.py", title="Temuan utama",
            icon=":material/lightbulb:"),
    st.Page("app_pages/3_ketahanan.py", title="Ketahanan hasil",
            icon=":material/verified:"),
    st.Page("app_pages/4_metode.py", title="Metode & sumber",
            icon=":material/menu_book:"),
    st.Page("app_pages/5_dampak_nasional.py", title="Dampak nasional",
            icon=":material/public:"),
])

with st.sidebar:
    st.markdown("### Panci listrik mini Q2-8012")
    st.caption("Optimasi ketebalan glasswool · LPPM UMB 2026")

halaman.run()

with st.sidebar:
    st.caption(
        "Bakti Alpihuda · Teknik Mesin UMB\n\n"
        "Data simulasi 8 Agustus 2026"
    )
