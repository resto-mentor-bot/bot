import pytest
from unittest.mock import AsyncMock, patch
from src.assistance_create import (
    create_assistant_with_combined_file_search,
    create_vector_store_with_menu_and_drinks,
)
#

@pytest.fixture(autouse=True)
def mock_openai_client(monkeypatch):
    fake = AsyncMock()
    fake.beta.vector_stores.create.return_value.id = "vs_test"
    fake.beta.vector_stores.file_batches.upload_and_poll.return_value.status = (
        "completed"
    )
    fake.beta.assistants.create.return_value.id = "asst_test"
    monkeypatch.setattr("src.assistance_create.client", fake)
    return fake


def test_create_vector_store(tmp_path, mock_openai_client):
    # мокаем экспорт JSON, чтобы не зависеть от БД
    with (
        patch(
            "src.assistance_create.export_menu_to_json",
            return_value=str(tmp_path / "m.json"),
        ),
        patch(
            "src.assistance_create.export_drinks_to_json",
            return_value=str(tmp_path / "d.json"),
        ),
        patch(
            "src.assistance_create.export_drinks_questions_to_json",
            return_value=str(tmp_path / "dq.json"),
        ),
        patch(
            "src.assistance_create.export_faq_to_json",
            return_value=str(tmp_path / "f.json"),
        ),
        patch(
            "src.assistance_create.export_test_ingredients_to_json",
            return_value=str(tmp_path / "ti.json"),
        ),
        patch(
            "src.assistance_create.export_work_features_questions_to_json",
            return_value=str(tmp_path / "wq.json"),
        ),
    ):
        vid = create_vector_store_with_menu_and_drinks()
        assert vid == "vs_test"


def test_create_assistant(mock_openai_client):
    aid = create_assistant_with_combined_file_search("vs_test")
    assert aid == "asst_test"
