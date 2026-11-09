@echo off
setlocal
cd /d "%~dp0.."
set "SENSING_PYTHON=%USERPROFILE%\radioconda\python.exe"
if not exist "%SENSING_PYTHON%" (
  echo Radioconda Python was not found at "%SENSING_PYTHON%".
  echo Open your Radioconda Prompt and run:
  echo python simulation\run_calibration_experiments.py
  pause
  exit /b 1
)
"%SENSING_PYTHON%" -u simulation\run_calibration_experiments.py
if errorlevel 1 (
  echo Experiment did not complete. See the error above and study_plan.json.
) else (
  echo Upload study_summary.json and calibration.json from the printed study directory.
)
pause
