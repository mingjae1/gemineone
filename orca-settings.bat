@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" "pythonw" "%~dp0.agents\scripts\orca_gui.py"
) else (
    start "" "python" "%~dp0.agents\scripts\orca_gui.py"
)
