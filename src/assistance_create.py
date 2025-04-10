"""
Модуль для создания Vector Store с данными о меню, напитках и дополнительной информацией,
а также для создания ассистента, использующего комбинированный поиск по файлам.

Функции:
    - create_vector_store_with_menu_and_drinks() -> str
    - create_assistant_with_combined_file_search(vector_store_id: str) -> str
"""

from contextlib import ExitStack
import logging
from typing import List

# Явные импорты функций для экспорта данных в JSON
from export_json import (
    export_menu_to_json,
    export_drinks_to_json,
    export_drinks_questions_to_json,
    export_faq_to_json,
    export_test_ingredients_to_json,
    export_work_features_questions_to_json,
)
from bot import client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_vector_store_with_menu_and_drinks() -> str:
    """
    Экспортирует данные о меню, напитках и связанных разделах в JSON-файлы,
    создаёт Vector Store и загружает в него файлы.

    Экспортируются следующие файлы:
      - Меню ресторана
      - Напитки ресторана
      - Вопросы по напиткам
      - FAQ
      - Данные для тестирования состава ингредиентов
      - Вопросы по особенностям работы
      - Дополнительные файлы: warnings.txt и service.txt

    Returns:
        str: Идентификатор созданного Vector Store.
    """
    # Экспорт данных в JSON-файлы
    menu_file_path = export_menu_to_json()
    drinks_file_path = export_drinks_to_json()
    drinks_questions_file_path = export_drinks_questions_to_json()
    faq_file_path = export_faq_to_json()
    test_ingredients_file_path = export_test_ingredients_to_json()
    work_features_questions_file_path = export_work_features_questions_to_json()

    # Пути к дополнительным файлам
    warnings_file_path = "../resources/warnings.txt"
    service_file_path = "../resources/service.txt"

    # Создаем Vector Store
    vector_store = client.beta.vector_stores.create(name="Menu, Drinks, and Service Data Store")
    logger.info("Создан Vector Store с ID: %s", vector_store.id)

    # Список всех путей к файлам для загрузки
    file_paths: List[str] = [
        menu_file_path,
        drinks_file_path,
        warnings_file_path,
        service_file_path,
        drinks_questions_file_path,
        faq_file_path,
        test_ingredients_file_path,
        work_features_questions_file_path,
    ]

    # Открываем все файлы в бинарном режиме с использованием ExitStack
    with ExitStack() as stack:
        file_streams = [stack.enter_context(open(path, "rb")) for path in file_paths]

        # Загружаем файлы в Vector Store
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=file_streams
        )

    logger.info("Vector Store создан с ID: %s", vector_store.id)
    logger.info("Статус загрузки: %s", file_batch.status)
    logger.info("Количество загруженных файлов: %s", file_batch.file_counts)
    return vector_store.id


def create_assistant_with_combined_file_search(vector_store_id: str) -> str:
    """
    Создает ассистента, использующего комбинированный поиск по файлам из указанного Vector Store.

    Args:
        vector_store_id (str): Идентификатор Vector Store, содержащего файлы с данными.

    Returns:
        str: Идентификатор созданного ассистента.
    """
    instructions = (
        "Ты — ассистент ресторана. Отвечай на вопросы, связанные с ресторанной тематикой, а также на общие вопросы, "
        "которые могут быть связаны с работой ресторана, обслуживанием, меню, напитками или сервисом. "
        "Если вопрос не относится к ресторанной тематике (например, 'Какая погода сегодня?'), вежливо попроси задать вопрос по теме. "
        "Будь лояльным к вопросам, которые могут быть связаны с ресторанной тематикой, даже если они сформулированы не строго. "
        "Если в данных нет конкретного комментария о том, что можно сделать с блюдом (например, изменить тесто, убрать соус или специи), "
        "в первую очередь используй данные из подключенных файлов, а если ничего не нашел – из своей базы знаний отвечай, "
        "что это невозможно, так как в нашем ресторане так блюдо не подают. "
        "Все соусы и специи — цельные заготовки, их нельзя изменять. Если пользователь спрашивает о такой возможности, "
        "отвечай, что это не предусмотрено. Будь строг в своих ответах, когда речь идёт о соблюдении стандартов ресторана, "
        "но проявляй гибкость в коммуникации, чтобы пользователь чувствовал себя комфортно."
    )

    assistant = client.beta.assistants.create(
        name="Restaurant Assistant",
        instructions=instructions,
        model="gpt-4o-mini",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )
    logger.info("Ассистент создан с ID: %s", assistant.id)
    return assistant.id
