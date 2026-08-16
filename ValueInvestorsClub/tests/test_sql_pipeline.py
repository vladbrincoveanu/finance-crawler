from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ValueInvestorsClub.ValueInvestorsClub.models import Base, Comment, Photo, Description, Catalysts
from ValueInvestorsClub.ValueInvestorsClub.items import ValueinvestorsclubItem
from ValueInvestorsClub.ValueInvestorsClub.pipelines import SqlPipeline


def test_process_item_persists_comments_and_photos():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = SqlPipeline.__new__(SqlPipeline)
    pipeline.engine = engine

    item = ValueinvestorsclubItem(
        ticker="ACME",
        link="https://www.valueinvestorsclub.com/idea/Acme/1",
        companyName="Acme Corp",
        date="January 28, 2020 - 3:56pm EST",
        username="janedoe",
        userLink="/member/janedoe",
        isShort=False,
        isContestWinner=False,
        description="Acme is a great business.",
        catalysts="New product launch.",
        comments=[
            {"author": "johnsmith", "when": "2020-01-29", "text": "Great writeup."},
            {"author": "janedoe", "when": "2020-01-30", "text": "Nice catalyst detail."},
        ],
        photos=[
            "https://www.valueinvestorsclub.com/images/moat-chart.png",
            "https://cdn.valueinvestorsclub.com/images/product.jpg",
        ],
    )

    pipeline.process_item(item)

    with Session(engine) as session:
        assert session.query(Description).count() == 1
        assert session.query(Catalysts).count() == 1

        comments = session.query(Comment).all()
        assert len(comments) == 2
        assert {c.author for c in comments} == {"johnsmith", "janedoe"}

        photos = session.query(Photo).all()
        assert len(photos) == 2
        assert {p.url for p in photos} == set(item["photos"])


def test_process_item_handles_missing_comments_and_photos():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = SqlPipeline.__new__(SqlPipeline)
    pipeline.engine = engine

    item = ValueinvestorsclubItem(
        ticker="ACME",
        link="https://www.valueinvestorsclub.com/idea/Acme/2",
        companyName="Acme Corp",
        date="January 28, 2020 - 3:56pm EST",
        username="janedoe",
        userLink="/member/janedoe",
        isShort=False,
        isContestWinner=False,
        description="Acme is a great business.",
        catalysts="New product launch.",
    )

    pipeline.process_item(item)

    with Session(engine) as session:
        assert session.query(Comment).count() == 0
        assert session.query(Photo).count() == 0
