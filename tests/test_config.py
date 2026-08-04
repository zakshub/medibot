import pytest
from pydantic import ValidationError

from medibot.config import Settings


def test_default_settings_are_fail_closed() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "local"
    assert settings.policy_version == "unapproved"
    assert settings.debug is False
    assert settings.max_request_body_bytes == 16_384


@pytest.mark.parametrize("environment", ["development", "prod", "unknown", ""])
def test_environment_must_be_allow_listed(environment: str) -> None:
    with pytest.raises(ValidationError):
        Settings(environment=environment, _env_file=None)


@pytest.mark.parametrize("body_limit", [0, 1_023, 1_048_577])
def test_request_body_limit_must_stay_in_safe_range(body_limit: int) -> None:
    with pytest.raises(ValidationError):
        Settings(max_request_body_bytes=body_limit, _env_file=None)


def test_production_debug_is_prohibited() -> None:
    with pytest.raises(ValidationError, match="debug mode is prohibited in production"):
        Settings(environment="production", debug=True, _env_file=None)


def test_production_requires_operator_api_key() -> None:
    with pytest.raises(ValidationError, match="operator API key is required"):
        Settings(environment="production", _env_file=None)


def test_production_accepts_configured_operator_api_key() -> None:
    settings = Settings(
        environment="production",
        operator_api_key="synthetic-operator-secret",
        _env_file=None,
    )

    assert settings.operator_api_key is not None
    assert settings.operator_api_key.get_secret_value() == "synthetic-operator-secret"


def test_policy_version_rejects_unsafe_characters() -> None:
    with pytest.raises(ValidationError):
        Settings(policy_version="release 1/<script>", _env_file=None)
