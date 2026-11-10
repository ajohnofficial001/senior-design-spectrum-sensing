@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Open Radioconda Prompt and run python simulation\run_reference_confirmation.py
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u simulation\run_reference_confirmation.py
if errorlevel 1 (
  echo Study incomplete. Review the error and reference_plan.json.
) else (
  echo Upload reference_summary.json and reference_comparison.csv from the printed directory.
)
pause
