@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Open Radioconda Prompt and run python cooperative_sensing\run_signed_detector.py
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -c "import cryptography" >nul 2>&1
if errorlevel 1 (
  echo Install the signature dependency in Radioconda Prompt first:
  echo python -m pip install -r cooperative_sensing\requirements-trust.txt
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u cooperative_sensing\run_signed_detector.py
if errorlevel 1 (
  echo Integration run failed or incomplete. Review the error above.
) else (
  echo Upload signed_detector_summary.json from the printed directory.
  echo Keep the entire directory with signed audits and batch records.
)
pause
