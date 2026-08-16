# Investment Data Context

Domain glossary for source ingestion, identity curation, holding history, and future company-centered retrieval.

## Language

**Investor**:
The reviewed canonical reporting fund or investing institution exposed to curated APIs and retrieval.
_Avoid_: treating a portfolio manager's name as the owner of every reported holding.

**Portfolio manager**:
An optional person associated with an Investor by source metadata, stored separately from the reporting fund identity.
_Avoid_: concatenating manager and fund names into one Investor identity.

**Source investor record**:
A website-specific representation of an investor, identified by `(source, source_key)` and preserved for provenance.
_Avoid_: merging source records by display name alone.

**Company**:
The reviewed canonical company-level subject that owns a company chapter and groups ideas, ownership, and events.
_Avoid_: using a raw ticker as the company identity.

**Security**:
A reviewed tradable instrument associated with one Company, identified by ticker, exchange, share class, or other market identifier.
_Avoid_: treating ticker spelling as proof of a distinct Company.

**Source company record**:
A website-specific ticker/name representation preserved as an alias candidate until mapped to a reviewed Security and Company.
_Avoid_: assuming `BRK.B` and `BRK-B` are different companies or merging them without evidence.

**Holding snapshot**:
A source-observed investor position for one company/security and reporting period, including shares, value, portfolio percentage, and source activity.
_Avoid_: calling a snapshot a buy/sell event.

**Holding event**:
A derived transition between ordered holding snapshots, such as open, add, reduce, hold, exit, or unknown, with evidence and confidence.
_Avoid_: inferring an exit solely from a missing row.

**Source evidence**:
Immutable fetched content and fetch metadata that supports a parsed or curated fact.
_Avoid_: treating parser output without source evidence as authoritative.

**Curated data**:
Validated facts whose source identities have approved canonical mappings and which are eligible for public APIs and retrieval.
_Avoid_: exposing staging, unresolved, or quarantined rows as curated data.

**Quarantine record**:
Rejected, incomplete, malformed, or unresolved source material retained for human review and excluded from curated data.
_Avoid_: silently discarding or silently promoting it.

**Company chapter**:
A future retrieval parent document for one curated Company, initially containing curated VIC ideas, investor ownership timelines/events, and company/security metadata in typed, time-bounded sections.
_Avoid_: embedding raw mixed-source pages as undifferentiated company context.

**Retrieval feedback loop**:
Evaluation records linking a query, retrieved sections, citations, ranking signals, and human usefulness labels to improve retrieval without changing curated facts. Any generated answer is transient evaluation context, not a persisted domain fact.
_Avoid_: treating feedback as automatic model training or permission to rewrite source data.

**Entity resolution**:
The process of mapping source investor/company records to canonical curated entities using deterministic candidates, model suggestions, and human approval.
_Avoid_: allowing an LLM to merge entities without approval.

## Relationships

- A **Source investor record** may map to zero or one curated **Investor** at a time.
- A source may associate a **Portfolio manager** with an **Investor** without changing the Investor identity.
- A **Source company record** may map to zero or one curated **Security**, which belongs to one curated **Company**.
- A **Holding snapshot** references one source investor record, one source company/security record, one period, and one source evidence record.
- A curated **Holding snapshot** references approved canonical **Investor** and **Security** identities while retaining source provenance.
- A **Holding event** is derived from one or more ordered **Holding snapshots** and never replaces them.
- A **Company** may own multiple **Securities**, such as share classes or exchange listings.
- A **Company chapter** contains only curated evidence sections.
- A **Retrieval feedback loop** evaluates retrieval results and agent answers without mutating curated data.
- A **Quarantine record** may be reviewed and reprocessed, but cannot be read by public APIs or retrieval.

## Example dialogue

> **Dev:** "Dataroma says BRK.B and HedgeFollow says BRK-B. Are these two Companies?"
>
> **Domain expert:** "They are two Source company records. Resolve them to one Company only after identifier and evidence review; preserve both aliases and source links."
>
> **Dev:** "Dataroma shows 120 shares in 2026 Q2 and HedgeFollow shows 118. Which Holding snapshot is correct?"
>
> **Domain expert:** "Keep both source observations with provenance. Do not overwrite one with the other; a later curated view may reconcile the conflict explicitly."

## Flagged ambiguities

- Source coverage may not provide a stable exchange/security identifier for every ticker. Such records require a review status rather than automatic Company/Security assignment.
- **Investor** now means canonical reviewed entity; source-specific rows must be called **Source investor records**.
- **Event** means derived historical transition; source strings such as `Buy`, `Add`, and `Reduce` are source activity values.
