from ValueInvestorsClub.ValueInvestorsClub.retrieval.ranking import reciprocal_rank_fusion


def test_rrf_combines_keyword_and_vector_ranks():
    result = reciprocal_rank_fusion(
        keyword_ids=["a", "b"],
        vector_ids=["b", "c"],
        k=60,
    )

    assert result[0].chunk_id == "b"
