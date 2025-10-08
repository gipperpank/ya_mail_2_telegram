@echo off
echo Alternative virtual environment creation...

:: Try different Python commands
echo Trying 'python' command...
python -m venv yandex_mail_bot_env
if exist "yandex_mail_bot_env" goto success

echo Trying 'py' command...
py -m venv yandex_mail_bot_env
if exist "yandex_mail_bot_env" goto success

echo Trying 'python3' command...
python3 -m venv yandex_mail_bot_env
if exist "yandex_mail_bot_env" goto success

echo All methods failed. Creating manual structure...
mkdir yandex_mail_bot_env
mkdir yandex_mail_bot_env\Scripts
mkdir yandex_mail_bot_env\Include
mkdir yandex_mail_bot_env\Lib
echo Manual structure created. Please install dependencies manually.
goto install

:success
echo Virtual environment created successfully!

:install
if exist "yandex_mail_bot_env\Scripts\activate.bat" (
    echo Activating and installing dependencies...
    call yandex_mail_bot_env\Scripts\activate.bat
    pip install imapclient pytelegrambotapi pillow requests beautifulsoup4 lxml
) else (
    echo Installing dependencies globally...
    pip install imapclient pytelegrambotapi pillow requests beautifulsoup4 lxml
)

echo Setup complete!
pause