"""Halaman 0 — Panduan sederhana untuk pembaca umum / pelaku industri.

Tidak memakai istilah teknik tanpa penjelasan. Tujuannya: orang yang belum
pernah dengar "CHT" atau "LCC" tetap bisa paham apa yang sedang dilihat dan
kenapa hasilnya begini.
"""

import streamlit as st

from app_core import sidebar_parameter, hitung_semua, tebal_komersial, rupiah

p = sidebar_parameter()
h = hitung_semua(p)
L_opt, LCC_opt, LCC_K0 = h["L_opt"], h["LCC_opt"], h["LCC_K0"]
L_pasar = tebal_komersial(L_opt)
hemat = LCC_K0 - LCC_opt

st.title("Panduan singkat")
st.caption(
    "Untuk pembaca yang baru pertama kali melihat dashboard ini — "
    "termasuk pelaku industri yang bukan peneliti."
)

# ── Apa yang sedang diteliti ─────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("#### Apa yang diteliti?")
    st.markdown(
        "Panci listrik mini (untuk masak air/mie instan) kehilangan panas "
        "lewat dindingnya — sama seperti gelas kopi panas yang lama-lama "
        "jadi dingin. Panas yang hilang ini **terbuang percuma sebagai "
        "listrik**, karena elemen pemanas harus terus bekerja "
        "menggantikannya.\n\n"
        "Solusinya: bungkus dinding panci dengan bahan isolasi (di sini "
        "dipakai **glasswool**, bahan yang sama seperti peredam suara/panas "
        "di rumah). Pertanyaannya: **seberapa tebal bungkusnya?** Terlalu "
        "tipis, masih boros listrik. Terlalu tebal, uang habis buat beli "
        "bahan yang manfaatnya sudah kecil. Penelitian ini mencari titik "
        "pas di antara keduanya."
    )

# ── Cara kerja penelitian, dalam 3 langkah ───────────────────────────────────
st.subheader("Bagaimana cara mencari jawabannya?")

k1, k2, k3 = st.columns(3)
with k1:
    with st.container(border=True, height="stretch"):
        st.markdown("**1. Ukur di komputer**")
        st.markdown(
            "Panci disimulasikan di software teknik (SolidWorks) dengan "
            "5 ketebalan pembungkus berbeda: 0, 5, 10, 15, dan 20 mm. "
            "Untuk tiap ketebalan, dihitung berapa **Watt** panas yang "
            "bocor keluar — sama seperti daya lampu, cuma ini daya yang "
            "terbuang, bukan yang berguna."
        )
with k2:
    with st.container(border=True, height="stretch"):
        st.markdown("**2. Hitung total biaya**")
        st.markdown(
            "Tiap ketebalan pembungkus punya dua biaya yang berlawanan "
            "arah: **biaya beli bahan** (makin tebal, makin mahal) dan "
            "**biaya listrik terbuang** (makin tebal, makin murah karena "
            "makin sedikit panas bocor). Keduanya dijumlahkan jadi satu "
            "angka: total biaya selama 5 tahun pemakaian."
        )
with k3:
    with st.container(border=True, height="stretch"):
        st.markdown("**3. Cari titik termurah**")
        st.markdown(
            "Dari lima titik data itu, dibuat kurva perkiraan untuk semua "
            "ketebalan di antaranya (bukan cuma 5 titik). Lalu dicari "
            "ketebalan mana yang membuat **total biaya paling rendah**. "
            "Itulah jawaban akhirnya."
        )

# ── Jawaban dengan bahasa sangat sederhana ───────────────────────────────────
st.subheader("Apa hasilnya?")

with st.container(border=True):
    st.markdown(
        f"### Bungkus glasswool setebal **{L_pasar} mm** adalah pilihan "
        f"paling hemat"
    )
    st.markdown(
        f"- **Tanpa pembungkus** (panci polos): biaya listrik terbuang "
        f"selama 5 tahun sekitar **{rupiah(LCC_K0)}**.\n"
        f"- **Dengan glasswool {L_pasar} mm**: total biaya (beli bahan + "
        f"listrik terbuang) turun jadi sekitar **{rupiah(LCC_opt)}**.\n"
        f"- **Uang yang dihemat: {rupiah(hemat)}**, atau sekitar "
        f"**{hemat / LCC_K0 * 100:.0f} dari setiap 100 rupiah** biaya "
        f"listrik terbuang.\n"
        f"- Modal untuk beli bahan pembungkus **kembali dalam "
        f"{h['payback']:.1f} tahun** — setelah itu, penghematannya murni "
        f"untung."
    )
    st.caption(
        "Semua angka di atas untuk pemakaian panci **1 jam per hari** — "
        "asumsi resmi penelitian. Geser \"Lama pakai per hari\" di panel "
        "kiri untuk melihat perubahan bila panci dipakai lebih sering."
    )

st.info(
    "**Kenapa tidak dibungkus setebal mungkin saja?** Karena setelah "
    "sekitar 10–15 mm, tambahan bahan nyaris tidak menghemat listrik lagi "
    "— tapi tetap menambah biaya beli bahan. Seperti memakai 5 jaket "
    "sekaligus di cuaca dingin: jaket ke-2 masih terasa manfaatnya, "
    "jaket ke-5 cuma bikin berat tanpa tambahan hangat yang berarti.",
    icon=":material/lightbulb:",
)

# ── Istilah yang mungkin membingungkan ───────────────────────────────────────
st.subheader("Istilah yang dipakai di dashboard ini")
st.caption("Supaya halaman lain lebih mudah diikuti")

istilah = [
    ("CHT (Conjugate Heat Transfer)",
     "Nama teknik untuk simulasi komputer yang menghitung bagaimana panas "
     "berpindah lewat benda padat (dinding panci) dan udara sekaligus. "
     "Ini yang menghasilkan angka Watt di setiap ketebalan."),
    ("LCC (Life Cycle Cost)",
     "Total biaya sesuatu selama seluruh umur pakainya — bukan cuma harga "
     "beli, tapi harga beli DITAMBAH biaya operasional (di sini: listrik "
     "yang terbuang) selama beberapa tahun ke depan."),
    ("Watt (W)",
     "Satuan daya — sama seperti yang tertulis di kemasan lampu atau "
     "setrika. Di sini dipakai untuk mengukur seberapa besar panas yang "
     "bocor keluar panci setiap detik."),
    ("Ketebalan optimal / L*",
     "Ketebalan pembungkus glasswool yang membuat total biaya (beli bahan "
     "+ listrik terbuang) paling rendah. Ini jawaban utama penelitian."),
    ("Balik modal (payback period)",
     "Berapa lama waktu yang dibutuhkan sampai uang yang dihemat dari "
     "tagihan listrik sama besarnya dengan uang yang dikeluarkan untuk "
     "beli bahan pembungkus."),
    ("Nilai sekarang / NPV",
     "Uang Rp 100.000 lima tahun lagi nilainya tidak sama dengan "
     "Rp 100.000 hari ini (karena inflasi, suku bunga, dll). NPV adalah "
     "cara menghitung \"berapa nilai uang itu kalau dihitung di hari "
     "ini\", supaya perbandingan biaya antar tahun jadi adil."),
    ("R² (R-kuadrat)",
     "Angka 0 sampai 1 yang menunjukkan seberapa cocok garis perkiraan "
     "dengan titik data asli. Semakin dekat ke 1 (misalnya 0,9997), "
     "semakin bisa dipercaya garis perkiraan itu."),
    ("Sensitivitas & Monte Carlo",
     "Cara menguji \"bagaimana kalau tebakan kita meleset?\" — misalnya "
     "kalau tarif listrik naik atau harga bahan berubah, apakah "
     "kesimpulannya masih sama? Ini cara peneliti menunjukkan hasilnya "
     "bisa dipercaya, bukan cuma kebetulan."),
]

for judul, isi in istilah:
    with st.expander(judul, icon=":material/help_outline:"):
        st.write(isi)

# ── Ke mana selanjutnya ──────────────────────────────────────────────────────
st.subheader("Mau lihat lebih jauh?")
st.markdown(
    "- **Hasil analisis** — angka lengkap dan gambar 3D panci\n"
    "- **Temuan utama** — kenapa hasilnya tidak bisa terus membaik "
    "walau dibungkus makin tebal\n"
    "- **Ketahanan hasil** — bukti bahwa kesimpulan ini tetap benar "
    "meski asumsi (tarif listrik, dll) meleset\n"
    "- **Metode & sumber** — untuk pembaca yang ingin detail teknis dan "
    "rumus yang dipakai\n"
    "- **Dampak nasional** — biaya per panci kelihatan kecil (puluhan "
    "ribu rupiah); halaman ini menunjukkan skalanya bila dipakai banyak unit"
)
