"""
energy_balance_k1.py
====================
Uji kesetimbangan energi (energy balance check) K1 -- model resistansi termal
paralel: dinding (glasswool) + alas bawah (glasswool) + tutup (SS304, tanpa insulasi).

Tujuan: verifikasi independen apakah Q hasil Goal Plot SolidWorks (7.429 W) konsisten
dengan Q konduksi Fourier lewat tiap jalur, TANPA bergantung pada korelasi Churchill-Chu.

Perlu data tambahan dari SolidWorks: suhu rata-rata TUTUP saja (Surface Parameters,
pilih HANYA face Tutup_SS), terpisah dari suhu dinding+alas glasswool.
"""

import numpy as np

# ── Data dari simulasi K1 (radiasi ON, hasil Goal Plot & Surface Parameters) ──
T_dinding_dalam = 95.0     # C -- BC Real Wall (sisi dalam wadah, kontak air)
T_ambien        = 27.0     # C

Q_goalplot      = 7.429    # W -- total rugi panas hasil Goal Plot (radiasi ON)

# Suhu rata-rata gabungan (dinding+alas glasswool+tutup) dari Surface Parameters awal
T_luar_gabungan = 53.47    # C

# TODO: isi dari Surface Parameters baru (HANYA face Tutup_SS)
T_tutup         = None     # C -- GANTI setelah cek SolidWorks

# ── Geometri ──
k_gw   = 0.036      # W/m.K -- glasswool
k_SS   = 16.0       # W/m.K -- AISI 304
L      = 0.135      # m -- tinggi dinding
r1     = 0.0605     # m -- radius dalam glasswool (= radius luar wadah SS)
r2     = 0.0655     # m -- radius luar glasswool (K1, tebal 5 mm)
t_alas_gw = 0.005    # m -- tebal alas glasswool (5 mm, sama dgn dinding K1)
t_tutup   = 0.001    # m -- tebal tutup SS (proposal: 1 mm)
r_tutup   = 0.0605   # m -- radius tutup (radius luar wadah, tutup menutup bagian atas)


def q_dinding(dT):
    """Konduksi radial lewat dinding silinder glasswool (Fourier 1-D radial)."""
    return 2 * np.pi * k_gw * L * dT / np.log(r2 / r1)


def q_alas(dT):
    """Konduksi 1-D lewat alas bawah glasswool (pelat datar, luas lingkaran r2)."""
    A = np.pi * r2**2
    return k_gw * A * dT / t_alas_gw


def q_tutup(dT):
    """Konduksi 1-D lewat tutup SS304 (TANPA glasswool -- jalur bocor panas)."""
    A = np.pi * r_tutup**2
    return k_SS * A * dT / t_tutup


def main():
    print("=" * 64)
    print(" ENERGY BALANCE CHECK -- K1 (Model Resistansi Termal Paralel)")
    print("=" * 64)

    dT_dinding_alas = T_dinding_dalam - T_luar_gabungan
    print(f"  Delta T dinding/alas (95 - {T_luar_gabungan}) : {dT_dinding_alas:.2f} C")

    Qd = q_dinding(dT_dinding_alas)
    Qa = q_alas(dT_dinding_alas)
    print(f"  Q dinding (glasswool)  : {Qd:.3f} W")
    print(f"  Q alas    (glasswool)  : {Qa:.3f} W")

    if T_tutup is None:
        print("\n  [!] T_tutup belum diisi -- lengkapi dari Surface Parameters SolidWorks")
        print("      (pilih HANYA face Tutup_SS, catat Temperature Solid Average)")
        print(f"\n  Sementara, estimasi kasar pakai T_tutup = T_luar_gabungan ({T_luar_gabungan} C):")
        dT_tutup_est = T_dinding_dalam - T_luar_gabungan
        Qt_est = q_tutup(dT_tutup_est)
        print(f"  Q tutup (estimasi kasar, SS304 tanpa insulasi): {Qt_est:.3f} W")
        Q_total_est = Qd + Qa + Qt_est
        print(f"\n  Q total estimasi        : {Q_total_est:.3f} W")
        print(f"  Q Goal Plot (SolidWorks): {Q_goalplot} W")
        selisih_est = abs(Q_total_est - Q_goalplot) / Q_goalplot * 100
        print(f"  Selisih (estimasi)      : {selisih_est:.2f} %")
        print("\n  Catatan: jika T_tutup asli lebih TINGGI dari T_luar_gabungan")
        print("  (karena SS304 tutup tanpa insulasi wajar lebih panas dari")
        print("  permukaan glasswool berinsulasi), maka dT_tutup lebih KECIL,")
        print("  Q_tutup akan TURUN dari estimasi ini -- hasil akan lebih presisi")
        print("  setelah T_tutup asli dimasukkan.")
        return

    dT_tutup = T_dinding_dalam - T_tutup
    Qt = q_tutup(dT_tutup)
    print(f"  Delta T tutup (95 - {T_tutup})     : {dT_tutup:.2f} C")
    print(f"  Q tutup (SS304, tanpa insulasi)    : {Qt:.3f} W")

    Q_total = Qd + Qa + Qt
    print(f"\n  Q total (dinding+alas+tutup) : {Q_total:.3f} W")
    print(f"  Q Goal Plot (SolidWorks)     : {Q_goalplot} W")

    selisih = abs(Q_total - Q_goalplot) / Q_goalplot * 100
    print(f"  Selisih                      : {selisih:.2f} %")
    status = "KONSISTEN (<=15%)" if selisih <= 15 else "PERLU DICEK LEBIH LANJUT"
    print(f"  Status                       : {status}")


if __name__ == "__main__":
    main()
