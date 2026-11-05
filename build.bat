@echo off
rem Build dist\Screen Recorder.exe (see docs\BUILD.md)
call "%~dp0src\build.bat" || exit /b 1
echo.
echo Output: src\dist\Screen Recorder.exe
