import pytest
import asyncio
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from db_func import get_categories

@pytest.mark.asyncio
async def test_get_categories():
    cats = await get_categories()
    assert isinstance(cats, list)
    # предполагаем, что хотя бы одна категория есть
    assert len(cats) > 0


@pytest.mark.asyncio
async def test_get_dishes_by_category():
    cats = await get_categories()
    first = cats[0]
    dishes = await get_dishes_by_category(first)
    assert isinstance(dishes, list)
    for d in dishes:
        assert "id" in d and "name" in d
