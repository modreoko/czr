@echo off
echo Starting Zmluvy application...

REM Run PowerShell script
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start.ps1"

echo Application started. Press any key to exit...
pause > nul