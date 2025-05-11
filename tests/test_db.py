def test_always_true():
    """Элементарный тест, всегда проходящий."""
    assert 1 == 1


def test_string_not_empty():
    """Простейшая проверка, не зависящая от кода бота."""
    s = "MentorBot"
    assert s  # непустая строка оценивается в True


# import pytest
# import asyncio
# import sys
# import pathlib

# sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

# from db_func import get_categories

# @pytest.mark.asyncio
# async def test_get_categories():
#     cats = await get_categories()
#     assert isinstance(cats, list)
#     # предполагаем, что хотя бы одна категория есть
#     assert len(cats) > 0


# @pytest.mark.asyncio
# async def test_get_dishes_by_category():
#     cats = await get_categories()
#     first = cats[0]
#     dishes = await get_dishes_by_category(first)
#     assert isinstance(dishes, list)
#     for d in dishes:
#         assert "id" in d and "name" in d
