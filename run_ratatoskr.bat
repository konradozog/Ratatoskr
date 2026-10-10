@echo off
rem Launch Ratatoskr in the background (no console window) using the project venv.
cd /d "%~dp0"
start "" "%~dp0.venv\Scripts\pythonw.exe" -m ratatoskr
