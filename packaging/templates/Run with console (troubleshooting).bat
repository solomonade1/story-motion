@echo off
rem Same as the normal launcher, but keeps a window open so error messages stay visible.
cd /d "%~dp0"
"%~dp0python\python.exe" -m storymotion_media doctor
echo.
"%~dp0python\python.exe" -m storymotion_media launch
echo.
pause
