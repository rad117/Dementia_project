from ml.nlp.annotate import annotate_transcript_segments


def _segment(text, start=0.0, end=1.0):
    return {"text": text, "start": start, "end": end, "avg_logprob": -0.2, "words": []}


def test_annotate_tags_filler_segment():
    result = annotate_transcript_segments([_segment("um")])

    assert result[0]["type"] == "filler"


def test_annotate_tags_revision_segment():
    result = annotate_transcript_segments([_segment("the jar, I mean, the cookie jar")])

    assert result[0]["type"] == "revision"


def test_annotate_tags_repetition_segment():
    segments = [_segment("the boy is running fast", 0.0, 1.0), _segment("the boy is jumping", 1.0, 2.0)]

    result = annotate_transcript_segments(segments)

    assert result[1]["type"] == "repetition"


def test_annotate_tags_concept_segment():
    result = annotate_transcript_segments([_segment("the mother is washing dishes at the sink")])

    assert result[0]["type"] == "concept"
    assert result[0]["concept"] in {"mother", "dishes", "sink"}


def test_annotate_tags_normal_segment():
    result = annotate_transcript_segments([_segment("nothing relevant is happening here today")])

    assert result[0]["type"] == "normal"
    assert "concept" not in result[0]


def test_annotate_assigns_sequential_local_ids():
    result = annotate_transcript_segments([_segment("one"), _segment("two")])

    assert [s["id"] for s in result] == ["seg-0", "seg-1"]
