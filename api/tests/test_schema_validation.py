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


def test_schema_validator_requires_comment_response_schema():
    schema = deepcopy(app.openapi())
    schema["components"]["schemas"].pop("CommentResponse")

    assert validate_schema(schema) is False


def test_schema_validator_requires_idea_detail_comments_field():
    schema = deepcopy(app.openapi())
    schema["components"]["schemas"]["IdeaDetailResponse"]["properties"].pop(
        "comments"
    )

    assert validate_schema(schema) is False


def test_schema_validator_requires_idea_detail_comments_field_to_be_required():
    schema = deepcopy(app.openapi())
    idea_detail_response = schema["components"]["schemas"]["IdeaDetailResponse"]
    idea_detail_response["required"] = [
        field
        for field in idea_detail_response.get("required", [])
        if field != "comments"
    ]

    assert validate_schema(schema) is False
