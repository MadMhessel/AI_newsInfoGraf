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

if not exist venv (
    echo [INIT] Создаем изолированное окружение...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Не удалось создать venv. Проверьте установку Python.
        pause
        exit /b
    )
    echo [OK] Окружение создано.
)

:: 2. АКТИВАЦИЯ ОКРУЖЕНИЯ
call venv\Scripts\activate

:: 3. УСТАНОВКА ЗАВИСИМОСТЕЙ ВНУТРЬ VENV
echo [AUTO] Проверка и установка библиотек...
python -m pip install --upgrade pip --disable-pip-version-check
:: Добавляем Pillow для работы с изображениями
pip install python-telegram-bot requests python-dotenv Pillow


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