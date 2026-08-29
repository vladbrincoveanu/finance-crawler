import json

from ValueInvestorsClub.ValueInvestorsClub import vic_note


def _item(**over):
    base = {
        "ticker": "AAPL",
        "companyName": "Apple Inc.",
        "date_iso": "2019-04-12",
        "username": "someuser",
        "idea_id": "1234567",
        "link": "https://valueinvestorsclub.com/idea/APPLE/1234567",
        "description": "Thesis line one.\nThesis line two.",
        "catalysts": "Catalyst line.",
        "comments": [],
        "isShort": False,
        "isContestWinner": False,
    }
    base.update(over)
    return base


def _frontmatter(doc: str) -> dict:
    assert doc.startswith("---\n")
    block = doc.split("---\n", 2)[1]
    out = {}
    for line in block.strip().split("\n"):
        k, v = line.split(": ", 1)
        out[k] = v
    return out


def test_note_path_is_ticker_sharded():
    assert vic_note.note_path(_item()) == "vic/AAPL/2019-04-12__someuser__1234567.md"


def test_note_path_is_deterministic():
    assert vic_note.note_path(_item()) == vic_note.note_path(_item())


def test_note_path_falls_back_when_fields_missing():
    path = vic_note.note_path(_item(ticker="", username="", date_iso=""))
    assert path == "vic/UNKNOWN/unknown-date__unknown-user__1234567.md"


def test_note_path_sanitises_unsafe_segments():
    path = vic_note.note_path(_item(ticker="BRK/B", username="a b/c"))
    assert path == "vic/BRKB/2019-04-12__a_bc__1234567.md"


def test_safe_segment_falls_back_for_whitespace_only_input():
    assert vic_note.safe_segment(" \t\n") == "unknown"


def test_safe_segment_falls_back_for_dot_segments():
    assert vic_note.safe_segment(".") == "unknown"
    assert vic_note.safe_segment("..") == "unknown"


def test_note_path_falls_back_when_idea_id_is_missing():
    item = _item()
    del item["idea_id"]
    assert vic_note.note_path(item) == "vic/AAPL/2019-04-12__someuser__unknown-id.md"


def test_frontmatter_carries_search_keys():
    fm = _frontmatter(vic_note.render(_item())[1])
    assert fm["source"] == '"vic"'
    assert fm["source_id"] == '"1234567"'
    assert fm["ticker"] == '"AAPL"'
    assert fm["company"] == '"Apple Inc."'
    assert fm["author"] == '"someuser"'
    assert fm["date"] == '"2019-04-12"'
    assert fm["url"] == '"https://valueinvestorsclub.com/idea/APPLE/1234567"'
    assert fm["is_short"] == "false"
    assert fm["comment_count"] == "0"


def test_frontmatter_escapes_quotes_in_company_name():
    fm = _frontmatter(vic_note.render(_item(companyName='The "Big" Co'))[1])
    assert fm["company"] == '"The \\"Big\\" Co"'


def test_render_returns_path_and_document():
    path, doc = vic_note.render(_item())
    assert path == "vic/AAPL/2019-04-12__someuser__1234567.md"
    assert doc.startswith("---\n")


def test_frontmatter_round_trips_control_characters():
    company_name = 'Line one\nLine two\r\t\0\x01"quoted"\\ caf\u00e9'
    fm = _frontmatter(vic_note.render(_item(companyName=company_name))[1])
    assert json.loads(fm["company"]) == company_name


def test_frontmatter_parses_winner_and_comment_count():
    fm = _frontmatter(
        vic_note.render(_item(isContestWinner=True, comments=[{}, {}]))[1]
    )
    assert fm["is_contest_winner"] == "true"
    assert fm["comment_count"] == "2"


def test_frontmatter_treats_string_false_as_false():
    fm = _frontmatter(vic_note.render(_item(isShort="false"))[1])
    assert fm["is_short"] == "false"


def test_body_restores_paragraph_breaks():
    doc = vic_note.render(_item())[1]
    assert "Thesis line one.\n\nThesis line two." in doc


def test_body_has_title_and_wikilinks():
    doc = vic_note.render(_item())[1]
    assert "# Apple Inc. ([[AAPL]])" in doc
    assert "Idea by [[someuser]] · 2019-04-12 · Long" in doc


def test_body_marks_shorts():
    doc = vic_note.render(_item(isShort=True))[1]
    assert "· Short" in doc


def test_body_treats_string_false_as_long():
    doc = vic_note.render(_item(isShort="false"))[1]
    assert "· Long" in doc


def test_body_has_sections_and_source_link():
    doc = vic_note.render(_item())[1]
    assert "## Thesis" in doc
    assert "## Catalysts" in doc
    assert "[Original on VIC](https://valueinvestorsclub.com/idea/APPLE/1234567)" in doc


def test_body_is_wrapped_in_generated_markers():
    doc = vic_note.render(_item())[1]
    assert vic_note.BEGIN_MARKER in doc
    assert doc.rstrip().endswith(vic_note.END_MARKER)


def test_empty_catalysts_section_is_omitted():
    doc = vic_note.render(_item(catalysts=""))[1]
    assert "## Catalysts" not in doc


_COMMENTS = [
    {"author": "bob", "when": "2019-04-14", "text": "Seasonal, not structural."},
    {"author": "sue", "when": "", "text": "Line one.\nLine two."},
]


def test_discussion_renders_each_comment_as_blockquote():
    doc = vic_note.render(_item(comments=_COMMENTS))[1]
    assert "## Discussion" in doc
    assert "**bob** · 2019-04-14" in doc
    assert "> Seasonal, not structural." in doc


def test_discussion_omits_missing_timestamp():
    doc = vic_note.render(_item(comments=_COMMENTS))[1]
    assert "**sue**\n" in doc


def test_discussion_blockquotes_every_line():
    doc = vic_note.render(_item(comments=_COMMENTS))[1]
    assert "> Line one.\n>\n> Line two." in doc


def test_discussion_section_omitted_when_no_comments():
    assert "## Discussion" not in vic_note.render(_item(comments=[]))[1]


def test_comment_count_reflects_comments():
    doc = vic_note.render(_item(comments=_COMMENTS))[1]
    assert _frontmatter(doc)["comment_count"] == "2"


def test_discussion_precedes_source():
    doc = vic_note.render(_item(comments=_COMMENTS))[1]
    assert doc.index("## Discussion") < doc.index("## Source")


def test_merge_returns_document_when_no_existing_file():
    _, doc = vic_note.render(_item())
    assert vic_note.merge(None, doc) == doc


def test_merge_preserves_text_written_after_the_end_marker():
    _, first = vic_note.render(_item())
    annotated = first + "\n## My notes\n\nI bought this.\n"
    _, second = vic_note.render(_item(comments=_COMMENTS))
    merged = vic_note.merge(annotated, second)
    assert "## My notes" in merged
    assert "I bought this." in merged


def test_merge_refreshes_the_generated_region():
    _, first = vic_note.render(_item())
    annotated = first + "\n## My notes\n\nI bought this.\n"
    _, second = vic_note.render(_item(comments=_COMMENTS))
    merged = vic_note.merge(annotated, second)
    assert "## Discussion" in merged
    assert _frontmatter(merged)["comment_count"] == "2"


def test_merge_is_idempotent():
    _, doc = vic_note.render(_item())
    assert vic_note.merge(vic_note.merge(None, doc), doc) == doc


def test_merge_replaces_file_lacking_markers():
    _, doc = vic_note.render(_item())
    assert vic_note.merge("hand written, no markers\n", doc) == doc
