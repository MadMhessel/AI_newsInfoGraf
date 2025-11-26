import os
import logging
import tempfile
from typing import Tuple

import google.generativeai as genai
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TEXT_MODEL_NAME = os.getenv("TEXT_MODEL_NAME", "gemini-3.0-pro")
IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL_NAME", "imagen-3.0-generate-001")

# Инструкция для Gemini: ИИ принимает решения, код лишь проводник
SYSTEM_INSTRUCTION = (
    "You are an autonomous infographic art director. "
    "Analyse the provided news in Russian or English, decide on the best visual metaphor, "
    "and produce a single, concise English prompt for an elegant, minimalist infographic. "
    "Use only visuals (icons, charts, maps, timelines, silhouettes). Do not put any text into the image. "
    "Return only the final prompt; do not explain the reasoning."
)


def configure_genai() -> None:
    if not GOOGLE_API_KEY:
        raise RuntimeError("Не найден GOOGLE_API_KEY в переменных окружения")

    genai.configure(api_key=GOOGLE_API_KEY)
    logging.info(
        "GenAI настроен. Текстовая модель: %s, модель изображений: %s",
        TEXT_MODEL_NAME,
        IMAGE_MODEL_NAME,
    )


async def generate_ai_content(user_text: str) -> Tuple[object, str]:
    """Полностью доверяем выбору ИИ: анализ новости -> промпт -> изображение."""

    text_model = genai.GenerativeModel(TEXT_MODEL_NAME)

    logging.info("Отправка текста новости в Gemini для генерации промпта инфографики")
    prompt_response = text_model.generate_content(
        [
            {"role": "system", "parts": [SYSTEM_INSTRUCTION]},
            {"role": "user", "parts": [f"News text: {user_text}"]},
        ],
        generation_config={"temperature": 0.9, "top_p": 0.95},
    )

    image_prompt = (prompt_response.text or "").strip()
    if not image_prompt:
        raise RuntimeError("Gemini не вернул промпт для изображения")

    logging.info("Промпт для изображения: %s", image_prompt)

    image_model = genai.ImageGenerationModel(IMAGE_MODEL_NAME)

    logging.info("Запрос Imagen на генерацию финальной инфографики")
    images = image_model.generate_images(
        prompt=image_prompt,
        number_of_images=1,
        aspect_ratio="3:4",
        safety_filter="block_only_high",
    )

    return images[0], image_prompt


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    if not user_text:
        return

    status_message = await update.message.reply_text(
        "🧠 ИИ анализирует новость и придумывает инфографику..."
    )

    try:
        image_result, used_prompt = await generate_ai_content(user_text)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            image_path = temp_file.name
            image_result.save(image_path)

        await status_message.edit_text("🎨 Рисую изображение...")

        with open(image_path, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=(
                    "📊 **Инфографика готова!**\n\n"
                    "_ИИ решил визуализировать это так:_\n"
                    f"{used_prompt}"
                ),
                parse_mode="Markdown",
            )

        await status_message.delete()
    except Exception as e:
        logging.exception("Сбой при генерации инфографики")
        error_msg = f"Произошла ошибка при генерации: {str(e)}"
        if "400" in str(e):
            error_msg += (
                "\n\nВозможно, вашему ключу не доступна Imagen 3. "
                "Проверьте тариф или замените IMAGE_MODEL_NAME в .env."
            )
        await status_message.edit_text(error_msg)
    finally:
        # Удаляем временный файл, если он создавался
        try:
            if "image_path" in locals() and os.path.exists(image_path):
                os.remove(image_path)
        except OSError:
            logging.warning("Не удалось удалить временный файл %s", image_path)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот-генератор инфографики.\n"
        "Отправь мне текст новости, и Gemini 3 Pro сам решит, как её визуализировать."
    )


def main():
    configure_genai()

    if not TELEGRAM_TOKEN:
        raise RuntimeError("Не найден TELEGRAM_TOKEN в переменных окружения")

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    start_handler = MessageHandler(filters.COMMAND & filters.Regex("^/start$"), start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(message_handler)

    print("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()
