"""
validasi_churchill_chu.py
=========================
Validasi koefisien konveksi natural hasil simulasi CHT SolidWorks (h_FVM)
terhadap korelasi Churchill-Chu analitik — Penelitian CHT-LCC Glasswool Q2-8012.
Dosen: Bakti Alpihuda — Hibah Internal LPPM UMB 2026.

Acuan proposal §2.4.5: validasi LULUS bila |h_FVM - h_CC| / h_CC <= 10%.

Dua korelasi Churchill-Chu:
  [11] Plat/silinder VERTIKAL (untuk dinding samping panci):
       Nu = { 0.825 + 0.387*Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27) }^2
  [12] Silinder HORIZONTAL (untuk acuan tutup/alas, opsional):
       Nu = { 0.60 + 0.387*Ra^(1/6) / [1 + (0.559/Pr)^(9/16)]^(8/27) }^2

Sifat udara dievaluasi pada SUHU FILM: T_film = (T_dinding + T_ambien)/2.

CATATAN METODOLOGI (8 Agu 2026): h_FVM dari SolidWorks adalah koefisien GABUNGAN
konveksi+radiasi (radiative surface eksplisit SS304 eps=0.28 aktif di K0). Churchill-Chu
murni konvektif, jadi TIDAK apple-to-apple bila dibandingkan langsung.

DICOBA & DITOLAK: estimasi h_radiasi via koefisien radiatif linear (Stefan-Boltzmann,
h_rad = eps*sigma*(Ts^4-Tsur^4)/(Ts-Tsur)) dijumlahkan ke h_CC lalu dibandingkan ke h_FVM.
Hasil: gap MEMBESAR (15,10% -> 37,06%), h_total_teori (9,25) jauh > h_FVM (5,82) — arah
salah. Penyebab: rumus linear ini mengasumsikan permukaan memandang langsung ke lingkungan
radiasi tak-hingga pada T_sur seragam, mengabaikan view factor & domain komputasi terbatas
yang sudah dihitung akurat oleh solver Discrete Transfer SolidWorks — over-estimate h_rad.
Fungsi hitung_h_radiasi() DIPERTAHANKAN sbg info tambahan (bukan basis validasi resmi).

VALIDASI RESMI tetap: h_FVM (dinding vertikal saja, exclude tutup) vs h_Churchill-Chu murni
konvektif — lihat status "STATUS VALIDASI" utama di bawah. Untuk kuantifikasi kontribusi
radiasi yang akurat, cara yang benar adalah uji ON/OFF radiasi LANGSUNG DI SOLVER SolidWorks
(clone project, matikan Radiation di General Settings, run ulang) — bukan hitung tangan,
seperti sudah dilakukan untuk K1 (lihat project_simulasi_cht_k0.md, kontribusi radiasi 38,7%).

Jalankan:  python validasi_churchill_chu.py
"""

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# INPUT — DATA DARI SIMULASI CHT (K0, 8 Agu 2026 — geometri baru + BC/radiative surface lengkap)
#   Ganti nilai ini sesuai hasil Surface Parameters tiap konfigurasi.
# ─────────────────────────────────────────────────────────────────────────────
T_dinding = 94.86      # °C  — Temperature (Solid) Average, DINDING SAMPING SAJA (Surface Parameters 2, 0,0395 m², exclude tutup)
T_ambien  = 27.0       # °C  — suhu udara ambien (Tasikmalaya, proposal)
L_dinding = 0.110      # m   — tinggi karakteristik dinding vertikal Lc (tinggi wadah luar, geometri koreksi 2026-08-06)
h_FVM     = 5.821      # W/m2.K — h DINDING SAMPING SAJA (Surface Parameters 2, exclude tutup horizontal — apple-to-apple dgn korelasi vertikal)

EPSILON   = 0.28       # emisivitas SS304 (Radiative Surface eksplisit yg dipakai di K0, lihat PANDUAN_SIMULASI_CHT_K0-K4.md §5)
T_SUR     = T_ambien   # °C — suhu lingkungan radiasi = Radiation Environment Temp Wizard SolidWorks (sama dgn T_ambien)
SIGMA     = 5.670374e-8  # W/m2.K4 — konstanta Stefan-Boltzmann

GRAVITASI = 9.81       # m/s²

# ─────────────────────────────────────────────────────────────────────────────
# SIFAT TERMOFISIKA UDARA pada suhu film (interpolasi linier dari tabel standar)
#   Sumber: tabel sifat udara (Incropera/Cengel), tekanan atmosfer.
#   Tabel acuan (T °C : rho, k, nu, Pr, beta=1/T_K):
# ─────────────────────────────────────────────────────────────────────────────
# T(°C),  k(W/mK),   nu(m²/s),     Pr
_TBL = np.array([
    [ 27.0, 0.02624, 15.89e-6, 0.7282],
    [ 47.0, 0.02808, 17.95e-6, 0.7241],
    [ 60.0, 0.02881, 18.90e-6, 0.7202],   # ~ interpolasi
    [ 77.0, 0.02991, 20.92e-6, 0.7177],
    [ 97.0, 0.03156, 23.06e-6, 0.7137],
    [127.0, 0.03365, 26.41e-6, 0.7100],
])

def sifat_udara(T_c):
    """Interpolasi sifat udara pada suhu T (°C) dari tabel standar."""
    k  = np.interp(T_c, _TBL[:, 0], _TBL[:, 1])
    nu = np.interp(T_c, _TBL[:, 0], _TBL[:, 2])
    Pr = np.interp(T_c, _TBL[:, 0], _TBL[:, 3])
    beta = 1.0 / (T_c + 273.15)   # gas ideal: beta = 1/T_film(K)
    return k, nu, Pr, beta


def rayleigh(T_s, T_inf, Lc):
    """Bilangan Rayleigh Ra = g*beta*dT*Lc^3 / nu^2 * Pr, sifat pada suhu film."""
    T_film = 0.5 * (T_s + T_inf)
    k, nu, Pr, beta = sifat_udara(T_film)
    dT = abs(T_s - T_inf)
    Ra = GRAVITASI * beta * dT * Lc**3 / (nu**2) * Pr
    return Ra, Pr, k, T_film


def nu_churchill_chu_vertikal(Ra, Pr):
    """Churchill-Chu plat vertikal [11] — untuk dinding samping."""
    num = 0.387 * Ra**(1/6)
    den = (1.0 + (0.492 / Pr)**(9/16))**(8/27)
    return (0.825 + num / den)**2


def nu_churchill_chu_horizontal(Ra, Pr):
    """Churchill-Chu silinder horizontal [12] — acuan tutup/alas."""
    num = 0.387 * Ra**(1/6)
    den = (1.0 + (0.559 / Pr)**(9/16))**(8/27)
    return (0.60 + num / den)**2


def hitung_h_cc(T_s, T_inf, Lc, mode="vertikal"):
    """Hitung h dari korelasi Churchill-Chu. Mengembalikan dict ringkas."""
    Ra, Pr, k, T_film = rayleigh(T_s, T_inf, Lc)
    if mode == "vertikal":
        Nu = nu_churchill_chu_vertikal(Ra, Pr)
    else:
        Nu = nu_churchill_chu_horizontal(Ra, Pr)
    h = Nu * k / Lc
    return dict(Ra=Ra, Pr=Pr, k=k, T_film=T_film, Nu=Nu, h=h, mode=mode)


def hitung_h_radiasi(T_s_c, T_sur_c, eps):
    """Koefisien radiatif linear: h_rad = eps*sigma*(Ts^4 - Tsur^4)/(Ts - Tsur).
    Ts, Tsur dalam Kelvin untuk pangkat 4; hasil h_rad dalam W/m2.K (Incropera eq. 1.9)."""
    Ts_K, Tsur_K = T_s_c + 273.15, T_sur_c + 273.15
    if abs(Ts_K - Tsur_K) < 1e-9:
        return eps * SIGMA * 4 * Ts_K**3  # limit turunan saat Ts=Tsur
    return eps * SIGMA * (Ts_K**4 - Tsur_K**4) / (Ts_K - Tsur_K)


# ─────────────────────────────────────────────────────────────────────────────
# EKSEKUSI
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 64)
    print(" VALIDASI CHURCHILL-CHU - Konveksi Natural Dinding Luar Panci")
    print(" Penelitian CHT-LCC Glasswool Q2-8012 | LPPM UMB 2026")
    print("=" * 64)
    print(f"  Suhu dinding (T_s)   : {T_dinding:.2f} °C")
    print(f"  Suhu ambien (T_inf)  : {T_ambien:.2f} °C")
    print(f"  Tinggi karakter (Lc) : {L_dinding:.3f} m")
    print(f"  h_FVM (SolidWorks)   : {h_FVM:.3f} W/m2.K")
    print("-" * 64)

    r = hitung_h_cc(T_dinding, T_ambien, L_dinding, mode="vertikal")
    print(f"  Suhu film            : {r['T_film']:.2f} °C")
    print(f"  Pr                   : {r['Pr']:.4f}")
    print(f"  k udara              : {r['k']:.5f} W/m.K")
    print(f"  Rayleigh (Ra)        : {r['Ra']:.3e}")
    rezim = "LAMINAR (Ra<1e9) [OK]" if r['Ra'] < 1e9 else "TURBULEN (Ra>=1e9)"
    print(f"  Rezim aliran         : {rezim}")
    print(f"  Nusselt (Nu)         : {r['Nu']:.3f}")
    print(f"  h_Churchill-Chu (konveksi murni) : {r['h']:.3f} W/m2.K")
    print("-" * 64)

    selisih_abs = abs(h_FVM - r['h'])
    selisih_pct = selisih_abs / r['h'] * 100.0
    print(f"  Selisih |h_FVM - h_CC| : {selisih_abs:.3f} W/m2.K")
    print(f"  Selisih relatif        : {selisih_pct:.2f} %")
    lulus = selisih_pct <= 10.0
    status = "LULUS [<=10%]" if lulus else "TIDAK LULUS [>10%]"
    print(f"  STATUS VALIDASI        : {status}")
    print("=" * 64)

    if not lulus:
        print("\n  CATATAN bila TIDAK lulus — periksa:")
        print("   - Lc tepat? (tinggi dinding vs panjang karakteristik silinder)")
        print("   - h_FVM rata-rata di permukaan yang BENAR (dinding vertikal saja)?")
        print("   - Mesh masih kasar -> jalankan mesh independence dulu.")
        print("   - Kriteria Cebeci: kelengkungan silinder signifikan? (D/L besar)")
        print("   - Radiasi tercampur di h_FVM (h_FVM idealnya konvektif murni) —")
        print("     kuantifikasi via uji ON/OFF radiasi LANGSUNG DI SOLVER (bukan")
        print("     estimasi tangan, lihat CATATAN METODOLOGI di docstring atas).")
    else:
        print("\n  Validasi metodologi CHT terkonfirmasi terhadap korelasi analitik.")

    # ── perbandingan informatif: korelasi horizontal (acuan tutup/alas) ──
    rh = hitung_h_cc(T_dinding, T_ambien, L_dinding, mode="horizontal")
    print(f"\n  [info] h korelasi horizontal (acuan tutup/alas): "
          f"{rh['h']:.3f} W/m2.K (Lc perlu disesuaikan utk geometri horizontal)")

    # ── info tambahan (BUKAN basis validasi): estimasi h_radiasi linear ──
    # Ditolak sbg metode validasi (lihat CATATAN METODOLOGI) — hanya utk gambaran
    # kasar orde-besaran, tidak mempertimbangkan view factor & domain terbatas.
    h_rad = hitung_h_radiasi(T_dinding, T_SUR, EPSILON)
    print(f"\n  [info, bukan basis validasi] h_radiasi linear (eps={EPSILON}): "
          f"{h_rad:.3f} W/m2.K — TERBUKTI over-estimate, lihat docstring.")


if __name__ == "__main__":
    main()
