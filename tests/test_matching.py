from techdd_scan.matching import Finding, Target, category_matches, match, summarise

PLANTED = [
    Target("P1", "a.py", [10], "sql_injection", "critical"),
    Target("P2", "a.py", [30], "weak_crypto", "high"),
    Target("P3", "b.js", [5], "xss", "high"),
]
DECOYS = [Target("D1", "a.py", [50], lure="sql_injection")]


def f(i, path, s, e, text):
    return Finding(i, path, s, e, text.lower(), text)


def test_exact_and_window_match():
    res = match([f(0, "a.py", 10, 10, "SQL injection via f-string"),
                 f(1, "a.py", 33, 33, "MD5 is weak for passwords")], PLANTED, DECOYS)
    assert res.detected == {"P1": 0, "P2": 1}


def test_outside_window_is_not_matched():
    res = match([f(0, "a.py", 14, 14, "SQL injection")], PLANTED, DECOYS)
    assert res.detected == {} and res.unplanted == [0]


def test_range_covering_target_matches():
    res = match([f(0, "a.py", 2, 20, "sql built by concatenation")], PLANTED, DECOYS)
    assert "P1" in res.detected


def test_wrong_file_never_matches():
    res = match([f(0, "c.py", 10, 10, "SQL injection")], PLANTED, DECOYS)
    assert not res.detected


def test_duplicate_counted_once():
    fs = [f(0, "b.js", 5, 5, "XSS via innerHTML"), f(1, "b.js", 6, 6, "innerHTML unsanitised")]
    res = match(fs, PLANTED, DECOYS)
    assert res.detected == {"P3": 0} and res.duplicates == [1]
    s = summarise(fs, PLANTED, DECOYS, res)
    assert s["planted_detected"] == 1 and s["true_positive_findings"] == 2 and s["duplicate_findings"] == 1
    assert s["precision_strict"] == 1.0


def test_near_miss_when_category_differs():
    res = match([f(0, "a.py", 10, 10, "Consider adding type hints")], PLANTED, DECOYS)
    assert res.near_miss == {0: ["P1"]} and not res.detected


def test_decoy_false_positive():
    fs = [f(0, "a.py", 51, 51, "Possible SQL injection here")]
    res = match(fs, PLANTED, DECOYS)
    assert res.decoy_fp == {0: "D1"}
    s = summarise(fs, PLANTED, DECOYS, res)
    assert s["decoy_false_positives"] == 1 and s["precision_strict"] == 0.0


def test_recall_by_severity():
    fs = [f(0, "a.py", 10, 10, "SQL injection")]
    res = match(fs, PLANTED, DECOYS)
    s = summarise(fs, PLANTED, DECOYS, res)
    assert s["by_severity"]["critical"] == {"planted": 1, "detected": 1}
    assert s["by_severity"]["high"] == {"planted": 2, "detected": 0}
    assert s["recall"] == round(1 / 3, 4)


def test_category_patterns():
    assert category_matches("open_redirect", "unvalidated redirect target")
    assert not category_matches("open_redirect", "sql injection")


def test_decoy_non_lure_comment_is_unplanted_not_decoy_fp():
    res = match([f(0, "a.py", 50, 50, "Add a docstring")], PLANTED, DECOYS)
    assert res.decoy_fp == {} and res.unplanted == [0]


def test_one_finding_can_credit_two_issues():
    planted = [Target("S1", "c.py", [10], "hardcoded_secret", "high"),
               Target("S2", "c.py", [12], "hardcoded_secret", "high")]
    res = match([f(0, "c.py", 9, 13, "Hardcoded secrets in source code")], planted, [])
    assert set(res.detected) == {"S1", "S2"} and res.duplicates == []


def test_related_location_in_other_file():
    planted = [Target("R1", "db.py", [5], "sql_injection", "high", extra={"routes.py": [20]})]
    res = match([f(0, "routes.py", 21, 21, "user-controlled ORDER BY enables SQL injection")], planted, [])
    assert res.detected == {"R1": 0}


def test_loose_keyword_does_not_credit_sensitive_logging():
    planted = [Target("L1", "p.py", [42], "sensitive_logging", "medium")]
    res = match([f(0, "p.py", 42, 42, "Eager f-string formatting in logging call defeats lazy evaluation")], planted, [])
    assert res.detected == {} and res.near_miss == {0: ["L1"]}
    res = match([f(0, "p.py", 42, 42, "The full card number is written to the log")], planted, [])
    assert res.detected == {"L1": 0}
