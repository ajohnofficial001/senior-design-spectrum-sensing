@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Radioconda Python not found. Open Radioconda Prompt and follow cooperative_sensing\COMBINED_RELIABILITY.md.
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -c "from gnuradio import gr; import cryptography" >nul 2>&1
if errorlevel 1 (
  echo GNU Radio or cryptography is unavailable in Radioconda.
  echo For cryptography run in PowerShell:
  echo ^& "%SENSING_PYTHON%" -m pip install -r cooperative_sensing\requirements-trust.txt
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u cooperative_sensing\run_combined_reliability.py
if errorlevel 1 (
  echo Study incomplete. Review the error and combined_plan.json.
) else (
  echo Upload combined_summary.json from the printed directory.
  echo Keep the complete output folder, including acquisitions and signed audits.
)
pause
