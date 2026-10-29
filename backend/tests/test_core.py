from app.hazards import risk_score
from app.media import pick_keyframes
from app.meta.sam import Track, parse_boxes, sam_cost
from app.report.marks import assign_marks, box_near

SAMPLE = ("<0f>0<|box;x1=10;y1=20;x2=110;y2=220;w=1280;h=720|><|mask;x=0;y=0;data=!abc|>,"
          "1<|box;x1=5;y1=5;x2=50;y2=50;w=1280;h=720|><|mask;x=0;y=0;data=!def|>\n"
          "<1f>0<|box;x1=12;y1=22;x2=112;y2=222;w=1280;h=720|><|mask;x=0;y=0;data=!ghi|>\n")


def test_parse_boxes_reads_frames_ids_and_media():
    tracks, media = parse_boxes(SAMPLE)
    assert media == {"width": 1280, "height": 720}
    assert tracks["0"] == {0: [10, 20, 110, 220], 1: [12, 22, 112, 222]}
    assert tracks["1"] == {0: [5, 5, 50, 50]}


def test_parse_boxes_empty_is_no_match():
    assert parse_boxes("") == ({}, {})


def test_sam_cost_has_50_frame_minimum():
    assert sam_cost(10) == sam_cost(50) == 50 * 0.2 / 1000


def test_marks_rank_by_track_length_and_box_near_tolerates_gaps():
    short = Track("lamp", "0", {0: [0, 0, 1, 1]})
    long = Track("bookshelf", "0", {f: [0, 0, 2, 2] for f in (0, 1, 2, 5)})
    marks = assign_marks([short, long])
    assert marks["1"].key == "bookshelf#0" and marks["2"].key == "lamp#0"
    assert box_near(long, 4) == [0, 0, 2, 2]      # nearest within 2 frames
    assert box_near(short, 9) is None


def test_keyframes_are_spread_and_in_range():
    assert pick_keyframes(300, 6) == [25, 75, 125, 175, 225, 275]
    assert pick_keyframes(3, 6) == [0, 1, 2]


def test_risk_score_grows_without_saturating():
    assert risk_score([]) == 0
    assert risk_score([{"severity": "low"}, {"severity": "medium"}]) == 32
    assert risk_score([{"severity": "medium"}] * 5) == 76
    assert risk_score([{"severity": "high"}] * 4) == 91


def test_fema_lookup_returns_known_sections_and_flags_unknown():
    from app.agents.fixer import fema_lookup
    out = fema_lookup(["6.5.2.1", "9.9.9"])
    assert [s["id"] for s in out["sections"]] == ["6.5.2.1"] and out["unknown_ids"] == ["9.9.9"]
    assert out["sections"][0]["mitigation"]
    assert [s["id"] for s in fema_lookup(["6.5.2.1 Bookshelves", "§6.5.6.3"])["sections"]] == ["6.5.2.1", "6.5.6.3"]


def test_best_frames_prefers_big_spread_out_boxes():
    from app.verify import best_frames
    t = Track("bookshelf", "0", {f: [0, 0, f, f] for f in range(1, 21)})
    assert [f for f, _ in best_frames([t], 3)] == [10, 15, 20]


def test_verify_guard_needs_sam_evidence_for_fixed():
    from app.verify import apply_guard
    claim = {"verdict": "fixed", "confidence": "high", "what_changed": "panel removed", "boxed_is_same_object": "yes"}
    assert apply_guard(claim, object_found=False)["verdict"] == "cannot_verify"
    assert apply_guard(claim, object_found=True)["verdict"] == "fixed"
    assert apply_guard({**claim, "boxed_is_same_object": "no"}, object_found=True)["verdict"] == "cannot_verify"
    assert apply_guard({**claim, "verdict": "not_fixed"}, object_found=False)["verdict"] == "not_fixed"


def test_proxy_is_trimmed_to_max_seconds(tmp_path):
    from app.media import ffmpeg, make_proxy, probe
    src = tmp_path / "long.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=10", "-pix_fmt", "yuv420p", str(src))
    proxy = make_proxy(src, tmp_path / "proxy.mp4", max_seconds=2)
    assert probe(proxy)["duration_s"] <= 2.2


def test_spark_json_retries_a_cut_off_answer_with_more_budget():
    import asyncio
    from types import SimpleNamespace
    from app.meta.spark import spark_json
    budgets = []

    async def create(**kwargs):
        budgets.append(kwargs["max_output_tokens"])
        status = "incomplete" if len(budgets) == 1 else "completed"
        return SimpleNamespace(status=status, usage=None, output=[], output_text='{"ok": true}',
                               incomplete_details=SimpleNamespace(reason="max_output_tokens"))
    api = SimpleNamespace(responses=SimpleNamespace(create=create))
    out, _ = asyncio.run(spark_json(api, [], {}, "t", instructions="", max_tokens=100))
    assert out == {"ok": True} and budgets == [100, 200]


def test_chain_retries_a_lagging_previous_response(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    import httpx
    from openai import BadRequestError
    from app.meta import spark
    calls = []

    async def create(**kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise BadRequestError("not yet", response=httpx.Response(400, request=httpx.Request("POST", "http://x")),
                                  body=None)
        return "ok"
    async def no_wait(_):
        return None
    monkeypatch.setattr(spark.asyncio, "sleep", no_wait)
    api = SimpleNamespace(responses=SimpleNamespace(create=create))
    assert asyncio.run(spark.chain(api)) == "ok" and len(calls) == 3


def test_parse_boxes_ignores_frame_markers_inside_mask_payloads():
    text = ("<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=10;h=10|><|mask;x=0;y=0;data=!a<12f>Qz~|>,"
            "1<|box;x1=5;y1=5;x2=6;y2=6;w=10;h=10|><|mask;x=0;y=0;data=!b|>\n"
            "<1f>0<|box;x1=1;y1=2;x2=3;y2=5;w=10;h=10|><|mask;x=0;y=0;data=!c|>\n")
    tracks, _ = parse_boxes(text)
    assert tracks == {"0": {0: [1, 2, 3, 4], 1: [1, 2, 3, 5]}, "1": {0: [5, 5, 6, 6]}}


def test_sam_backoff_honours_retry_after_and_caps():
    from app.meta.sam import backoff
    assert backoff(0, "3") == 3 and backoff(0, "60") == 10
    assert 0.5 <= backoff(0, None) <= 1.0 and 2 <= backoff(2, None) <= 2.5


def test_sam_does_not_retry_a_bad_request(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    import httpx
    from openai import BadRequestError
    from app.meta.sam import track_concept
    calls = []

    async def create(**kwargs):
        calls.append(1)
        raise BadRequestError("bad concept", response=httpx.Response(400, request=httpx.Request("POST", "http://x")),
                              body=None)
    api = SimpleNamespace(responses=SimpleNamespace(create=create))
    result = asyncio.run(track_concept(api, "file", "lamp"))
    assert len(calls) == 1 and result.status == "error" and result.tracks == []
