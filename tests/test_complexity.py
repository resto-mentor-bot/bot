import pytest
from radon.complexity import cc_visit
from radon.visitors import Function
import pathlib

# максимально допустимая сложность для одной функции
MAX_COMPLEXITY = 10
# MAX_COMPLEXITY = 65
# E       AssertionError: Найдены функции с избыточной сложностью (> 10):
# E         src\bot.py:send_drink_card — 13
# E         src\bot.py:button_handler — 64
# E         src\bot.py:handle_question — 27


def get_source_files():
    """Собираем все .py-файлы в src/"""
    root = pathlib.Path(__file__).parent.parent / "src"
    return list(root.rglob("*.py"))


def test_cyclomatic_complexity():
    """
    Проверяем, что в проекте нет функций с цикломатической сложностью выше MAX_COMPLEXITY.
    """
    too_complex = []
    for path in get_source_files():
        code = path.read_text(encoding="utf-8")
        for block in cc_visit(code):
            # блоки Function/Method
            if isinstance(block, Function) and block.complexity > MAX_COMPLEXITY:
                too_complex.append(
                    (path.relative_to(path.parent.parent), block.name, block.complexity)
                )

    assert (
        not too_complex
    ), "Найдены функции с избыточной сложностью (> {}):\n{}".format(
        MAX_COMPLEXITY,
        "\n".join(f"{file}:{name} — {comp}" for file, name, comp in too_complex),
    )
