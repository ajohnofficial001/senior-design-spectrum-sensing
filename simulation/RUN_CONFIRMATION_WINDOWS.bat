@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Open Radioconda Prompt and run python simulation\run_frozen_confirmation.py
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u simulation\run_frozen_confirmation.py
if errorlevel 1 (
  echo Confirmation did not complete. Review the error and confirmation_plan.json.
) else (
  echo Upload confirmation_summary.json and confirmation_comparison.csv from the printed directory.
)
pause
