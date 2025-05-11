# flake8: noqa

"""
Модуль для работы с базой данных (asyncpg).

Содержит функции для получения случайных вопросов, категорий, информации о блюдах и напитках.

Функции:
    - connect_to_db() -> asyncpg.Connection
    - get_random_work_features_general(n: int = 3) -> List[Dict[str, Any]]
    - get_random_menu_questions_general(n: int = 6) -> List[Dict[str, Any]]
    - get_random_drink_questions_general(n: int = 6) -> List[Dict[str, Any]]
    - get_random_questions() -> List[Dict[str, Any]]
    - get_random_drink_questions(category: str) -> List[Dict[str, Any]]
    - get_random_menu_questions() -> List[Dict[str, Any]]
    - get_dish_ingredients(dish_id: int) -> Optional[Dict[str, str]]
    - get_categories() -> List[str]
    - get_subcategories_by_category(category: str) -> List[str]
    - get_dishes_by_category(category: str) -> List[Dict[str, Any]]
    - get_drink_categories() -> List[str]
    - get_drinks_by_subcategory(category: str, subcategory: str) -> List[Dict[str, Any]]
    - get_dish_by_id(dish_id: int) -> Optional[List[Any]]
    - get_drink_by_id(drink_id: int) -> Optional[List[Any]]
"""

import json
import random
from typing import Any, Dict, List, Optional

import asyncpg

# Загрузка конфигурации подключения к БД
with open("../config/db_config.json", "r", encoding="utf-8") as file:
    db_config = json.load(file)


async def connect_to_db() -> asyncpg.Connection:
    """
    Подключается к базе данных с использованием конфигурационных данных.

    Returns:
        asyncpg.Connection: Объект подключения к базе данных.
    """
    return await asyncpg.connect(
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["dbname"],
        host=db_config["host"],
        port=db_config["port"],
    )


async def get_random_work_features_general(n: int = 3) -> List[Dict[str, Any]]:
    """
    Возвращает случайные вопросы по особенностям работы.

    Args:
        n (int, optional): Количество вопросов. По умолчанию 3.

    Returns:
        List[Dict[str, Any]]: Список вопросов с ключами "question", "answer", "explanation" и "type".
    """
    conn = await connect_to_db()
    try:
        rows = await conn.fetch(
            "SELECT question, answer, explanation FROM work_features_questions "
            "ORDER BY RANDOM() LIMIT $1",
            n * 2,
        )
        # Убираем дубликаты
        unique = list({(r["question"], r["answer"], r["explanation"]) for r in rows})
        random.shuffle(unique)
        selected = unique[:n]
        return [
            {"question": q[0], "answer": q[1], "explanation": q[2], "type": "work"}
            for q in selected
        ]
    finally:
        await conn.close()


async def get_random_menu_questions_general(n: int = 6) -> List[Dict[str, Any]]:
    """
    Возвращает случайные общие вопросы по меню.

    Args:
        n (int, optional): Количество вопросов. По умолчанию 6.

    Returns:
        List[Dict[str, Any]]: Список вопросов с ключами "id", "question", "answer", "explanation" и "type".
    """
    conn = await connect_to_db()
    try:
        rows = await conn.fetch(
            "SELECT id, question, answer, explanation FROM faq ORDER BY RANDOM() LIMIT $1",
            n * 2,
        )
        unique = list(
            {(r["id"], r["question"], r["answer"], r["explanation"]) for r in rows}
        )
        random.shuffle(unique)
        selected = unique[:n]
        return [
            {
                "id": q[0],
                "question": q[1],
                "answer": q[2],
                "explanation": q[3],
                "type": "menu",
            }
            for q in selected
        ]
    finally:
        await conn.close()


async def get_random_drink_questions_general(n: int = 6) -> List[Dict[str, Any]]:
    """
    Возвращает случайные общие вопросы по напиткам.

    Args:
        n (int, optional): Количество вопросов. По умолчанию 6.

    Returns:
        List[Dict[str, Any]]: Список вопросов с ключами "id", "question", "answer", "explanation" и "type".
    """
    conn = await connect_to_db()
    try:
        rows = await conn.fetch(
            "SELECT id, question, answer, explanation FROM drinks_questions ORDER BY RANDOM() LIMIT $1",
            n * 2,
        )
        random.shuffle(rows)
        selected = rows[:n]
        return [
            {
                "id": r["id"],
                "question": r["question"],
                "answer": r["answer"],
                "explanation": r["explanation"],
                "type": "drink",
            }
            for r in selected
        ]
    finally:
        await conn.close()


async def get_random_questions() -> List[Dict[str, Any]]:
    """
    Возвращает случайные вопросы по особенностям работы.

    Returns:
        List[Dict[str, Any]]: Список вопросов с ключами "question", "correct_answer" и "explanation".
    """
    conn = await connect_to_db()
    try:
        rows = await conn.fetch(
            "SELECT question, answer, explanation FROM work_features_questions "
            "ORDER BY RANDOM() LIMIT 10"
        )
        unique = list({(r["question"], r["answer"], r["explanation"]) for r in rows})
        random.shuffle(unique)
        selected = unique[:5]
        return [
            {"question": q[0], "correct_answer": q[1], "explanation": q[2]}
            for q in selected
        ]
    finally:
        await conn.close()


async def get_random_drink_questions(category: str) -> List[Dict[str, Any]]:
    """
    Выбирает случайные вопросы по напиткам для заданной категории.

    Args:
        category (str): Название категории напитков.

    Returns:
        List[Dict[str, Any]]: Список вопросов с ключами "id", "question", "answer" и "explanation".
    """
    conn = await connect_to_db()
    try:
        query = """
            SELECT id, question, answer, explanation FROM drinks_questions
            WHERE category = $1
            ORDER BY RANDOM() LIMIT 7
        """
        raw_questions = await conn.fetch(query, category)
        if not raw_questions:
            return []
        questions = [
            {
                "id": row["id"],
                "question": row["question"],
                "answer": row["answer"],
                "explanation": row["explanation"],
            }
            for row in raw_questions
        ]
        random.shuffle(questions)
        return questions
    finally:
        await conn.close()


async def get_random_menu_questions() -> List[Dict[str, Any]]:
    """
    Выбирает случайные вопросы по меню.

    Returns:
        List[Dict[str, Any]]: Список вопросов с ключами "id", "question", "answer" и "explanation".
    """
    conn = await connect_to_db()
    try:
        query = "SELECT id, question, answer, explanation FROM faq ORDER BY RANDOM() LIMIT 12"
        raw_questions = await conn.fetch(query)
        if not raw_questions:
            return []
        unique_questions = list(
            {
                (row["id"], row["question"], row["answer"], row["explanation"])
                for row in raw_questions
            }
        )
        random.shuffle(unique_questions)
        selected_questions = unique_questions[:7]
        return [
            {"id": q[0], "question": q[1], "answer": q[2], "explanation": q[3]}
            for q in selected_questions
        ]
    finally:
        await conn.close()


async def get_dish_ingredients(dish_id: int) -> Optional[Dict[str, str]]:
    """
    Получает ингредиенты блюда по его ID.

    Args:
        dish_id (int): Идентификатор блюда.

    Returns:
        Optional[Dict[str, str]]: Словарь с ключами "name" (название блюда) и "ingredients", либо None, если запись не найдена.
    """
    conn = await connect_to_db()
    try:
        query = "SELECT question, answer FROM test_ingredients WHERE id = $1"
        row = await conn.fetchrow(query, dish_id)
        if row:
            return {"name": row["question"], "ingredients": row["answer"]}
        return None
    finally:
        await conn.close()


async def get_categories() -> List[str]:
    """
    Получает все категории блюд.

    Returns:
        List[str]: Список категорий.
    """
    conn = await connect_to_db()
    try:
        query = "SELECT DISTINCT category FROM full_menu"
        rows = await conn.fetch(query)
        categories = [row["category"] for row in rows]

        desired_order = [
            "Специи и соусы",
            "Закуски",
            "Салаты",
            "Супы",
            "Горячее",
            "Хачапури",
            "Хинкали",
            "Тесто",
            "Завтраки",
            "Десерты",
        ]
        categories = sorted(
            categories,
            key=lambda x: (
                desired_order.index(x) if x in desired_order else float("inf")
            ),
        )
        return categories
    finally:
        await conn.close()


async def get_subcategories_by_category(category: str) -> List[str]:
    """
    Получает подкатегории напитков для заданной категории.

    Args:
        category (str): Название категории.

    Returns:
        List[str]: Список подкатегорий.
    """
    conn = await connect_to_db()
    try:
        query = "SELECT DISTINCT subcategory FROM drinks WHERE category = $1 ORDER BY subcategory"
        rows = await conn.fetch(query, category)
        return [row["subcategory"] for row in rows]
    finally:
        await conn.close()


async def get_dishes_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Получает блюда для заданной категории.

    Args:
        category (str): Название категории.

    Returns:
        List[Dict[str, Any]]: Список блюд с ключами "id" и "name".
    """
    conn = await connect_to_db()
    try:
        query = "SELECT id, name FROM full_menu WHERE category = $1 ORDER BY id"
        rows = await conn.fetch(query, category)
        return [{"id": row["id"], "name": row["name"]} for row in rows]
    finally:
        await conn.close()


async def get_drink_categories() -> List[str]:
    """
    Получает все категории напитков.

    Returns:
        List[str]: Список категорий напитков.
    """
    conn = await connect_to_db()
    try:
        query = "SELECT DISTINCT category FROM drinks ORDER BY category"
        rows = await conn.fetch(query)
        return [row["category"] for row in rows]
    finally:
        await conn.close()


async def get_drinks_by_subcategory(
    category: str, subcategory: str
) -> List[Dict[str, Any]]:
    """
    Получает напитки для заданной подкатегории.

    Args:
        category (str): Название категории.
        subcategory (str): Название подкатегории.

    Returns:
        List[Dict[str, Any]]: Список напитков с ключами "id" и "name".
    """
    conn = await connect_to_db()
    try:
        query = "SELECT id, name FROM drinks WHERE category = $1 AND subcategory = $2 ORDER BY id"
        rows = await conn.fetch(query, category, subcategory)
        return [{"id": row["id"], "name": row["name"]} for row in rows]
    finally:
        await conn.close()


async def get_dish_by_id(dish_id: int) -> Optional[List[Any]]:
    """
    Получает информацию о блюде по его ID.

    Args:
        dish_id (int): Идентификатор блюда.

    Returns:
        Optional[List[Any]]: Список значений полей записи о блюде или None, если запись не найдена.
    """
    conn = await connect_to_db()
    try:
        query = """
            SELECT id, name, category, description, photo_url, features,
                   ingredients, details, allergens, veg 
            FROM full_menu 
            WHERE id = $1
        """
        row = await conn.fetchrow(query, dish_id)
        return list(row.values()) if row else None
    finally:
        await conn.close()


async def get_drink_by_id(drink_id: int) -> Optional[List[Any]]:
    """
    Получает информацию о напитке по его ID.

    Args:
        drink_id (int): Идентификатор напитка.

    Returns:
        Optional[List[Any]]: Список значений полей записи о напитке или None, если запись не найдена.
    """
    conn = await connect_to_db()
    try:
        query = """
            SELECT id, name, category, description, photo_url, notes, 
                   ingredients, aroma_profile, taste_profile, sugar_content, 
                   producer, gastropair, subcategory
            FROM drinks 
            WHERE id = $1
        """
        row = await conn.fetchrow(query, drink_id)
        return list(row.values()) if row else None
    finally:
        await conn.close()
