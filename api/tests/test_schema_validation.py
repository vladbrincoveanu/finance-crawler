from copy import deepcopy

from api.main import app
from api.validate_schema import validate_schema


def test_schema_validator_requires_crawl_status_endpoint():
    schema = deepcopy(app.openapi())
    schema["paths"].pop("/crawl/status")

    assert validate_schema(schema) is False


def test_schema_validator_requires_crawl_status_response_schemas():
    schema = deepcopy(app.openapi())
    schema["components"]["schemas"].pop("CrawlCountsResponse")

    assert validate_schema(schema) is False


def test_schema_validator_requires_pending_identity_count_field():
    schema = deepcopy(app.openapi())
    schema["components"]["schemas"]["CrawlCountsResponse"]["properties"].pop(
        "pending_identity"
    )

    assert validate_schema(schema) is False


def test_crawl_status_runtime_fields_are_required_or_explicitly_nullable():
    schema = app.openapi()
    definitions = schema["components"]["schemas"]

    assert set(definitions["CrawlRunResponse"]["required"]) == {
        "id",
        "source",
        "target",
        "status",
        "parser_version",
        "started_at",
        "finished_at",
        "rows_seen",
        "rows_accepted",
        "rows_rejected",
        "rows_duplicate",
        "error_message",
    }
    assert set(definitions["CrawlCountsResponse"]["required"]) == {
        "parser_output",
        "staged",
        "pending_identity",
        "curated",
        "public",
    }
