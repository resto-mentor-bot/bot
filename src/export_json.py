import json
from typing import Any

from bot import connect_to_db


def export_table_to_json(query: str, json_file_path: str) -> str:
    """
    Выполняет указанный SQL-запрос, получает все данные,
    формирует список словарей и экспортирует данные в JSON-файл.

    Args:
        query (str): SQL-запрос для извлечения данных.
        json_file_path (str): Путь к файлу, в который будут записаны данные.

    Returns:
        str: Путь к созданному JSON-файлу.
    """
    conn = connect_to_db()
    try:
        # Используем контекстный менеджер для курсора
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]

        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        print(f"Данные экспортированы в JSON-файл: {json_file_path}")
        return json_file_path
    except Exception as e:
        print(f"Ошибка при экспорте данных: {e}")
        raise
    finally:
        conn.close()


def export_menu_to_json() -> str:
    """
    Экспортирует данные из таблицы full_menu в JSON-файл.

    Returns:
        str: Путь к JSON-файлу с данными меню.
    """
    query = "SELECT * FROM full_menu"
    json_file_path = "../data/menu_data.json"
    return export_table_to_json(query, json_file_path)


def export_drinks_to_json() -> str:
    """
    Экспортирует данные из таблицы drinks в JSON-файл.

    Returns:
        str: Путь к JSON-файлу с данными напитков.
    """
    query = "SELECT * FROM drinks"
    json_file_path = "../data/drinks_data.json"
    return export_table_to_json(query, json_file_path)


def export_drinks_questions_to_json() -> str:
    """
    Экспортирует данные из таблицы drinks_questions в JSON-файл.

    Returns:
        str: Путь к JSON-файлу с данными вопросов по напиткам.
    """
    query = "SELECT * FROM drinks_questions"
    json_file_path = "../data/drinks_questions_data.json"
    return export_table_to_json(query, json_file_path)


def export_faq_to_json() -> str:
    """
    Экспортирует данные из таблицы faq в JSON-файл.

    Returns:
        str: Путь к JSON-файлу с FAQ.
    """
    query = "SELECT * FROM faq"
    json_file_path = "../data/faq_data.json"
    return export_table_to_json(query, json_file_path)


def export_test_ingredients_to_json() -> str:
    """
    Экспортирует данные из таблицы test_ingredients в JSON-файл.

    Returns:
        str: Путь к JSON-файлу с данными по тестированию ингредиентов.
    """
    query = "SELECT * FROM test_ingredients"
    json_file_path = "../data/test_ingredients_data.json"
    return export_table_to_json(query, json_file_path)


def export_work_features_questions_to_json() -> str:
    """
    Экспортирует данные из таблицы work_features_questions в JSON-файл.

    Returns:
        str: Путь к JSON-файлу с вопросами по особенностям работы.
    """
    query = "SELECT * FROM work_features_questions"
    json_file_path = "../data/work_features_questions_data.json"
    return export_table_to_json(query, json_file_path)
