import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TEXT_MODEL_NAME = os.getenv("TEXT_MODEL_NAME", "gemini-1.5-pro-latest")
IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL_NAME", "imagen-3.0-generate-001")

# Настройка Google GenAI
genai.configure(api_key=GOOGLE_API_KEY)

async def generate_ai_content(user_text: str):
    """
    Функция, где ИИ принимает решения.
    1. Анализирует текст.
    2. Придумывает концепцию инфографики.
    3. Генерирует изображение.
    """
    try:
        # ЭТАП 1: Текстовый анализ и создание промпта для картинки
        # Мы просим ИИ выступить в роли арт-директора
        text_model = genai.GenerativeModel(TEXT_MODEL_NAME)
        
        system_instruction = (
            "Ты — профессиональный дизайнер инфографики и новостной аналитик. "
            "Твоя задача: прочитать новость и создать детальное описание (промпт) на английском языке "
            "для генерации изображения, которое будет представлять собой стильную, минималистичную инфографику, "
            "отражающую суть этой новости. "
            "Не используй текст на картинке, только визуальные метафоры, графики, иконки и схемы. "
            "Ответ должен содержать ТОЛЬКО промпт на английском."
        )
        
        logging.info("Отправка запроса на генерацию промпта...")
        prompt_response = text_model.generate_content(f"{system_instruction}\n\nНовость: {user_text}")
        image_prompt = prompt_response.text.strip()
        
        logging.info(f"ИИ сгенерировал промпт для изображения: {image_prompt}")

        # ЭТАП 2: Генерация изображения на основе решения ИИ
        # Используем модель Imagen
        image_model = genai.ImageGenerationModel(IMAGE_MODEL_NAME)
        
        logging.info("Генерация изображения...")
        images = image_model.generate_images(
            prompt=image_prompt,
            number_of_images=1,
            aspect_ratio="3:4", # Вертикальный формат удобен для мобильных
            safety_filter="block_only_high",
        )
        
        return images[0], image_prompt

    except Exception as e:
        logging.error(f"Ошибка AI: {e}")
        raise e

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    if not user_text:
        return

    status_message = await update.message.reply_text("🧠 ИИ анализирует новость и придумывает инфографику...")

    try:
        # Запуск логики ИИ
        image_result, used_prompt = await generate_ai_content(user_text)
        
        # Сохранение во временный буфер (или файл) не обязательно,
        # библиотека genai возвращает объект, который можно сохранить.
        # Для отправки в телеграм сохраним временно на диск.
        file_path = "temp_infographic.jpg"
        image_result.save(file_path)

        await status_message.edit_text("🎨 Рисую изображение...")

        # Отправка фото
        with open(file_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📊 **Инфографика готова!**\n\n_ИИ решил визуализировать это так:_\n{used_prompt}",
                parse_mode="Markdown"
            )
        
        # Удаление временного сообщения и файла
        await status_message.delete()
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        error_msg = f"Произошла ошибка при генерации: {str(e)}"
        if "400" in str(e):
             error_msg += "\n\nВозможно, ваш API ключ не имеет доступа к Imagen 3 или генерации изображений."
        await status_message.edit_text(error_msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот-генератор инфографики.\n"
        "Отправь мне текст новости, и я через Gemini создам для неё визуализацию."
    )

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GOOGLE_API_KEY:
        print("ОШИБКА: Не заданы API ключи в файле .env")
        exit(1)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    start_handler = MessageHandler(filters.COMMAND & filters.Regex("^/start$"), start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(message_handler)

    print("Бот запущен...")
    application.run_polling()
