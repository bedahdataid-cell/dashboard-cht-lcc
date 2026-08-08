@echo off
REM ============================================================
REM  Buka dashboard Streamlit di browser
REM  Klik dua kali file ini. Browser terbuka sendiri.
REM ============================================================
cd /d "%~dp0"

echo.
echo  ============================================================
echo   DASHBOARD CHT-LCC GLASSWOOL
echo  ============================================================
echo.
echo   Browser akan terbuka sendiri ke http://localhost:8501
echo.
echo   JANGAN TUTUP jendela hitam ini selama dashboard dipakai.
echo   Untuk berhenti: tekan Ctrl + C di jendela ini.
echo.
echo   Catatan: dashboard hanya bisa diakses dari laptop ini
echo   (mode lokal, tidak dibagikan ke jaringan luar).
echo.
echo  ============================================================
echo.

python -m streamlit run streamlit_app.py --server.address localhost

echo.
echo  Dashboard berhenti. Tekan tombol apa saja untuk menutup.
pause >nul
