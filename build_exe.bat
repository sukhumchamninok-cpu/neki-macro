@echo off
title Neki Macro - Build to EXE
echo ============================================
echo   Neki Macro v.1 - Build EXE Script
echo   Written By Neki
echo ============================================
echo.

echo [1/3] Installing required packages...
pip install pyinstaller customtkinter keyboard tkinterdnd2
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. Please check your Python/pip installation.
    pause
    exit /b 1
)

echo.
echo [2/3] Building NekiMacro.exe (this may take a minute)...
pyinstaller --onefile --windowed --name "NekiMacro" --collect-all tkinterdnd2 --clean neki_macro.py
if errorlevel 1 (
    echo.
    echo ERROR: Build failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo Your EXE file is located at: dist\NekiMacro.exe
echo.
echo TIP: Right-click NekiMacro.exe and choose "Run as administrator"
echo      so global hotkeys work correctly in all applications.
echo.
pause
