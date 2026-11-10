@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Open Radioconda Prompt and run python simulation\run_window_experiments.py
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u simulation\run_window_experiments.py
if errorlevel 1 (
  echo Study did not finish. Review the error and window_plan.json.
) else (
  echo Upload window_summary.json and window_comparison.csv from the printed directory.
)
pause
