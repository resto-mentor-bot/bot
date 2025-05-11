# flake8: noqa

import json
import logging
import random
import re
import asyncio

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    Message,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Импорт собственных модулей
from assistance_create import *
from db_func import *

import openai
from openai import AsyncOpenAI

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации (токен бота и ключ OpenAI)
with open("../config/config.json", "r", encoding="utf-8") as file:
    config = json.load(file)
    TOKEN = config["BOT_TOKEN"]
    OPENAI_API_KEY = config["OPENAI_API_KEY"]

openai.api_key = OPENAI_API_KEY
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# =============================================================================
# Вспомогательные функции
# =============================================================================
def clean_chatgpt_response(response: str) -> str:
    """
    Очищает ответ ChatGPT от нежелательных шаблонов.
    """
    cleaned_response = re.sub(r"【\d+(?::\d+)?†source】", "", response)
    return cleaned_response.strip()


def parse_value(val: str) -> str:
    """
    Если значение равно "NULL", возвращает строку 'Отсутствуют'.
    """
    return val if val != "NULL" else "Отсутствуют"


def add_to_history(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, role: str, content: str
) -> None:
    """
    Добавляет новое сообщение в историю диалога.
    Ограничивает историю 10 последними сообщениями.
    """
    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []
    context.user_data["conversation_history"].append({"role": role, "content": content})
    if len(context.user_data["conversation_history"]) > 10:
        context.user_data["conversation_history"] = context.user_data[
            "conversation_history"
        ][-10:]


# =============================================================================
# Функции для взаимодействия с OpenAI
# =============================================================================
async def process_openai_general_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_prompt: str,
    waiting_message: Message,
) -> None:
    """
    Обработка запроса к OpenAI для общего диалога.
    """
    try:
        thread = await client.beta.threads.create(
            messages=[{"role": "user", "content": user_prompt}]
        )
        run = await client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id="asst_35v1pLP2iy1MCdxvAZbPDviU"
        )
        messages = list(
            await client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id)
        )
        if messages:
            _, messages_list = messages[0]
            message = messages_list[0]
            text_content = message.content[0].text.value
            message_content = clean_chatgpt_response(text_content)
            add_to_history(
                context, update.effective_user.id, "assistant", message_content
            )
            keyboard = [
                [
                    InlineKeyboardButton(
                        "⏹ Прекратить общение", callback_data="stop_chat"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await waiting_message.edit_text(
                f"💬 {message_content}",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
        else:
            await waiting_message.edit_text(
                "К сожалению, я не смог проверить ваш ответ. Попробуйте снова."
            )
    except Exception as e:
        logger.exception("Ошибка при обработке общего запроса к OpenAI:")
        await waiting_message.edit_text(f"❌ Ошибка: {e}")


async def process_openai_answer_for_test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_prompt: str,
    waiting_message: Message,
    test: dict,
    next_question_func,
) -> None:
    """
    Обработка запроса к OpenAI для тестирования.
    """
    try:
        thread = await client.beta.threads.create(
            messages=[{"role": "user", "content": user_prompt}]
        )
        run = await client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id="asst_35v1pLP2iy1MCdxvAZbPDviU"
        )
        messages = list(
            await client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id)
        )
        if messages:
            _, messages_list = messages[0]
            message = messages_list[0]
            text_content = message.content[0].text.value
            assistant_response = clean_chatgpt_response(text_content)
            await waiting_message.edit_text(
                f"💬 {assistant_response}", parse_mode="Markdown"
            )
            if (
                "правильно" in assistant_response.lower()
                and "неправильно" not in assistant_response.lower()
            ):
                test["score"] += 1
            test["current_index"] += 1
            await next_question_func(update, context)
        else:
            await waiting_message.edit_text(
                "К сожалению, я не смог проверить ваш ответ. Попробуйте снова."
            )
    except Exception as e:
        logger.exception("Ошибка при тестировании через OpenAI:")
        await waiting_message.edit_text(f"❌ Ошибка: {e}")


async def process_openai_answer_for_composition(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_prompt: str,
    waiting_message: Message,
    dish_data,
) -> None:
    """
    Обработка запроса к OpenAI для проверки состава блюда.
    """
    try:
        thread = await client.beta.threads.create(
            messages=[{"role": "user", "content": user_prompt}]
        )
        run = await client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id="asst_35v1pLP2iy1MCdxvAZbPDviU"
        )
        messages = list(
            await client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id)
        )
        if messages:
            _, messages_list = messages[0]
            message = messages_list[0]
            text_content = message.content[0].text.value
            assistant_response = clean_chatgpt_response(text_content)
            category_callback = f"test_compositions_{dish_data[2]}"
            keyboard = [
                [InlineKeyboardButton("🔙 Завершить", callback_data=category_callback)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await waiting_message.edit_text(
                f"💬 {assistant_response}",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
            context.user_data.pop("test_dish", None)
            context.user_data.pop("test_composition_in_progress", None)
        else:
            await waiting_message.edit_text(
                "К сожалению, я не смог проверить ваш ответ. Попробуйте снова."
            )
    except Exception as e:
        logger.exception("Ошибка при проверке состава блюда через OpenAI:")
        await waiting_message.edit_text(f"❌ Ошибка: {e}")


async def process_openai_answer_for_entity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_prompt: str,
    waiting_message: Message,
    entity_data,
    entity_type: str,
    entity_key: str,
) -> None:
    """
    Обработка запроса к OpenAI для вопросов по блюдам или напиткам.
    """
    try:
        thread = await client.beta.threads.create(
            messages=[{"role": "user", "content": user_prompt}]
        )
        run = await client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id="asst_35v1pLP2iy1MCdxvAZbPDviU"
        )
        messages = list(
            await client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id)
        )
        if messages:
            _, messages_list = messages[0]
            message = messages_list[0]
            text_content = message.content[0].text.value
            assistant_response = clean_chatgpt_response(text_content)
            response_text = (
                f"{assistant_response}\n\n"
                "Вы можете задать следующий вопрос или нажать кнопку *Завершить вопросы*."
            )
            add_to_history(
                context, update.effective_user.id, "assistant", assistant_response
            )
            if "order" in entity_key:
                callback_data = (
                    f"order_dish_{entity_data[0]}"
                    if "dish" in entity_key
                    else f"order_drink_{entity_data[0]}"
                )
            else:
                callback_data = (
                    f"category_{entity_data[2]}"
                    if "dish" in entity_key
                    else f"back_drink_{entity_data[2]}_{entity_data[-1]}"
                )
            keyboard = [
                [InlineKeyboardButton("Завершить вопросы", callback_data=callback_data)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await waiting_message.edit_text(
                response_text, parse_mode="Markdown", reply_markup=reply_markup
            )
        else:
            await waiting_message.edit_text("К сожалению, я не смог получить ответ.")
    except Exception as e:
        logger.exception("Ошибка при запросе по сущности:")
        await waiting_message.edit_text(f"❌ Произошла ошибка: {e}")


# =============================================================================
# Функции тестирования
# =============================================================================
async def handle_test_general(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Запускает общий тест, объединяя вопросы по работе, меню и напиткам.
    """
    work_q = await get_random_work_features_general(3)
    menu_q = await get_random_menu_questions_general(6)
    drink_q = await get_random_drink_questions_general(6)
    all_questions = work_q + menu_q + drink_q
    random.shuffle(all_questions)
    context.user_data["test_general"] = {
        "questions": all_questions,
        "current_index": 0,
        "score": 0,
    }
    context.user_data["test_general_in_progress"] = True
    await send_next_general_question(query, context)


async def send_next_general_question(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет следующий вопрос общего теста.
    """
    test = context.user_data.get("test_general")
    if not test or test["current_index"] >= len(test["questions"]):
        score = test["score"]
        total = len(test["questions"])
        context.user_data.pop("test_general_in_progress", None)
        context.user_data.pop("test_general", None)
        await query.message.reply_text(
            f"🎉 Общий тест завершён! Вы набрали *{score}/{total}* баллов.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Назад", callback_data="test")]]
            ),
        )
        return
    current_question = test["questions"][test["current_index"]]
    context.user_data["current_general_question"] = current_question
    await query.message.reply_text(
        f"❓ Вопрос {test['current_index'] + 1}:\n{current_question['question']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Завершить тест", callback_data="cancel_test")]]
        ),
    )


async def handle_general_test_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработка ответа пользователя в общем тесте.
    """
    user_message = update.message.text.strip()
    test = context.user_data.get("test_general")
    current_question = context.user_data.get("current_general_question")
    if not test or not current_question:
        await update.message.reply_text("❌ Тестирование неактивно.")
        return
    user_prompt = (
        "Ты — мой дружелюбный наставник. Оцени мой ответ максимально лояльно, "
        "с учетом смысла и ключевых слов, а не точного совпадения текста.\n\n"
        f"📌 Вопрос: {current_question['question']}\n"
        f"✍️ Мой ответ: {user_message}\n"
        f"✅ Верный ответ: {current_question['answer']}\n"
        f"💡 Дополнительное пояснение: {current_question['explanation']}\n\n"
        "Как оценивать:\n"
        "- Если ответ близок по смыслу к верному — напиши 'правильно', но всегда рассказывай полный вариант ответа с пояснением\n"
        "- Если ответ неверный — напиши 'неправильно' с комментариями\n"
    )
    waiting_message = await update.message.reply_text(
        "⏳ Проверяю ваш ответ, подождите..."
    )
    asyncio.create_task(
        process_openai_answer_for_test(
            update,
            context,
            user_prompt,
            waiting_message,
            test,
            send_next_general_question,
        )
    )


async def handle_test_drinks(query) -> None:
    """
    Меню выбора категории для тестирования по напиткам.
    """
    keyboard = [
        [InlineKeyboardButton("🍷 Красные вина", callback_data="test_drink_red")],
        [InlineKeyboardButton("🍾 Белые вина", callback_data="test_drink_white")],
        [InlineKeyboardButton("🥂 Остальные вина", callback_data="test_drink_wine")],
        [InlineKeyboardButton("🍹 Другие напитки", callback_data="test_drink_other")],
        [InlineKeyboardButton("🔙 Назад", callback_data="test")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите категорию напитков для тестирования:", reply_markup=reply_markup
    )


async def handle_test_drink_category(
    query, category: str, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработка выбора категории напитков для тестирования.
    """
    category_map = {
        "red": "Красные вина",
        "white": "Белые вина",
        "wine": "Остальные вина",
        "other": "Другие напитки",
    }
    category_name = category_map.get(category, category)
    questions = await get_random_drink_questions(category_name)
    if not questions:
        await query.message.reply_text("❌ В этой категории пока нет вопросов.")
        return
    context.user_data["test_drinks"] = {
        "questions": questions,
        "current_index": 0,
        "score": 0,
    }
    context.user_data["test_drinks_in_progress"] = True
    await send_next_drink_question(query, context)


async def send_next_drink_question(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправка следующего вопроса теста по напиткам.
    """
    test = context.user_data.get("test_drinks")
    if not test or test["current_index"] >= len(test["questions"]):
        score = test["score"]
        total = len(test["questions"])
        context.user_data.pop("test_drinks_in_progress", None)
        context.user_data.pop("test_drinks", None)
        await query.message.reply_text(
            f"🎉 Тест по напиткам завершён! Вы набрали *{score}/{total}* баллов.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Назад", callback_data="test")]]
            ),
        )
        return
    current_question = test["questions"][test["current_index"]]
    context.user_data["current_drink_question"] = current_question
    await query.message.reply_text(
        f"❓ Вопрос {test['current_index'] + 1}:\n{current_question['question']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Завершить тест", callback_data="cancel_test")]]
        ),
    )


async def handle_drink_test_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработка ответа пользователя в тесте по напиткам.
    """
    user_message = update.message.text.strip()
    test = context.user_data.get("test_drinks")
    current_question = context.user_data.get("current_drink_question")
    if not test or not current_question:
        await update.message.reply_text("❌ Тестирование неактивно.")
        return
    user_prompt = (
        f"Ты — мой дружелюбный наставник, помогающий разбираться в напитках ресторана Хачапури и Вино. "
        f"Оцени мой ответ **максимально лояльно**, учитывая **смысл** и **ключевые слова**, а не точное совпадение текста.\n\n"
        f"📌 Вопрос: {current_question['question']}\n"
        f"✍️ Мой ответ: {user_message}\n"
        f"✅ Верный ответ: {current_question['answer']}\n"
        f"💡 Дополнительное пояснение: {current_question['explanation']}\n\n"
        f"🤖 Как оценивать:\n"
        f"- Если ответ **близок по смыслу** к верному — засчитывай **✅ Правильно!**\n"
        f"- Если ответ **верный, но содержит лишние детали** — тоже **✅ Правильно!**, просто уточни, что можно сказать короче\n"
        f"- Если ответ **ошибочный**, мягко объясни, что исправить, и напиши **❌ Пока неправильно**\n"
        f"- Если ответ верный, но можно дополнить, используй пояснение как дополнительный факт\n"
    )
    waiting_message = await update.message.reply_text(
        "⏳ Проверяю ваш ответ, подождите..."
    )
    asyncio.create_task(
        process_openai_answer_for_test(
            update,
            context,
            user_prompt,
            waiting_message,
            test,
            send_next_drink_question,
        )
    )


async def handle_work_features_test(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработка теста по особенностям работы (например, для официантов).
    """
    questions = await get_random_questions()  # Функция из db_func
    context.user_data["current_test"] = {
        "questions": questions,
        "current_index": 0,
        "score": 0,
    }
    context.user_data["test_in_progress"] = True
    await send_next_question(query, context)


async def send_next_question(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправка следующего вопроса теста по особенностям работы.
    """
    test = context.user_data.get("current_test")
    if not test or test["current_index"] >= len(test["questions"]):
        score = test["score"]
        total = len(test["questions"])
        for key in ["test_in_progress", "current_test", "current_question"]:
            context.user_data.pop(key, None)
        await query.message.reply_text(
            f"🎉 Тест завершён! Вы набрали *{score}/{total}* баллов.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Назад", callback_data="test")]]
            ),
        )
        return
    current_question = test["questions"][test["current_index"]]
    context.user_data["current_question"] = current_question
    await query.message.reply_text(
        f"❓ Вопрос {test['current_index'] + 1}:\n{current_question['question']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Завершить тест", callback_data="cancel_test")]]
        ),
    )


async def handle_cancel_test(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработка нажатия кнопки "Завершить тест" – сброс временных данных тестирования.
    """
    keys_to_remove = [
        "test_in_progress",
        "current_test",
        "current_question",
        "test_menu_in_progress",
        "test_drinks_in_progress",
        "test_general_in_progress",
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    await query.message.reply_text(
        "Вы завершили тест досрочно. Вы можете вернуться в раздел тестирования.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Вернуться", callback_data="test")]]
        ),
    )


async def handle_work_features_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработка ответа пользователя в тесте по особенностям работы.
    """
    user_message = update.message.text.strip()
    test = context.user_data.get("current_test")
    current_question = context.user_data.get("current_question")
    if not test or not current_question:
        await update.message.reply_text("Тестирование неактивно.")
        return
    user_prompt = (
        f"Ты — мой дружелюбный наставник, помогающий разбираться в работе официанта ресторана Хачапури и Вино. "
        f"Оцени мой ответ **максимально лояльно**, учитывая **смысл** и **ключевые слова**, а не точное совпадение текста.\n\n"
        f"📌 Вопрос: {current_question['question']}\n"
        f"✍️ Мой ответ: {user_message}\n"
        f"✅ Верный ответ: {current_question['correct_answer']}\n"
        f"💡 Дополнительное пояснение: {current_question['explanation']}\n\n"
        f"🤖 Как оценивать:\n"
        f"- Если ответ **близок по смыслу** к верному — засчитывай **✅ Правильно!**\n"
        f"- Если ответ **верный, но содержит лишние детали** — тоже **✅ Правильно!**, просто уточни, что можно сказать короче\n"
        f"- Если ответ **ошибочный**, мягко объясни, что исправить, и напиши **❌ Пока неправильно**\n"
        f"- Если ответ верный, но можно дополнить, используй пояснение как дополнительный факт\n"
    )
    waiting_message = await update.message.reply_text(
        "⏳ Проверяю ваш ответ, подождите..."
    )
    asyncio.create_task(
        process_openai_answer_for_test(
            update, context, user_prompt, waiting_message, test, send_next_question
        )
    )


async def handle_test_full_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Запуск теста по всему меню (блюдам).
    """
    questions = await get_random_menu_questions()  # Функция из db_func
    context.user_data["test_menu"] = {
        "questions": questions,
        "current_index": 0,
        "score": 0,
    }
    context.user_data["test_menu_in_progress"] = True
    await send_next_menu_question(query, context)


async def send_next_menu_question(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправка следующего вопроса теста по меню.
    """
    test = context.user_data.get("test_menu")
    if not test or test["current_index"] >= len(test["questions"]):
        score = test["score"]
        total = len(test["questions"])
        context.user_data.pop("test_menu_in_progress", None)
        context.user_data.pop("test_menu", None)
        await query.message.reply_text(
            f"🎉 Тест завершён! Вы набрали *{score}/{total}* баллов.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Назад", callback_data="test")]]
            ),
        )
        return
    current_question = test["questions"][test["current_index"]]
    context.user_data["current_menu_question"] = current_question
    await query.message.reply_text(
        f"❓ Вопрос {test['current_index'] + 1}: {current_question['question']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Завершить тест", callback_data="cancel_test")]]
        ),
    )


async def handle_menu_test_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработка ответа пользователя в тесте по меню.
    """
    user_message = update.message.text.strip()
    test = context.user_data.get("test_menu")
    current_question = context.user_data.get("current_menu_question")
    if not test or not current_question:
        await update.message.reply_text("Тестирование неактивно.")
        return
    user_prompt = (
        f"Ты — мой дружелюбный наставник, помогающий разбираться в меню ресторана Хачапури и Вино. "
        f"Оцени мой ответ **максимально лояльно**, учитывая **смысл** и **ключевые слова**, а не точное совпадение текста.\n\n"
        f"📌 Вопрос: {current_question['question']}\n"
        f"✍️ Мой ответ: {user_message}\n"
        f"✅ Верный ответ: {current_question['answer']}\n"
        f"💡 Дополнительное пояснение (Эту часть знаешь ты - она создана для твоего понимания): {current_question['explanation']}\n\n"
        f"🤖 Как оценивать:\n"
        f"- Если ответ **близок по смыслу** к верному — засчитывай **✅ Правильно!**\n"
        f"- Если ответ **верный, но содержит лишние детали** — тоже **✅ Правильно!**, просто уточни, что можно сказать короче\n"
        f"- Если ответ **ошибочный**, мягко объясни, что исправить, и напиши **❌ Пока неправильно**\n"
        f"- Если ответ верный, но можно дополнить, используй пояснение как дополнительный факт\n"
    )
    waiting_message = await update.message.reply_text(
        "⏳ Проверяю ваш ответ, подождите..."
    )
    asyncio.create_task(
        process_openai_answer_for_test(
            update, context, user_prompt, waiting_message, test, send_next_menu_question
        )
    )


async def handle_test_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Главное меню тестирования – выбор раздела (основное меню, напитки, особенности работы, общий тест).
    """
    keyboard = [
        [InlineKeyboardButton("Основное меню", callback_data="test_main_menu")],
        [InlineKeyboardButton("Напитки", callback_data="test_drinks")],
        [InlineKeyboardButton("Назад", callback_data="welcome")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите раздел для тестирования:", reply_markup=reply_markup
    )


async def handle_test_main_menu(query) -> None:
    """
    Меню выбора типа тестирования для основного меню.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "Тестирование по составам", callback_data="test_compositions"
            )
        ],
        [
            InlineKeyboardButton(
                "Тестирование по всему меню", callback_data="test_full_menu"
            )
        ],
        [InlineKeyboardButton("Назад", callback_data="test")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите тип тестирования для основного меню:", reply_markup=reply_markup
    )


async def handle_test_compositions(query) -> None:
    """
    Обработка тестирования "по составам" – вывод категорий.
    """
    categories = await get_categories()
    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"test_compositions_{category}")]
        for category in categories
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="test_main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📋 Выберите категорию для тестирования по составам:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def handle_test_compositions_category(query, category_name: str) -> None:
    """
    Обработка выбора категории для тестирования по составам.
    """
    dishes = await get_dishes_by_category(category_name)
    if not dishes:
        await query.edit_message_text(
            f"🚫 В категории *{category_name}* нет доступных блюд.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Назад", callback_data="test_compositions")]]
            ),
        )
        return
    keyboard = [
        [
            InlineKeyboardButton(
                dish["name"], callback_data=f"test_composition_dish_{dish['id']}"
            )
        ]
        for dish in dishes
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="test_compositions")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"📋 Выберите блюдо из категории *{category_name}* для проверки состава:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def handle_test_composition_dish(
    query, dish_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработка выбора конкретного блюда для теста по составу.
    """
    dish_data = await get_dish_ingredients(dish_id)
    d2 = await get_dish_by_id(dish_id)
    if not dish_data:
        await query.message.reply_text("❌ Данные о составе блюда не найдены.")
        return
    context.user_data["test_composition_in_progress"] = True
    context.user_data["test_dish"] = {
        "dish_id": dish_id,
        "dish_name": dish_data["name"],
        "correct_ingredients": dish_data["ingredients"],
    }
    await query.message.reply_text(
        f"📋 Назовите полный состав блюда *{dish_data['name']}*.\n"
        "Перечислите все ингредиенты через запятую.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Назад", callback_data=f"test_compositions_{d2[2]}"
                    )
                ]
            ]
        ),
    )


async def handle_test_composition_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Обработка ответа пользователя в тесте по составу блюда.
    """
    user_message = update.message.text.strip().lower()
    test_dish = context.user_data.get("test_dish")
    if not test_dish:
        await update.message.reply_text(
            "❌ Тестирование неактивно. Выберите блюдо заново."
        )
        return
    dish_id = test_dish["dish_id"]
    dish_data = await get_dish_by_id(dish_id)
    user_prompt = (
        f"Блюдо: {test_dish['dish_name']}\n"
        f"Ответ пользователя: {user_message}\n"
        f"Эталонный состав: {test_dish['correct_ingredients'].lower()}\n\n"
        f"Проанализируй ответ пользователя. Если есть ошибки, укажи, какие ингредиенты лишние (если такие есть), "
        f"и какие отсутствуют (если пользователь не назвал их). "
        f"Обратись к пользователю дружелюбно, избегая формальностей. Вердикт: 'правильно' или 'неправильно'."
    )
    waiting_message = await update.message.reply_text(
        "⏳ Проверяю ваш ответ, подождите..."
    )
    asyncio.create_task(
        process_openai_answer_for_composition(
            update, context, user_prompt, waiting_message, dish_data
        )
    )


# =============================================================================
# Функции отображения карточек блюд и напитков
# =============================================================================
async def send_dish_card(query, dish_data) -> None:
    """
    Отправка карточки блюда с описанием, списком ингредиентов и дополнительной информацией.
    """
    if dish_data:
        (
            id,
            name,
            category,
            description,
            photo_url,
            features,
            ingredients,
            details,
            allergens,
            veg,
        ) = dish_data
        message = f"🍴 *{name}*\n"
        message += f"📂 Категория: {category}\n\n"
        if description:
            message += f"📖 *Описание:*\n{parse_value(description)}\n\n"
        if features:
            message += f"⭐ *Особенности:*\n{parse_value(features)}\n\n"
        if ingredients:
            message += f"📝 *Ингредиенты:*\n{parse_value(ingredients)}\n\n"
        if allergens:
            message += f"⚠️ *Аллергены:*\n{parse_value(allergens)}\n\n"
        if veg:
            message += f"🌱 *Подходит вегетарианцам/веганам:* {parse_value(veg)}\n\n"
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data="main_menu")],
            [
                InlineKeyboardButton(
                    "Задать вопрос по этому блюду",
                    callback_data=f"ask_dish_{dish_data[0]}",
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if photo_url:
            try:
                await query.message.reply_photo(
                    photo=photo_url,
                    caption=message,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
            except Exception as e:
                message += "\n🌐 Фото временно недоступно."
                await query.message.reply_text(
                    message, parse_mode="Markdown", reply_markup=reply_markup
                )
        else:
            await query.message.reply_text(
                message, parse_mode="Markdown", reply_markup=reply_markup
            )
    else:
        await query.message.reply_text("Данные о выбранном блюде не найдены.")


async def send_drink_card(query, drink_data) -> None:
    """
    Отправка карточки напитка с описанием, составом, ароматическим и вкусовым профилем.
    """
    if drink_data:
        (
            id,
            name,
            category,
            description,
            photo_url,
            notes,
            ingredients,
            aroma_profile,
            taste_profile,
            sugar_content,
            producer,
            gastropair,
            subcategory,
        ) = drink_data
        message = f"🍷 *{name}*\n"
        message += f"📂 Категория: {category}\n"
        if subcategory:
            message += f"🧾 Подкатегория: {subcategory}\n\n"
        if description:
            message += f"📖 *Описание:*\n{description}\n\n"
        if ingredients:
            message += f"📝 *Ингредиенты:*\n{ingredients}\n\n"
        if aroma_profile:
            message += f"👃 *Ароматический профиль:*\n{aroma_profile}\n\n"
        if taste_profile:
            message += f"👅 *Вкусовой профиль:*\n{taste_profile}\n\n"
        if sugar_content:
            message += f"🍬 *Стиль напитка:*\n{sugar_content}\n\n"
        if producer:
            message += f"🏭 *Производитель:*\n{producer}\n\n"
        if gastropair:
            message += f"🍽 *Гастропара:*\n{gastropair}\n\n"
        if notes:
            message += f"📝 *Примечания:*\n{notes}\n\n"
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data="drinks")],
            [
                InlineKeyboardButton(
                    "Задать вопрос по этому напитку",
                    callback_data=f"ask_drink_{drink_data[0]}",
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if photo_url:
            try:
                await query.message.reply_photo(
                    photo=photo_url,
                    caption=message,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
            except Exception as e:
                message += "\n🌐 Фото временно недоступно."
                await query.message.reply_text(
                    message, parse_mode="Markdown", reply_markup=reply_markup
                )
        else:
            await query.message.reply_text(
                message, parse_mode="Markdown", reply_markup=reply_markup
            )
    else:
        await query.message.reply_text("Данные о выбранном напитке не найдены.")


# =============================================================================
# Функции оформления заказа
# =============================================================================
async def handle_main_menu(query) -> None:
    """
    Отображает основное меню с выбором категорий блюд.
    """
    categories = await get_categories()
    keyboard = [
        [InlineKeyboardButton(category, callback_data=category)]
        for category in categories
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="welcome")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.message.text:
        await query.edit_message_text(
            "Выберите раздел основного меню:", reply_markup=reply_markup
        )
    else:
        await query.message.reply_text(
            "Выберите раздел основного меню:", reply_markup=reply_markup
        )


async def handle_take_order(query) -> None:
    """
    Меню выбора категории для оформления заказа.
    """
    keyboard = [
        [InlineKeyboardButton("Еда", callback_data="order_food")],
        [InlineKeyboardButton("Напитки", callback_data="order_drinks")],
        [InlineKeyboardButton("Назад", callback_data="welcome")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите категорию заказа:", reply_markup=reply_markup
    )


async def handle_order_food(query) -> None:
    """
    Обработка выбора еды – вывод категорий блюд.
    """
    categories = await get_categories()
    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"order_category_{category}")]
        for category in categories
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="take_order")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    current_text = query.message.text if query.message.text else ""
    new_text = "Выберите категорию еды:"
    if current_text != new_text or query.message.reply_markup != reply_markup:
        await query.edit_message_text(new_text, reply_markup=reply_markup)
    else:
        logger.info("Сообщение не изменено. Запрос на редактирование пропущен.")


async def handle_order_drinks(query) -> None:
    """
    Обработка выбора напитков – вывод категорий напитков.
    """
    categories = await get_drink_categories()
    keyboard = [
        [
            InlineKeyboardButton(
                category, callback_data=f"drink_order_category_{category}"
            )
        ]
        for category in categories
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="take_order")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите категорию напитков:", reply_markup=reply_markup
    )


async def handle_drink_order_category(query, category_name: str) -> None:
    """
    Обработка выбора подкатегории напитков в выбранной категории.
    """
    subcategories = await get_subcategories_by_category(category_name)
    keyboard = [
        [
            InlineKeyboardButton(
                subcategory, callback_data=f"drk_ord_sub_{category_name}_{subcategory}"
            )
        ]
        for subcategory in subcategories
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="order_drinks")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Выберите подкатегорию из категории *{category_name}*:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def handle_drink_order_subcategory(
    query, category_name: str, subcategory_name: str
) -> None:
    """
    Отображает напитки в выбранной подкатегории.
    """
    drinks = await get_drinks_by_subcategory(category_name, subcategory_name)
    keyboard = [
        [
            InlineKeyboardButton(
                drink["name"], callback_data=f"order_drink_{drink['id']}"
            )
        ]
        for drink in drinks
    ]
    keyboard.append(
        [
            InlineKeyboardButton(
                "Назад", callback_data=f"drink_order_category_{category_name}"
            )
        ]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.message.text:
        await query.edit_message_text(
            f"Напитки в подкатегории *{subcategory_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        await query.message.reply_text(
            f"Напитки в подкатегории *{subcategory_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def handle_order_drink(query, drink_id: int) -> None:
    """
    Обработка выбора конкретного напитка – вывод карточки напитка.
    """
    drink_data = await get_drink_by_id(drink_id)
    if drink_data:
        await send_drink_card(query, drink_data)
    else:
        await query.message.reply_text("Данные о выбранном напитке не найдены.")


async def handle_drink_ok(
    query, drink_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Подтверждение выбора напитка и запрос количества.
    """
    drink_data = await get_drink_by_id(drink_id)
    if not drink_data:
        await query.message.reply_text("Информация о выбранном напитке недоступна.")
        return
    context.user_data["current_drink"] = drink_data
    await query.message.reply_text(
        f"Вы выбрали *{drink_data[1]}*.\n\nВведите количество порций этого напитка:",
        parse_mode="Markdown",
    )


async def handle_order_category(query, category_name: str) -> None:
    """
    Отображает блюда выбранной категории для оформления заказа.
    """
    dishes = await get_dishes_by_category(category_name)
    buttons = [
        [InlineKeyboardButton(dish["name"], callback_data=f"order_dish_{dish['id']}")]
        for dish in dishes
    ]
    buttons.append([InlineKeyboardButton("Назад", callback_data=f"order_food")])
    reply_markup = InlineKeyboardMarkup(buttons)
    try:
        if query.message.text:
            await query.edit_message_text(
                f"Выберите блюдо из категории *{category_name}*:",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
        else:
            await query.message.reply_text(
                f"Выберите блюдо из категории *{category_name}*:",
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
    except Exception as e:
        await query.message.reply_text(
            "Произошла ошибка при обработке вашего запроса. Попробуйте снова."
        )


async def handle_order_dish(query, dish_id: int) -> None:
    """
    Обработка выбора конкретного блюда – вывод карточки блюда.
    """
    dish_data = await get_dish_by_id(dish_id)
    if dish_data:
        await send_dish_card(query, dish_data)
    else:
        await query.message.reply_text("Данные о выбранном блюде не найдены.")


async def handle_dish_ok(
    query, dish_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Подтверждение выбора блюда и запрос количества.
    """
    dish_data = await get_dish_by_id(dish_id)
    if not dish_data:
        await query.message.reply_text("Информация о выбранном блюде недоступна.")
        return
    context.user_data["current_dish"] = dish_data
    await query.message.reply_text(
        f"Вы выбрали *{dish_data[1]}*.\n\nВведите количество этого блюда:",
        parse_mode="Markdown",
    )


async def handle_finish_order(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Завершает оформление заказа – вывод итогового заказа.
    """
    order = context.user_data.get("order", [])
    if not order:
        await query.message.reply_text(
            "Ваш заказ пуст. Пожалуйста, выберите блюда или напитки, прежде чем завершить заказ.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Вернуться к выбору еды", callback_data="order_food"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Вернуться к выбору напитков", callback_data="order_drinks"
                        )
                    ],
                    [InlineKeyboardButton("Главное меню", callback_data="welcome")],
                ]
            ),
        )
        return
    message = "📝 *Ваш заказ:*\n\n"
    for item in order:
        if "dish" in item:
            dish_name = item["dish"][1]
            quantity = item["quantity"]
            if item["comment"] is not None:
                comment = item["comment"]
                message += (
                    f"🍽 *{dish_name}* x{quantity}\n  📋 Комментарий: {comment}\n\n"
                )
            else:
                message += f"🍽 *{dish_name}* x{quantity}\n\n"
        elif "drink" in item:
            drink_name = item["drink"][1]
            quantity = item["quantity"]
            if item["comment"] is not None:
                comment = item["comment"]
                message += (
                    f"🍷 *{drink_name}* x{quantity}\n  📋 Комментарий: {comment}\n\n"
                )
            else:
                message += f"🍷 *{drink_name}* x{quantity}\n\n"
    context.user_data.pop("order", None)
    await query.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Вернуться в главное меню", callback_data="welcome"
                    )
                ]
            ]
        ),
    )


async def handle_drinks_menu(query) -> None:
    """
    Отображает меню категорий напитков.
    """
    categories = await get_drink_categories()
    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"drink_category_{category}")]
        for category in categories
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="welcome")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.message.text:
        await query.edit_message_text(
            "Выберите категорию напитков:", reply_markup=reply_markup
        )
    else:
        await query.message.reply_text(
            "Выберите категорию напитков:", reply_markup=reply_markup
        )


async def handle_category(query, category_name: str) -> None:
    """
    Отображает блюда выбранной категории (для основного меню).
    """
    dishes = await get_dishes_by_category(category_name)
    buttons = [
        [InlineKeyboardButton(dish["name"], callback_data=f"dish_{dish['id']}")]
        for dish in dishes
    ]
    buttons.append([InlineKeyboardButton("Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(buttons)
    if query.message.text:
        await query.edit_message_text(
            f"Выберите блюдо из раздела *{category_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        await query.message.reply_text(
            f"Выберите блюдо из раздела *{category_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def handle_drink_category(query, category_name: str) -> None:
    """
    Отображает подкатегории напитков выбранной категории.
    """
    subcategories = await get_subcategories_by_category(category_name)
    if "Другое" in subcategories:
        subcategories.remove("Другое")
        subcategories.append("Другое")
    keyboard = [
        [
            InlineKeyboardButton(
                subcategory,
                callback_data=f"drink_subcategory_{category_name}_{subcategory}",
            )
        ]
        for subcategory in subcategories
    ]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="drinks")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.message.text:
        await query.edit_message_text(
            f"Выберите подкатегорию из категории *{category_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        await query.message.reply_text(
            f"Выберите подкатегорию из категории *{category_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def handle_drink_subcategory(
    query, category_name: str, subcategory_name: str
) -> None:
    """
    Отображает напитки в выбранной подкатегории.
    """
    drinks = await get_drinks_by_subcategory(category_name, subcategory_name)
    keyboard = [
        [InlineKeyboardButton(drink["name"], callback_data=f"get_drink_{drink['id']}")]
        for drink in drinks
    ]
    keyboard.append(
        [InlineKeyboardButton("Назад", callback_data=f"drink_category_{category_name}")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.message.text:
        await query.edit_message_text(
            f"Напитки в подкатегории *{subcategory_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    else:
        await query.message.reply_text(
            f"Напитки в подкатегории *{subcategory_name}*:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def handle_dish(query, dish_id: int) -> None:
    """
    Обработка выбора блюда – вывод карточки блюда.
    """
    dish_data = await get_dish_by_id(dish_id)
    if dish_data:
        await send_dish_card(query, dish_data)
    else:
        await query.message.reply_text(
            "Данные о выбранном блюде не найдены.", parse_mode="Markdown"
        )


async def handle_drink(query, drink_id: int) -> None:
    """
    Обработка выбора напитка – вывод карточки напитка.
    """
    drink_data = await get_drink_by_id(drink_id)
    if drink_data:
        await send_drink_card(query, drink_data)
    else:
        await query.message.reply_text(
            "Данные о выбранном напитке не найдены.", parse_mode="Markdown"
        )


# =============================================================================
# Функции для обработки вопросов по блюдам и напиткам
# =============================================================================
async def handle_entity_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    entity_key: str,
    entity_type: str,
) -> None:
    """
    Универсальная функция для обработки вопросов по блюдам и напиткам.
    """
    if entity_key not in context.user_data:
        await update.message.reply_text(
            f"❌ Вопрос по {entity_type} не найден. Выберите {entity_type} сначала."
        )
        return
    entity_data = context.user_data[entity_key]
    user_message = update.message.text.strip()
    user_prompt = (
        "Ты — эксперт по ресторанному делу и обслуживанию, наставник официанта-стажера. "
        "Твоя задача — помогать с вопросами официанта, связанными с меню (блюда, напитки), сервисом, работой официанта и всеми стандартами ресторана 'Хачапури и Вино'.\n\n"
        "📌 Ты должен использовать ТОЛЬКО информацию из подключённых файлов (меню, напитки, сервис). "
        "📌 Никогда не предлагай блюда и напитки, которых НЕТ в этих данных. "
        "📌 Если в вопросе просят рекомендацию, но нужного блюда или напитка нет, скажи, что такой позиции нет в меню, и предложи альтернативу ТОЛЬКО из доступных данных. "
        "📌 Если в файлах нет данных про заданный вопрос, придумай ответ самостоятельно, дополнительные гастропары можно придумывать самостоятельно, но используй блюда и напитки ТОЛЬКО из данных, "
        "📌 НЕ ПРИДУМЫВАЙ новых блюд, новых напитков, новых ингредиентов, новых рецептов. "
        "📌 Если пользователь спрашивает о блюде, которого нет в меню, просто сообщи об этом и не пытайся его описать.\n\n"
        f"🗣 Вопрос по {entity_type}: {entity_data}\n"
        f"Пользователь: {user_message}"
    )
    waiting_message = await update.message.reply_text(
        "⏳ Обработка запроса, пожалуйста, подождите..."
    )
    asyncio.create_task(
        process_openai_answer_for_entity(
            update,
            context,
            user_prompt,
            waiting_message,
            entity_data,
            entity_type,
            entity_key,
        )
    )


# =============================================================================
# Обработка общего диалога и приветствия
# =============================================================================
async def handle_welcome(query) -> None:
    """
    Отображает главное меню с выбором разделов.
    """
    keyboard = [
        [InlineKeyboardButton("Основное меню", callback_data="main_menu")],
        [InlineKeyboardButton("Напитки", callback_data="drinks")],
        [InlineKeyboardButton("Тестирование", callback_data="test")],
        [
            InlineKeyboardButton(
                "💬 Задать общий вопрос", callback_data="general_question"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query.message.text:
        await query.edit_message_text("Выберите раздел:", reply_markup=reply_markup)
    else:
        await query.message.reply_text("Выберите раздел:", reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Стартовая функция – сбрасывает временные данные и предлагает перейти в главное меню.
    """
    keys_to_remove = [
        "test_in_progress",
        "test_menu_in_progress",
        "test_composition_in_progress",
        "current_test",
        "test_drinks_in_progress",
        "test_general_in_progress",
        "current_question",
        "current_drink_question",
        "current_menu_question",
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    keyboard = [[InlineKeyboardButton("Начать", callback_data="welcome")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🍷 Добро пожаловать в Ментор бот! 🍴\n\n"
        "👉 Нажмите *Начать*, чтобы перейти к выбору раздела!",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


# =============================================================================
# Обработка нажатий кнопок (callback_query)
# =============================================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Универсальный обработчик callback_query.
    """
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "main_menu":
        await handle_main_menu(query)
    elif data == "work_features":
        keyboard = [
            [InlineKeyboardButton("Утренняя смена", callback_data="work_morning")],
            [InlineKeyboardButton("Дневная смена", callback_data="work_day")],
            [InlineKeyboardButton("Вечерняя смена", callback_data="work_evening")],
            [InlineKeyboardButton("Знакомство с ХиВом", callback_data="work_dating")],
            [InlineKeyboardButton("Основы основ", callback_data="work_base")],
            [InlineKeyboardButton("Работа с iiko", callback_data="work_iiko")],
            [InlineKeyboardButton("Работа на раздаче", callback_data="work_bring")],
            [InlineKeyboardButton("Шаги сервиса", callback_data="work_service")],
            [InlineKeyboardButton("Хост", callback_data="work_host")],
            [InlineKeyboardButton("Работа с доставкой", callback_data="work_delivery")],
            [InlineKeyboardButton("О производстве вина", callback_data="work_wine")],
            [InlineKeyboardButton("Работа с баром", callback_data="work_bar")],
            [InlineKeyboardButton("Особые случаи", callback_data="work_special")],
            [InlineKeyboardButton("Назад", callback_data="welcome")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "Выберите раздел, чтобы узнать подробности:", reply_markup=reply_markup
        )
    elif data == "work_morning":
        await handle_morning_shift(query)  # Функцию реализуйте самостоятельно
    elif data == "test":
        await handle_test_menu(query, context)
    elif data == "instruction":
        await handle_instruction(query)  # Функцию реализуйте самостоятельно
    elif data == "test_general":
        await handle_test_general(query, context)
    elif data == "test_drinks":
        await handle_test_drinks(query)
    elif data.startswith("test_drink_"):
        category = data.split("_")[2]
        await handle_test_drink_category(query, category, context)
    elif data == "test_main_menu":
        await handle_test_main_menu(query)
    elif data == "test_compositions":
        await handle_test_compositions(query)
    elif data.startswith("test_compositions_"):
        category_name = data.split("_", 2)[2]
        await handle_test_compositions_category(query, category_name)
    elif data.startswith("test_composition_dish_"):
        dish_id = int(data.split("_")[3])
        await handle_test_composition_dish(query, dish_id, context)
    elif data.startswith("test_full_menu"):
        await handle_test_full_menu(query, context)
    elif data == "test_work_features":
        await handle_work_features_test(query, context)
    elif data == "cancel_test":
        await handle_cancel_test(query, context)
    elif data == "work_day":
        await handle_day_shift(query)
    elif data == "work_evening":
        await handle_evening_shift(query)
    elif data == "work_iiko":
        await handle_iiko(query)
    elif data == "work_dating":
        await handle_dating(query)
    elif data == "work_service":
        await handle_service(query)
    elif data == "work_special":
        await handle_special(query)
    elif data == "work_base":
        await handle_base(query)
    elif data == "work_host":
        await handle_host(query)
    elif data == "work_wine":
        await handle_wine(query)
    elif data == "work_bar":
        await handle_bar(query)
    elif data == "work_delivery":
        await handle_delivery(query)
    elif data == "work_bring":
        await handle_bring(query)
    elif data in await get_categories():
        await handle_category(query, data)
    elif data == "take_order":
        await handle_take_order(query)
    elif data == "no_comment_dish":
        current_dish = context.user_data.pop("current_dish", None)
        current_quantity = context.user_data.pop("current_quantity", None)
        if current_dish and current_quantity:
            if "order" not in context.user_data:
                context.user_data["order"] = []
            context.user_data["order"].append(
                {"dish": current_dish, "quantity": current_quantity, "comment": None}
            )
            await query.message.reply_text(
                f"Блюдо *{current_dish[1]}* x{current_quantity} добавлено в заказ!\n"
                "Выберите следующее блюдо или завершите заказ.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Завершить заказ", callback_data="finish_order"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "Продолжить выбор", callback_data="take_order"
                            )
                        ],
                    ]
                ),
            )
        else:
            await query.message.reply_text(
                "Произошла ошибка: не удалось обработать заказ."
            )
    elif data == "no_comment_drink":
        current_drink = context.user_data.pop("current_drink", None)
        current_quantity = context.user_data.pop("current_quantity", None)
        if current_drink and current_quantity:
            if "order" not in context.user_data:
                context.user_data["order"] = []
            context.user_data["order"].append(
                {"drink": current_drink, "quantity": current_quantity, "comment": None}
            )
            await query.message.reply_text(
                f"Напиток *{current_drink[1]}* x{current_quantity} добавлен в заказ!\n"
                "Выберите следующий напиток или завершите заказ.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Завершить заказ", callback_data="finish_order"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "Продолжить выбор", callback_data="take_order"
                            )
                        ],
                    ]
                ),
            )
        else:
            await query.message.reply_text(
                "Произошла ошибка: не удалось обработать заказ."
            )
    elif data == "order_food":
        await handle_order_food(query)
    elif data.startswith("order_category_"):
        category_name = data.split("_")[2]
        await handle_order_category(query, category_name)
    elif data.startswith("order_dish_"):
        context.user_data.pop("awaiting_question_for_order_dish", None)
        dish_id = int(data.split("_")[2])
        await handle_order_dish(query, dish_id)
    elif data.startswith("ask_order_dish_"):
        dish_id = int(data.split("_")[3])
        dish_data = await get_dish_by_id(dish_id)
        await query.message.reply_text("Введите ваш вопрос по этому блюду:")
        context.user_data["awaiting_question_for_order_dish"] = dish_data
    elif data == "order_drinks":
        await handle_order_drinks(query)
    elif data.startswith("drink_order_category_"):
        category_name = data.split("_")[3]
        await handle_drink_order_category(query, category_name)
    elif data.startswith("drk_ord_sub_"):
        _, _, _, category_name, subcategory_name = data.split("_")
        await handle_drink_order_subcategory(query, category_name, subcategory_name)
    elif data.startswith("order_drink_"):
        context.user_data.pop("awaiting_question_for_order_drink", None)
        drink_id = int(data.split("_")[2])
        await handle_order_drink(query, drink_id)
    elif data.startswith("drink_ok_"):
        drink_id = int(data.split("_")[2])
        await handle_drink_ok(query, drink_id, context)
    elif data.startswith("ask_order_drink_"):
        drink_id = int(data.split("_")[3])
        drink_data = await get_drink_by_id(drink_id)
        await query.message.reply_text("Введите ваш вопрос по этому напитку:")
        context.user_data["awaiting_question_for_order_drink"] = drink_data
    elif data.startswith("dish_ok_"):
        dish_id = int(data.split("_")[2])
        await handle_dish_ok(query, dish_id, context)
    elif data == "finish_order":
        await handle_finish_order(query, context)
    elif data == "drinks":
        await handle_drinks_menu(query)
    elif data.startswith("drink_category_"):
        category_name = data.split("_")[2]
        await handle_drink_category(query, category_name)
    elif data.startswith("drink_subcategory_"):
        _, _, category_name, subcategory_name = data.split("_")
        await handle_drink_subcategory(query, category_name, subcategory_name)
    elif data.startswith("get_drink_"):
        drink_id = int(data.split("_")[2])
        await handle_drink(query, drink_id)
    elif data.startswith("dish_"):
        dish_id = int(data.split("_")[1])
        await handle_dish(query, dish_id)
    elif data.startswith("category_"):
        context.user_data.pop("awaiting_question_for_dish")
        category_name = data.split("_")[1]
        await query.message.reply_text(
            "Вопросы по текущему блюду завершены. Вы можете выбрать другое блюдо."
        )
        await handle_category(query, category_name)
    elif data.startswith("back_drink_"):
        context.user_data.pop("awaiting_question_for_drink", "")
        category_name = data.split("_")[2]
        subcategory_name = data.split("_")[3]
        await query.message.reply_text(
            "Вопросы по текущему напитку завершены. Вы можете выбрать другой напиток."
        )
        await handle_drink_subcategory(query, category_name, subcategory_name)
    elif data.startswith("ask_drink_"):
        drink_id = int(data.split("_")[2])
        drink_data = await get_drink_by_id(drink_id)
        if drink_data:
            context.user_data["awaiting_question_for_drink"] = drink_data
            await query.message.reply_text("Введите ваш вопрос по этому напитку:")
        else:
            await query.message.reply_text(
                "Не удалось найти данные о выбранном напитке."
            )
    elif data.startswith("ask_dish_"):
        dish_id = int(data.split("_")[2])
        dish_data = await get_dish_by_id(dish_id)
        await query.message.reply_text("Введите ваш вопрос по этому блюду:")
        context.user_data["awaiting_question_for_dish"] = dish_data
    elif data == "general_question":
        context.user_data["general_question_in_progress"] = True
        keyboard = [
            [InlineKeyboardButton("⏹ Прекратить общение", callback_data="stop_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "🗣 Вы можете задать любой вопрос. Я поддерживаю диалог и помню историю беседы.\n\n"
            "Когда захотите закончить разговор, нажмите кнопку *Прекратить общение*.",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    elif data == "stop_chat":
        context.user_data.pop("general_question_in_progress", None)
        context.user_data.pop("conversation_history", None)
        await query.message.reply_text(
            "🔚 Общий диалог завершён. Вы можете вернуться в главное меню.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Главное меню", callback_data="welcome")]]
            ),
        )
    elif data == "welcome":
        await handle_welcome(query)
    elif data == "links":
        await handle_links(query)  # Функцию реализуйте самостоятельно
    else:
        logger.info(f"Необработанный callback_data: {data}")


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Основной обработчик входящих текстовых сообщений – направляет сообщение в зависимости от контекста.
    """
    user_message = update.message.text
    if context.user_data.get("test_general_in_progress"):
        await handle_general_test_answer(update, context)
        return
    elif context.user_data.get("test_composition_in_progress"):
        await handle_test_composition_answer(update, context)
        return
    elif context.user_data.get("test_menu_in_progress"):
        await handle_menu_test_answer(update, context)
        return
    elif context.user_data.get("test_in_progress"):
        await handle_work_features_answer(update, context)
        return
    elif context.user_data.get("test_drinks_in_progress"):
        await handle_drink_test_answer(update, context)
        return

    add_to_history(context, update.effective_user.id, "user", user_message)

    if context.user_data.get("general_question_in_progress"):
        user_prompt = (
            "Ты — эксперт по ресторанному делу и обслуживанию, наставник официанта-стажера. "
            "Твоя задача — помогать с вопросами официанта, связанными с меню (блюда, напитки), сервисом, работой официанта и всеми стандартами ресторана 'Хачапури и Вино'.\n\n"
            "📌 Ты должен использовать ТОЛЬКО информацию из подключённых файлов (меню, напитки, сервис). "
            "📌 Никогда не предлагай блюда и напитки, которых НЕТ в этих данных. "
            "📌 Если в вопросе просят рекомендацию, но нужного блюда или напитка нет, скажи, что такой позиции нет в меню, и предложи альтернативу ТОЛЬКО из доступных данных. "
            "📌 НЕ ПРИДУМЫВАЙ новых блюд, новых напитков, новых ингредиентов, новых рецептов. "
            "📌 Если пользователь спрашивает о блюде, которого нет в меню, просто сообщи об этом и не пытайся его описать.\n\n"
            f"🔹 История диалога:\n{context.user_data.get('conversation_history', [])}\n\n"
            f"🗣 Пользователь: {user_message}"
        )
        waiting_message = await update.message.reply_text("⏳ Думаю над ответом...")
        asyncio.create_task(
            process_openai_general_answer(update, context, user_prompt, waiting_message)
        )
    elif (
        "current_dish" in context.user_data
        and "current_quantity" not in context.user_data
    ):
        try:
            quantity = int(user_message)
            if quantity <= 0:
                await update.message.reply_text(
                    "Пожалуйста, введите положительное число."
                )
                return
            context.user_data["current_quantity"] = quantity
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Без комментария", callback_data="no_comment_dish"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Добавьте комментарий к блюду (или нажмите 'Без комментария'):",
                reply_markup=reply_markup,
            )
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите корректное количество (число)."
            )
    elif (
        "current_dish" in context.user_data and "current_quantity" in context.user_data
    ):
        current_dish = context.user_data.pop("current_dish")
        current_quantity = context.user_data.pop("current_quantity")
        comment = (
            user_message
            if user_message.strip().lower() != "без комментария"
            else "Без комментария"
        )
        if "order" not in context.user_data:
            context.user_data["order"] = []
        context.user_data["order"].append(
            {"dish": current_dish, "quantity": current_quantity, "comment": comment}
        )
        await update.message.reply_text(
            f"Блюдо *{current_dish[1]}* x{current_quantity} добавлено в заказ!\n"
            "Выберите следующее блюдо или завершите заказ.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Завершить заказ", callback_data="finish_order"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Продолжить выбор", callback_data="take_order"
                        )
                    ],
                ]
            ),
        )
    elif (
        "current_drink" in context.user_data
        and "current_quantity" not in context.user_data
    ):
        try:
            quantity = int(user_message)
            if quantity <= 0:
                await update.message.reply_text(
                    "Пожалуйста, введите положительное число."
                )
                return
            context.user_data["current_quantity"] = quantity
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Без комментария", callback_data="no_comment_drink"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Добавьте комментарий к напитку (или нажмите 'Без комментария'):",
                reply_markup=reply_markup,
            )
        except ValueError:
            await update.message.reply_text(
                "Пожалуйста, введите корректное количество (число)."
            )
    elif (
        "current_drink" in context.user_data and "current_quantity" in context.user_data
    ):
        current_drink = context.user_data.pop("current_drink")
        current_quantity = context.user_data.pop("current_quantity")
        comment = (
            user_message
            if user_message.strip().lower() != "без комментария"
            else "Без комментария"
        )
        if "order" not in context.user_data:
            context.user_data["order"] = []
        context.user_data["order"].append(
            {"drink": current_drink, "quantity": current_quantity, "comment": comment}
        )
        await update.message.reply_text(
            f"Напиток *{current_drink[1]}* x{current_quantity} добавлен в заказ!\n"
            "Выберите следующий напиток или завершите заказ.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Завершить заказ", callback_data="finish_order"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Продолжить выбор", callback_data="take_order"
                        )
                    ],
                ]
            ),
        )
    elif "awaiting_question_for_dish" in context.user_data:
        await handle_entity_question(
            update, context, "awaiting_question_for_dish", "dish"
        )
    elif "awaiting_question_for_drink" in context.user_data:
        await handle_entity_question(
            update, context, "awaiting_question_for_drink", "drink"
        )
    elif "awaiting_question_for_order_dish" in context.user_data:
        await handle_entity_question(
            update, context, "awaiting_question_for_order_dish", "dish"
        )
    elif "awaiting_question_for_order_drink" in context.user_data:
        await handle_entity_question(
            update, context, "awaiting_question_for_order_drink", "drink"
        )
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите блюдо или напиток для вопроса."
        )


# =============================================================================
# Точка входа
# =============================================================================
def main() -> None:
    """
    Инициализация и запуск бота.
    """
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
    logger.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()
