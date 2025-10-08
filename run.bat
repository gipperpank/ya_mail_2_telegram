@echo off
echo Activating virtual environment...
call yandex_mail_bot_env\Scripts\activate.bat

echo Starting Yandex Mail to Telegram Bot...
python yandex_mail_bot.py

pause