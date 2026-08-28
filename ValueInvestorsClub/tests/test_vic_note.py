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
