@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Open Radioconda Prompt and run python simulation\run_noise_aware_experiments.py
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u simulation\run_noise_aware_experiments.py
if errorlevel 1 (
  echo Study incomplete. Review the error and noise_aware_plan.json.
) else (
  echo Upload noise_aware_summary.json and noise_aware_comparison.csv from the printed directory.
)
pause
