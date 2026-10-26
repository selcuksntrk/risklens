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
