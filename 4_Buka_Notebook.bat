@echo off
REM ============================================================
REM  Buka notebook analisis di browser (Jupyter Lab)
REM  Klik dua kali file ini.
REM ============================================================
cd /d "%~dp0"

echo.
echo  ============================================================
echo   NOTEBOOK ANALISIS CHT-LCC
echo  ============================================================
echo.
echo   Browser akan terbuka sendiri. Klik file:
echo       Analisis_CHT_LCC.ipynb
echo.
echo   Cara memakai di dalam notebook:
echo     - Jalankan sel satu per satu: Shift + Enter
echo     - Jalankan semua sekaligus  : menu Run - Run All Cells
echo     - Sel Monte Carlo perlu 1-2 menit, harap ditunggu
echo.
echo   JANGAN TUTUP jendela hitam ini selama notebook dipakai.
echo   Untuk berhenti: tekan Ctrl + C di jendela ini.
echo.
echo  ============================================================
echo.

python -m jupyterlab "Analisis_CHT_LCC.ipynb"

echo.
echo  Notebook berhenti. Tekan tombol apa saja untuk menutup.
pause >nul
