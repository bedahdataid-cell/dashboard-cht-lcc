"""Halaman 5 — Dampak nasional: skala penghematan bila dipakai banyak unit.

PENTING (integritas data — lihat .claude/rules/penelitian.md):
  Tidak ada data terverifikasi jumlah unit Q2-8012 spesifik yang beredar di
  Indonesia. Karena itu skala nasional di halaman ini SELALU berupa skenario
  ilustratif yang bisa diatur pengguna (bukan angka pasti), dipisahkan tegas
  dari konteks pasar rice cooker umum yang memang bersumber (CLASP 2021).
"""

import streamlit as st

from app_core import (
    sidebar_parameter, hitung_semua, rupiah,
    RICE_COOKER_TERJUAL_2018_JUTA, RICE_COOKER_TERPASANG_JUTA,
    RICE_COOKER_PROYEKSI_2030_JUTA, RICE_COOKER_SUMBER,
)

p = sidebar_parameter()
h = hitung_semua(p)
hemat_per_unit = h["LCC_K0"] - h["LCC_opt"]

st.title("Dampak bila dipakai banyak orang")
st.caption(
    "Satu panci hanya hemat puluhan ribu rupiah — kelihatan kecil. "
    "Halaman ini menunjukkan skalanya bila dipakai banyak unit sekaligus."
)

st.warning(
    "**Bacaan penting sebelum lanjut.** Tidak ada data resmi berapa unit "
    "panci listrik mini **Q2-8012 secara spesifik** yang terjual atau "
    "dipakai di Indonesia — data publik seperti itu tidak tersedia. Angka "
    "\"jumlah unit\" di halaman ini karena itu adalah **skenario yang bisa "
    "Anda atur sendiri**, bukan hasil riset pasar Q2-8012. Yang bersumber "
    "hanya konteks pasar rice cooker rumah tangga secara umum (bagian "
    "bawah halaman).",
    icon=":material/report:",
)

# ── Skenario nasional — jelas berlabel ilustratif ────────────────────────────
st.subheader("Skenario: kalikan hemat per unit")
st.caption(
    "Geser untuk mengubah anggapan jumlah unit yang memakai glasswool "
    f"{'optimal (' + str(round(h['L_opt'],1)) + ' mm)' } ini. Ini murni "
    "perkalian sederhana — hemat per unit × jumlah unit — bukan proyeksi "
    "pasar."
)

kiri, kanan = st.columns([2, 3], vertical_alignment="center")
with kiri:
    skenario = st.select_slider(
        "Anggap jumlah unit terpasang",
        options=[1_000, 10_000, 100_000, 1_000_000, 13_000_000, 56_000_000],
        value=100_000,
        format_func=lambda x: f"{x:,}".replace(",", "."),
        help="Beberapa titik referensi: 13 juta = penjualan rice cooker "
             "nasional per tahun (2018); 56 juta = perkiraan total rice "
             "cooker terpasang. Keduanya BUKAN angka Q2-8012 spesifik — "
             "lihat peringatan di atas.",
    )
    st.metric("Hemat per unit (5 tahun)", rupiah(hemat_per_unit), border=True)

with kanan:
    total_hemat = hemat_per_unit * skenario
    if total_hemat >= 1e12:
        ringkas = f" ({total_hemat / 1e12:,.2f} triliun)"
    elif total_hemat >= 1e9:
        ringkas = f" ({total_hemat / 1e9:,.1f} miliar)"
    elif total_hemat >= 1e6:
        ringkas = f" ({total_hemat / 1e6:,.1f} juta)"
    else:
        ringkas = ""
    label_unit = f"Jika {skenario:,}".replace(",", ".") + " unit memakai insulasi ini"
    st.metric(
        label_unit, rupiah(total_hemat) + ringkas, border=True,
        help="Hemat per unit dikalikan jumlah unit pada skenario ini. "
             "Selama 5 tahun (umur analisis penelitian).",
    )
    st.caption(
        "Angka ini murni perkalian — **bukan hasil riset jumlah unit "
        "sungguhan**. Geser slider di kiri untuk skenario lain."
    )

st.divider()

# ── Konteks pasar (bersumber, bukan klaim Q2-8012) ──────────────────────────
st.subheader("Untuk perbandingan: skala pasar alat masak listrik nasional")
st.caption(
    "Angka berikut BERSUMBER, tapi untuk **rice cooker rumah tangga pada "
    "umumnya (kapasitas 1–3 liter)** — bukan panci mini seperti Q2-8012. "
    "Ditampilkan sekadar gambaran skala pasar alat masak listrik di "
    "Indonesia, bukan estimasi populasi Q2-8012."
)

with st.container(horizontal=True):
    st.metric("Rice cooker terjual/tahun", "13 juta unit", border=True,
              help="Data 2018. " + RICE_COOKER_SUMBER)
    st.metric("Rice cooker terpasang (estimasi)", "56 juta unit", border=True,
              help="Perkiraan total unit sedang dipakai di Indonesia. "
                   + RICE_COOKER_SUMBER)
    st.metric("Proyeksi penjualan 2030", "19,6 juta unit/tahun", border=True,
              help="Proyeksi laporan, titik saturasi pasar ~2025. "
                   + RICE_COOKER_SUMBER)

st.caption(f"Sumber: {RICE_COOKER_SUMBER}.")

st.info(
    "**Mengapa tidak langsung dikalikan 56 juta?** Karena 56 juta itu "
    "rice cooker rumah tangga biasa (kapasitas nasi 1–3 liter, konstruksi "
    "beda dari panci mini Q2-8012), bukan produk yang sama dengan yang "
    "diteliti di sini. Menyamakan keduanya akan melebih-lebihkan hasil. "
    "Angka ini sekadar menunjukkan: **pasar alat masak listrik di "
    "Indonesia memang berskala puluhan juta unit** — jadi potensi "
    "penghematan energi nasional dari optimasi insulasi seperti ini "
    "nyata skalanya, meski jumlah pasti Q2-8012 belum diketahui.",
    icon=":material/lightbulb:",
)

st.subheader("Yang dibutuhkan untuk angka nasional yang valid")
st.markdown(
    "- Data penjualan/populasi **Q2-8012 spesifik** (dari produsen atau "
    "riset pasar khusus)\n"
    "- Atau: data populasi **kategori panci listrik mini sejenis** "
    "(kapasitas kos-kosan, <1 liter) — kategori ini belum ada datanya "
    "di laporan pasar yang ditemukan\n"
    "- Verifikasi bahwa hemat energi K0→K2 (tanpa insulasi → 10mm) "
    "berlaku sama untuk semua merek/model sejenis, bukan cuma Q2-8012"
)
st.caption(
    "Sampai data itu tersedia, perlakukan angka nasional di halaman ini "
    "sebagai ilustrasi skala, bukan proyeksi dampak riil — tandai "
    "\"perlu verifikasi\" bila dikutip di laporan atau presentasi."
)
