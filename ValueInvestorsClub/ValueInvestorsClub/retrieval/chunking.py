from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceChunkDraft:
    section_type: str
    content: str
    citation_ids: list[str] = field(default_factory=list)
    citation_urls: list[str] = field(default_factory=list)
    company_id: str | None = None
    security_id: str | None = None
    investor_id: str | None = None


def _citation_ids(row: dict[str, Any], fallback: str) -> list[str]:
    return [str(row.get("citation_id") or fallback)]


def _citation_urls(row: dict[str, Any]) -> list[str]:
    url = row.get("citation_url")
    return [str(url)] if url else []


def build_company_chunks(data: dict[str, Any]) -> list[EvidenceChunkDraft]:
    company = data["company"]
    company_id = str(company["id"])
    ideas = data.get("ideas", [])
    ownership = data.get("ownership", [])
    fallback_citation = f"company:{company_id}"
    chunks = [
        EvidenceChunkDraft(
            section_type="metadata",
            content=(
                f"{company['name']} metadata. Securities: "
                + ", ".join(str(item.get("ticker")) for item in data.get("securities", []))
            ),
            citation_ids=[
                str(
                    next(
                        (item.get("citation_id") for item in ideas + ownership if item.get("citation_id")),
                        fallback_citation,
                    )
                )
            ],
            citation_urls=[
                str(
                    item["citation_url"]
                )
                for item in ideas + ownership
                if item.get("citation_url")
            ][:1],
            company_id=company_id,
        )
    ]
    for row in ideas:
        chunks.append(
            EvidenceChunkDraft(
                section_type="ideas",
                content=str(row.get("text", "")),
                citation_ids=_citation_ids(row, fallback_citation),
                citation_urls=_citation_urls(row),
                company_id=company_id,
            )
        )
    for row in ownership:
        chunks.append(
            EvidenceChunkDraft(
                section_type="ownership",
                content=str(row.get("text", "")),
                citation_ids=_citation_ids(row, fallback_citation),
                citation_urls=_citation_urls(row),
                company_id=company_id,
                security_id=row.get("security_id"),
                investor_id=row.get("investor_id"),
            )
        )
    return chunks
