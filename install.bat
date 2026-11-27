@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "NoDefaultCurrentDirectoryInExePath=1"

set "TARGET_DIR=%~1"
setlocal EnableDelayedExpansion
if "!TARGET_DIR!"=="" set "TARGET_DIR=."

rem Reject cmd.exe metacharacters in TARGET_DIR before path normalization or command invocation
set "CHECK_DIR=!TARGET_DIR!"
if not "!CHECK_DIR!"=="!CHECK_DIR:&=!" goto :invalid_target
if not "!CHECK_DIR!"=="!CHECK_DIR:|=!" goto :invalid_target
if not "!CHECK_DIR!"=="!CHECK_DIR:<=!" goto :invalid_target
if not "!CHECK_DIR!"=="!CHECK_DIR:>=!" goto :invalid_target
if not "!CHECK_DIR!"=="!CHECK_DIR:^=!" goto :invalid_target
if not "!CHECK_DIR!"=="!CHECK_DIR:%%=!" goto :invalid_target
if not "!CHECK_DIR!"=="!CHECK_DIR:;=!" goto :invalid_target

rem Strip trailing backslashes cleanly; append '.' for root paths (\ or X:\) so \" never escapes closing quotes
:strip_slash
if "!TARGET_DIR!"=="\" goto :slash_done
if "!TARGET_DIR:~1!"==":\" goto :slash_done
if "!TARGET_DIR:~-1!"=="\" (
    set "TARGET_DIR=!TARGET_DIR:~0,-1!"
    goto :strip_slash
)
:slash_done
if "!TARGET_DIR:~-1!"=="\" set "TARGET_DIR=!TARGET_DIR!."

echo [gemineone 0.4.1] Installing self-bootstrapping orchestration harness into !TARGET_DIR!...
if not exist "!TARGET_DIR!\.agents" mkdir "!TARGET_DIR!\.agents"
robocopy "%~dp0.agents" "!TARGET_DIR!\.agents" /E /XJ /XD __pycache__ /XF orca-audit.log .orca-state.json *.pyc >nul
if errorlevel 8 (
    echo [gemineone] ERROR: Failed to copy .agents directory into !TARGET_DIR!.
    exit /b 1
)

if not exist "!TARGET_DIR!\GEMINI.md" (
    copy /Y "%~dp0GEMINI.md" "!TARGET_DIR!\GEMINI.md" >nul
    echo [gemineone] Created GEMINI.md in target.
) else (
    echo [gemineone] GEMINI.md already exists in target, preserving existing file.
)

set "PYTHON_CMD="
where $path:python.exe >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
) else (
    where $path:py.exe >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if "!PYTHON_CMD!"=="" (
    echo [gemineone] WARNING: Python not found in PATH. Skipping bootstrap probe.
    echo [gemineone] Install Python 3 and run:
    echo   python -X utf8 "!TARGET_DIR!\.agents\scripts\bootstrap.py" --probe-and-configure --target "!TARGET_DIR!"
    exit /b 1
)

echo [gemineone] Running self-bootstrapping environment probe...
!PYTHON_CMD! -X utf8 "!TARGET_DIR!\.agents\scripts\bootstrap.py" --probe-and-configure --target "!TARGET_DIR!"
if errorlevel 1 (
    echo [gemineone] ERROR: Bootstrap probe failed with exit code !ERRORLEVEL!.
    exit /b !ERRORLEVEL!
)

echo [gemineone] Installation and Phase 1 bootstrap complete!
echo [gemineone] Open SETUP.md in your first AI session, then run:
echo   python -X utf8 .agents/scripts/bootstrap.py --finalize --target .
endlocal
endlocal
exit /b 0

:invalid_target
echo [gemineone] ERROR: Target directory contains disallowed characters: !TARGET_DIR!
endlocal
endlocal
exit /b 1
