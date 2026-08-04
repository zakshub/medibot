from medibot.main import create_app


def test_openapi_contains_versioned_product_routes() -> None:
    schema = create_app().openapi()

    assert set(schema["paths"]) == {
        "/v1/health",
        "/v1/ready",
        "/v1/messages",
        "/v1/video/status",
        "/v1/video/domain",
        "/v1/video/dataset",
        "/v1/video/videos",
        "/v1/video/previews",
        "/v1/video/previews/{content_id}/storyboard",
        "/v1/video/videos/{candidate_id}/approve",
        "/v1/video/insights",
        "/v1/video/schedule/recommend",
    }
    assert schema["info"]["version"] == "0.1.0"


def test_video_operator_routes_document_api_key_security() -> None:
    schema = create_app().openapi()
    security_schemes = schema["components"]["securitySchemes"]

    assert security_schemes == {
        "APIKeyHeader": {"type": "apiKey", "in": "header", "name": "X-Operator-Key"}
    }
    for path, operations in schema["paths"].items():
        if not path.startswith("/v1/video/"):
            continue
        for operation in operations.values():
            assert operation["security"] == [{"APIKeyHeader": []}]


def test_message_contract_documents_all_bounded_responses() -> None:
    operation = create_app().openapi()["paths"]["/v1/messages"]["post"]

    assert set(operation["responses"]) == {"200", "413", "422", "429", "503"}
    for status_code in ("413", "422", "429"):
        schema_ref = operation["responses"][status_code]["content"]["application/json"]["schema"]
        assert schema_ref == {"$ref": "#/components/schemas/ErrorResponse"}

    unavailable_schema = operation["responses"]["503"]["content"]["application/json"]["schema"]
    assert unavailable_schema == {"$ref": "#/components/schemas/MessageResponse"}


def test_error_response_schema_cannot_contain_health_input() -> None:
    schemas = create_app().openapi()["components"]["schemas"]
    error_properties = schemas["ErrorResponse"]["properties"]
    detail_properties = schemas["ErrorDetail"]["properties"]

    assert set(error_properties) == {"request_id", "error"}
    assert set(detail_properties) == {"code", "message"}
    assert "input" not in error_properties
    assert "detail" not in error_properties


def test_message_request_forbids_additional_properties() -> None:
    request_schema = create_app().openapi()["components"]["schemas"]["MessageRequest"]

    assert request_schema["additionalProperties"] is False
    assert set(request_schema["required"]) == {"message", "locale"}
