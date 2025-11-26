@echo off
chcp 65001
TITLE Infographic AI Bot

echo ===================================================
echo   ПРОВЕРКА И УСТАНОВКА ЗАВИСИМОСТЕЙ
echo ===================================================

:: Проверяем, установлен ли Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: Python не установлен! Установите Python 3.10+ и поставьте галочку "Add to PATH".
    pause
    exit
)

:: Установка библиотек
echo Устанавливаю необходимые библиотеки...
pip install python-telegram-bot google-generativeai python-dotenv

echo.
echo ===================================================
echo   ЗАПУСК БОТА
echo ===================================================
echo.

python bot.py

if %errorlevel% neq 0 (
    echo.
    echo Бот упал с ошибкой. Смотри текст выше.
    pause
)