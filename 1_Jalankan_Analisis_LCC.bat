@echo off
REM ============================================================
REM  Jalankan analisis LCC (lcc_optimizer.py)
REM  Klik dua kali file ini. Tidak perlu PowerShell.
REM ============================================================
cd /d "%~dp0"

echo.
echo  ============================================================
echo   ANALISIS CHT-LCC GLASSWOOL
echo   Proses memakan waktu 1-2 menit (Monte Carlo 10.000 skenario)
echo   Jangan tutup jendela ini sampai muncul tulisan SELESAI.
echo  ============================================================
echo.

python lcc_optimizer.py

echo.
if errorlevel 1 (
  echo  ------------------------------------------------------------
  echo   GAGAL. Baca pesan error di atas.
  echo   Bila tertulis ModuleNotFoundError, jalankan dulu:
  echo       2_Install_Kebutuhan.bat
  echo  ------------------------------------------------------------
) else (
  echo  ------------------------------------------------------------
  echo   SELESAI. Hasil gambar dan CSV ada di folder: output\
  echo  ------------------------------------------------------------
  echo.
  echo  Membuka folder output...
  start "" "%~dp0output"
)

echo.
echo  Tekan tombol apa saja untuk menutup jendela ini.
pause >nul
