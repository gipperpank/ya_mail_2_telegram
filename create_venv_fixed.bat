@echo off
echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv yandex_mail_bot_env

if exist "yandex_mail_bot_env" (
    echo Virtual environment created successfully!
) else (
    echo ERROR: Failed to create virtual environment
    echo Trying alternative method...
    py -m venv yandex_mail_bot_env
    if exist "yandex_mail_bot_env" (
        echo Virtual environment created successfully with py command!
    ) else (
        echo ERROR: Still failed to create virtual environment
        echo Please check Python installation
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call yandex_mail_bot_env\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install imapclient
pip install pytelegrambotapi
pip install pillow
pip install requests

echo.
echo ========================================
echo Virtual environment setup complete!
echo ========================================
echo.
echo To activate the environment, run:
echo   yandex_mail_bot_env\Scripts\activate.bat
echo.
echo Then run the bot with:
echo   python yandex_mail_bot.py
echo.
pause