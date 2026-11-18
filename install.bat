@echo off
setlocal
set TARGET_DIR=%~1
if "%TARGET_DIR%"=="" set TARGET_DIR=.

echo [gemineone] Installing orchestration harness into %TARGET_DIR%...
if not exist "%TARGET_DIR%\.agents" mkdir "%TARGET_DIR%\.agents"
xcopy /E /I /Y "%~dp0.agents" "%TARGET_DIR%\.agents"
if not exist "%TARGET_DIR%\GEMINI.md" (
    copy /Y "%~dp0GEMINI.md" "%TARGET_DIR%\GEMINI.md"
    echo [gemineone] Created GEMINI.md in target.
) else (
    echo [gemineone] GEMINI.md already exists in target, preserving existing file.
)
echo [gemineone] Installation complete! Fast Intake + Max-Effort Swarm is ready.
endlocal
