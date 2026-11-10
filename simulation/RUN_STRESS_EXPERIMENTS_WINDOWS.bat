@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Open Radioconda Prompt and run python simulation\run_stress_experiments.py
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u simulation\run_stress_experiments.py
if errorlevel 1 (
  echo Stress study incomplete. Review the error and stress_plan.json.
) else (
  echo Upload stress_summary.json and stress_comparison.csv from the printed directory.
)
pause
