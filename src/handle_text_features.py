from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup


def read_text_from_file(fp: str) -> str:
    """
    Читает текст из файла с указанным путём.

    Args:
        fp (str): Путь к файлу.

    Returns:
        str: Содержимое файла или сообщение об ошибке.
    """
    try:
        with open(fp, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "Файл с информацией не найден."
    except Exception as e:
        return f"Произошла ошибка при чтении файла: {e}"


async def send_text_in_chunks(
        query,
        file_path: str,
        chunk_size: int = 4000,
        back_callback: str = None,
        first_message_edit: bool = True,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = False,
):
    """
    Считывает текст из файла, разбивает его на части указанного размера и отправляет каждую часть.

    Если first_message_edit=True, первая часть заменяет текущее сообщение (query.edit_message_text),
    а все последующие отправляются как новые (query.message.reply_text).

    Если back_callback задан, к последней части добавляется кнопка «Назад».

    Args:
        query: Объект CallbackQuery (Telegram).
        file_path (str): Путь к файлу с информацией.
        chunk_size (int, optional): Максимальная длина одной части. По умолчанию 4000.
        back_callback (str, optional): Callback для кнопки «Назад».
        first_message_edit (bool, optional): Редактировать ли первое сообщение. По умолчанию True.
        parse_mode (str, optional): Режим разметки текста. По умолчанию "Markdown".
        disable_web_page_preview (bool, optional): Отключать ли превью ссылок. По умолчанию False.
    """
    text = read_text_from_file(file_path)
    # Разбиваем текст на части
    chunks = [text[i: i + chunk_size] for i in range(0, len(text), chunk_size)]

    # Если ничего не прочитано, отправляем сообщение об отсутствии данных
    if not chunks:
        await query.edit_message_text("Нет данных для отображения.", parse_mode=parse_mode)
        return

    # Отправляем каждую часть
    for i, part in enumerate(chunks):
        keyboard = []
        # Если это последний блок и задан callback "Назад", добавляем кнопку
        if i == len(chunks) - 1 and back_callback:
            keyboard = [[InlineKeyboardButton("Назад", callback_data=back_callback)]]
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        if i == 0 and first_message_edit:
            await query.edit_message_text(
                part,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        else:
            await query.message.reply_text(
                part,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )


# Обработчики для смен и другой информации

async def handle_morning_shift(query) -> None:
    """
    Обработчик для утренней смены.
    """
    # Предполагается, что текст утренней смены помещается в один блок
    await send_text_in_chunks(query, "../resources/morning_shift.txt", chunk_size=4096, back_callback="work_features")


async def handle_day_shift(query) -> None:
    """
    Обработчик для дневной смены.
    """
    await send_text_in_chunks(query, "../resources/day_shift.txt", chunk_size=4096, back_callback="work_features")


async def handle_evening_shift(query) -> None:
    """
    Обработчик для ночной смены (evening shift).
    """
    await send_text_in_chunks(query, "../resources/night_shift.txt", chunk_size=3940, back_callback="work_features")


async def handle_iiko(query) -> None:
    """
    Обработчик для информации по iiko.
    """
    await send_text_in_chunks(query, "../resources/iiko.txt", chunk_size=3940, back_callback="work_features")


async def handle_dating(query) -> None:
    """
    Обработчик для информации о знакомстве с рестораном.
    """
    await send_text_in_chunks(query, "../resources/dating.txt", chunk_size=3940, back_callback="work_features")


async def handle_base(query) -> None:
    """
    Обработчик для информации по основам работы.
    """
    await send_text_in_chunks(query, "../resources/base.txt", chunk_size=3907, back_callback="work_features")


async def handle_bring(query) -> None:
    """
    Обработчик для информации по работе на раздаче.
    """
    await send_text_in_chunks(query, "../resources/bring.txt", chunk_size=4000, back_callback="work_features")


async def handle_wine(query) -> None:
    """
    Обработчик для информации о вине.
    """
    await send_text_in_chunks(query, "../resources/wine.txt", chunk_size=4000, back_callback="work_features")


async def handle_service(query) -> None:
    """
    Обработчик для информации по сервису.
    """
    await send_text_in_chunks(query, "../resources/service.txt", chunk_size=4000, back_callback="work_features")


async def handle_instruction(query) -> None:
    """
    Обработчик для отображения инструкции.
    """
    await send_text_in_chunks(query, "../resources/instruction.txt", chunk_size=4000, back_callback="welcome")


async def handle_host(query) -> None:
    """
    Обработчик для информации о хосте.
    """
    await send_text_in_chunks(query, "../resources/host.txt", chunk_size=4000, back_callback="work_features")


async def handle_delivery(query) -> None:
    """
    Обработчик для информации по доставке.
    """
    await send_text_in_chunks(query, "../resources/delivery.txt", chunk_size=4000, back_callback="work_features")


async def handle_bar(query) -> None:
    """
    Обработчик для информации по бару.
    """
    await send_text_in_chunks(query, "../resources/bar.txt", chunk_size=4000, back_callback="work_features")


async def handle_special(query) -> None:
    """
    Обработчик для информации по особым случаям (work).
    """
    await send_text_in_chunks(query, "../resources/work.txt", chunk_size=4000, back_callback="work_features")


async def handle_links(query) -> None:
    """
    Обработчик для отображения полезных ссылок.
    """
    # Для ссылок отключаем веб-превью и используем один блок (если текст длинный, можно добавить разделение)
    await send_text_in_chunks(
        query,
        "../resources/useful_links.txt",
        chunk_size=4000,
        back_callback="welcome",
        disable_web_page_preview=True
    )
