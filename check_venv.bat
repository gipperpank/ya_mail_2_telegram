@echo off
echo === Environment Check ===
echo.

echo Python version:
python --version
echo.

echo PIP version:
pip --version
echo.

echo Checking virtual environment...
if exist "yandex_mail_bot_env" (
    echo Virtual environment folder exists
    echo.
    echo Checking virtual environment structure...
    if exist "yandex_mail_bot_env\Scripts\activate.bat" (
        echo activate.bat found
    ) else (
        echo activate.bat NOT found
    )
    if exist "yandex_mail_bot_env\Scripts\python.exe" (
        echo python.exe found
    ) else (
        echo python.exe NOT found
    )
) else (
    echo Virtual environment folder NOT found
)

echo.
echo Checking dependencies...
pip list | findstr "imapclient telebot pillow requests"
echo.

pause