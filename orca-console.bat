@echo off
cd /d "%~dp0"
title ORCA Controller Console
cls
echo ========================================================
echo  ORCA Controller Console
echo  Commands: orca status | orca setting | orca model | orca sync
echo ========================================================
echo.
call "%~dp0orca.cmd" status
echo.
cmd /k
