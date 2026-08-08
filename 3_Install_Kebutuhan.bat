@echo off
REM ============================================================
REM  Pasang library Python yang dibutuhkan.
REM  Hanya perlu dijalankan bila muncul error ModuleNotFoundError.
REM ============================================================
cd /d "%~dp0"

echo.
echo  Memasang library yang dibutuhkan (numpy, scipy, matplotlib,
echo  pandas, streamlit). Perlu koneksi internet.
echo.

python -m pip install -r requirements.txt

echo.
echo  Selesai. Tekan tombol apa saja untuk menutup.
pause >nul
