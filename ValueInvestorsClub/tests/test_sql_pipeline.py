from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scrapy.exceptions import DropItem

from ValueInvestorsClub.ValueInvestorsClub.models import (
    Base,
    Catalysts,
    Comment,
    Company,
    Description,
    Idea,
    Photo,
    User,
)
from ValueInvestorsClub.ValueInvestorsClub.models.ingestion import IngestionRun
from ValueInvestorsClub.ValueInvestorsClub.items import ValueinvestorsclubItem
from ValueInvestorsClub.ValueInvestorsClub.pipelines import SqlPipeline


def _spider():
    return SimpleNamespace(
        source="valueinvestorsclub", parser_version="idea-pipeline-v1"
    )


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

    spider = _spider()
    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        idea = session.query(Idea).one()
        assert run.source == "valueinvestorsclub"
        assert run.target == "ideas"
        assert run.parser_version == "idea-pipeline-v1"
        assert run.rows_seen == 1
        assert run.rows_accepted == 1
        assert run.rows_rejected == 0
        assert run.status == "complete"
        assert idea.ingestion_run_id == run.id
        assert idea.link == item["link"]
        assert session.query(Description).count() == 1
        assert session.query(Catalysts).count() == 1

        comments = session.query(Comment).all()
        assert len(comments) == 2
        assert {c.author for c in comments} == {"johnsmith", "janedoe"}

        photos = session.query(Photo).all()
        assert len(photos) == 2
        assert {p.url for p in photos} == set(item["photos"])


def test_sql_pipeline_spider_closed_signal_records_reason_after_pipeline_close():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = SqlPipeline.__new__(SqlPipeline)
    pipeline.engine = engine
    spider = _spider()

    pipeline.open_spider(spider)
    pipeline.close_spider(spider)
    pipeline._on_spider_closed(spider, reason="shutdown")

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.status == "failed"
        assert run.error_message == "shutdown"


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

    spider = _spider()
    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        assert session.query(Comment).count() == 0
        assert session.query(Photo).count() == 0


def test_sql_pipeline_uses_scrapy_finish_reason_when_reason_is_omitted():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = SqlPipeline.__new__(SqlPipeline)
    pipeline.engine = engine
    stats = SimpleNamespace(
        get_value=lambda key: "fatal parser error" if key == "finish_reason" else None
    )
    spider = SimpleNamespace(
        source="valueinvestorsclub",
        parser_version="idea-pipeline-v1",
        crawler=SimpleNamespace(stats=stats),
    )
    item = ValueinvestorsclubItem(
        ticker="ACME",
        link="https://www.valueinvestorsclub.com/idea/Acme/4",
        companyName="Acme Corp",
        date="January 28, 2020 - 3:56pm EST",
        username="janedoe",
        userLink="/member/janedoe",
        isShort=False,
        isContestWinner=False,
        description="Acme is a great business.",
        catalysts="New product launch.",
    )

    pipeline.open_spider(spider)
    pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.status == "failed"
        assert run.error_message == "fatal parser error"


def test_rejected_vic_item_is_counted_without_public_side_effects():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = SqlPipeline.__new__(SqlPipeline)
    pipeline.engine = engine
    spider = _spider()
    pipeline.open_spider(spider)

    with pytest.raises(DropItem, match="missing ticker"):
        pipeline.process_item({"parse_error": "missing ticker"}, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.rows_seen == 1
        assert run.rows_accepted == 0
        assert run.rows_rejected == 1
        assert run.status == "partial"
        assert run.error_message == "missing ticker"
        assert session.query(Idea).count() == 0
        assert session.query(Company).count() == 0
        assert session.query(User).count() == 0
        assert session.query(Description).count() == 0
        assert session.query(Catalysts).count() == 0
        assert session.query(Comment).count() == 0
        assert session.query(Photo).count() == 0


def test_failed_vic_item_rolls_back_the_whole_item_transaction():
    engine = create_engine("sqlite:///:memory:")
    Base.Base.metadata.create_all(engine)

    pipeline = SqlPipeline.__new__(SqlPipeline)
    pipeline.engine = engine
    spider = _spider()
    pipeline.open_spider(spider)
    item = ValueinvestorsclubItem(
        ticker="ACME",
        link="https://www.valueinvestorsclub.com/idea/Acme/3",
        companyName="Acme Corp",
        date="January 28, 2020 - 3:56pm EST",
        username="janedoe",
        userLink="/member/janedoe",
        isShort=False,
        isContestWinner=False,
        description=None,
        catalysts="New product launch.",
    )

    with pytest.raises(IntegrityError):
        pipeline.process_item(item, spider)
    pipeline.close_spider(spider)

    with Session(engine) as session:
        run = session.query(IngestionRun).one()
        assert run.rows_seen == 1
        assert run.rows_accepted == 0
        assert run.rows_rejected == 1
        assert run.status == "partial"
        assert run.error_message
        assert session.query(Idea).count() == 0
        assert session.query(Description).count() == 0
        assert session.query(Catalysts).count() == 0
        assert session.query(Comment).count() == 0
        assert session.query(Photo).count() == 0
