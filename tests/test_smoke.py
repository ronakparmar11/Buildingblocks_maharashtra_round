import blackbox
from blackbox.config import get_settings


def test_package_imports_and_settings_load() -> None:
    settings = get_settings()

    assert blackbox.__name__ == "blackbox"
    assert settings.LLM_PROVIDER == "gemini"
    assert settings.DB_PATH == "data/blackbox.db"
