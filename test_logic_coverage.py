"""
Logic Coverage Criteria – TDD Test Suite
=========================================
Written BEFORE the implementation (test-first).

Operators (matching Offutt site):
  !   NOT
  &   AND        (also accepts &&)
  |   OR         (also accepts ||)
  >   Implication
  ^   Exclusive Or (XOR)
  =   Equivalence

Category Partition for the primary input (predicate string):
-------------------------------------------------------------------
  EMPTY          ""
  SINGLE         "a"
  BINARY_AND     "a & b"
  BINARY_OR      "a | b"
  NOT            "!a"
  IMPLICATION    "a > b"
  XOR            "a ^ b"
  EQUIV          "a = b"
  THREE_CLAUSES  "a & b | c"   (standard precedence: (a&b)|c)
  PARENS         "(a | b) & c"
  TAUTOLOGY      "a | !a"       (always True)
  CONTRADICTION  "a & !a"       (always False)
  INVALID        "a &&& b"

Coverage criteria tested: PC, CC, CoC, GACC, CACC, RACC, GICC, RICC
"""

import pytest
from logic_coverage import LogicCoverage


# ── Error / Validation Cases ─────────────────────────────────────────────────

def test_empty_predicate_raises():
    with pytest.raises(ValueError):
        LogicCoverage("")

def test_invalid_operator_raises():
    with pytest.raises(ValueError):
        LogicCoverage("a &&& b")

def test_no_clauses_raises():
    with pytest.raises(ValueError):
        LogicCoverage("&")

def test_unbalanced_parens_raises():
    with pytest.raises(ValueError):
        LogicCoverage("(a & b")


# ── Clause Parsing ───────────────────────────────────────────────────────────

def test_single_clause_parsed():
    lc = LogicCoverage("a")
    assert lc.clauses == ["a"]

def test_two_clauses_parsed():
    lc = LogicCoverage("a & b")
    assert set(lc.clauses) == {"a", "b"}
    assert len(lc.clauses) == 2

# NOT does not create extra clauses — "!a" has only clause "a"
def test_not_does_not_duplicate_clause():
    lc = LogicCoverage("!a")
    assert lc.clauses == ["a"]

# "a | !a" — only one distinct clause
def test_tautology_has_one_clause():
    lc = LogicCoverage("a | !a")
    assert lc.clauses == ["a"]

# Multi-character variable names
def test_multichar_variable_names():
    lc = LogicCoverage("foo & bar")
    assert set(lc.clauses) == {"foo", "bar"}

# && and || aliases are accepted (normalized to & and |)
def test_double_operator_aliases_accepted():
    lc = LogicCoverage("a && b")
    assert set(lc.clauses) == {"a", "b"}
    lc2 = LogicCoverage("a || b")
    assert set(lc2.clauses) == {"a", "b"}


# ── Truth Table Generation ───────────────────────────────────────────────────

def test_truth_table_single_has_2_rows():
    lc = LogicCoverage("a")
    tt = lc.generate_truth_table()
    assert len(tt) == 2
    assert any(r["result"] is True for r in tt)
    assert any(r["result"] is False for r in tt)

# "a & b": 4 rows; only (T,T) is True
def test_truth_table_and_shape():
    lc = LogicCoverage("a & b")
    tt = lc.generate_truth_table()
    assert len(tt) == 4
    true_rows = [r for r in tt if r["result"]]
    assert len(true_rows) == 1
    assert true_rows[0]["assignments"] == {"a": True, "b": True}

# "a | b": 4 rows; only (F,F) is False
def test_truth_table_or_shape():
    lc = LogicCoverage("a | b")
    tt = lc.generate_truth_table()
    assert len(tt) == 4
    false_rows = [r for r in tt if not r["result"]]
    assert len(false_rows) == 1
    assert false_rows[0]["assignments"] == {"a": False, "b": False}

# 3 clauses → 8 rows
def test_truth_table_three_clauses_has_8_rows():
    lc = LogicCoverage("a & b | c")
    tt = lc.generate_truth_table()
    assert len(tt) == 8

# "!a": result is the negation of a
def test_truth_table_not_negates():
    lc = LogicCoverage("!a")
    for row in lc.generate_truth_table():
        assert row["result"] == (not row["assignments"]["a"])

# "a | !a": always True
def test_truth_table_tautology_all_true():
    lc = LogicCoverage("a | !a")
    assert all(r["result"] for r in lc.generate_truth_table())

# "a & !a": always False
def test_truth_table_contradiction_all_false():
    lc = LogicCoverage("a & !a")
    assert all(not r["result"] for r in lc.generate_truth_table())

# Implication: a > b = !a | b
def test_truth_table_implication():
    lc = LogicCoverage("a > b")
    tt = lc.generate_truth_table()
    # Only False when a=T and b=F
    false_rows = [r for r in tt if not r["result"]]
    assert len(false_rows) == 1
    assert false_rows[0]["assignments"] == {"a": True, "b": False}

# XOR: a ^ b is True iff exactly one is True
def test_truth_table_xor():
    lc = LogicCoverage("a ^ b")
    for row in lc.generate_truth_table():
        a, b = row["assignments"]["a"], row["assignments"]["b"]
        assert row["result"] == (a != b)

# Equivalence: a = b is True iff both same
def test_truth_table_equivalence():
    lc = LogicCoverage("a = b")
    for row in lc.generate_truth_table():
        a, b = row["assignments"]["a"], row["assignments"]["b"]
        assert row["result"] == (a == b)

# "(a | b) & c": c=False always gives False
def test_truth_table_parens_c_false_gives_false():
    lc = LogicCoverage("(a | b) & c")
    tt = lc.generate_truth_table()
    assert len(tt) == 8
    c_false_rows = [r for r in tt if not r["assignments"]["c"]]
    assert all(not r["result"] for r in c_false_rows)


# ── _determines helper ───────────────────────────────────────────────────────

# a determines a&b iff b=T
def test_determines_and_a_with_b_true():
    lc = LogicCoverage("a & b")
    assert lc._determines("a", {"a": True,  "b": True})  is True
    assert lc._determines("a", {"a": False, "b": True})  is True

def test_determines_and_a_with_b_false():
    lc = LogicCoverage("a & b")
    assert lc._determines("a", {"a": True,  "b": False}) is False
    assert lc._determines("a", {"a": False, "b": False}) is False

# a determines a|b iff b=F
def test_determines_or_a_with_b_false():
    lc = LogicCoverage("a | b")
    assert lc._determines("a", {"a": True,  "b": False}) is True
    assert lc._determines("a", {"a": False, "b": False}) is True

def test_determines_or_a_with_b_true():
    lc = LogicCoverage("a | b")
    assert lc._determines("a", {"a": True,  "b": True})  is False
    assert lc._determines("a", {"a": False, "b": True})  is False

# Tautology: a never determines a | !a
def test_determines_tautology_never():
    lc = LogicCoverage("a | !a")
    assert lc._determines("a", {"a": True})  is False
    assert lc._determines("a", {"a": False}) is False


# ── Predicate Coverage (PC) ──────────────────────────────────────────────────

def test_pc_single_clause():
    lc = LogicCoverage("a")
    pc = lc.predicate_coverage()
    assert pc["true"] is not None and pc["true"]["a"] is True
    assert pc["false"] is not None and pc["false"]["a"] is False

def test_pc_and_true_is_tt():
    lc = LogicCoverage("a & b")
    pc = lc.predicate_coverage()
    assert pc["true"] == {"a": True, "b": True}
    assert pc["false"] is not None

def test_pc_tautology_no_false():
    lc = LogicCoverage("a | !a")
    pc = lc.predicate_coverage()
    assert pc["true"] is not None
    assert pc["false"] is None

def test_pc_contradiction_no_true():
    lc = LogicCoverage("a & !a")
    pc = lc.predicate_coverage()
    assert pc["true"] is None
    assert pc["false"] is not None


# ── Clause Coverage (CC) ─────────────────────────────────────────────────────

def test_cc_and_all_clauses_covered():
    lc = LogicCoverage("a & b")
    cc = lc.clause_coverage()
    for c in lc.clauses:
        assert cc[c]["true"]  is not None and cc[c]["true"][c]  is True
        assert cc[c]["false"] is not None and cc[c]["false"][c] is False

def test_cc_not_has_both():
    lc = LogicCoverage("!a")
    cc = lc.clause_coverage()
    assert cc["a"]["true"]  is not None and cc["a"]["true"]["a"]  is True
    assert cc["a"]["false"] is not None and cc["a"]["false"]["a"] is False


# ── Combinatorial Coverage (CoC) ─────────────────────────────────────────────

def test_coc_and_has_4_rows():
    lc = LogicCoverage("a & b")
    assert len(lc.combinatorial_coverage()) == 4

def test_coc_three_clauses_has_8_rows():
    lc = LogicCoverage("a & b | c")
    assert len(lc.combinatorial_coverage()) == 8

# CoC subsumes CC: every clause T and F value appears
def test_coc_subsumes_cc():
    lc = LogicCoverage("a & b")
    assignments = [r["assignments"] for r in lc.combinatorial_coverage()]
    for c in lc.clauses:
        assert any(a[c] is True  for a in assignments)
        assert any(a[c] is False for a in assignments)


# ── General Active Clause Coverage (GACC) ────────────────────────────────────

# a determines a&b only when b=T
def test_gacc_and_clause_a():
    lc = LogicCoverage("a & b")
    gacc = lc.gacc()
    assert gacc["a"]["true"]  == {"a": True,  "b": True}
    assert gacc["a"]["false"] == {"a": False, "b": True}

# b determines a&b only when a=T
def test_gacc_and_clause_b():
    lc = LogicCoverage("a & b")
    gacc = lc.gacc()
    assert gacc["b"]["true"]  == {"a": True, "b": True}
    assert gacc["b"]["false"] == {"a": True, "b": False}

# a determines a|b only when b=F
def test_gacc_or_clause_a():
    lc = LogicCoverage("a | b")
    gacc = lc.gacc()
    assert gacc["a"]["true"]  == {"a": True,  "b": False}
    assert gacc["a"]["false"] == {"a": False, "b": False}

# b determines a|b only when a=F
def test_gacc_or_clause_b():
    lc = LogicCoverage("a | b")
    gacc = lc.gacc()
    assert gacc["b"]["true"]  == {"a": False, "b": True}
    assert gacc["b"]["false"] == {"a": False, "b": False}

# Tautology: no clause ever determines predicate
def test_gacc_tautology_returns_none():
    lc = LogicCoverage("a | !a")
    gacc = lc.gacc()
    assert gacc["a"]["true"]  is None
    assert gacc["a"]["false"] is None

# Each returned GACC test actually determines the predicate
def test_gacc_tests_actually_determine():
    lc = LogicCoverage("a & b")
    gacc = lc.gacc()
    for c in lc.clauses:
        for which in ("true", "false"):
            test = gacc[c][which]
            if test:
                assert lc._determines(c, test), \
                    f"GACC {which}-test for {c} does not determine predicate: {test}"


# ── Correlated Active Clause Coverage (CACC) ─────────────────────────────────

def test_cacc_and_clause_a():
    lc = LogicCoverage("a & b")
    cacc = lc.cacc()
    assert cacc["a"]["true"]  == {"a": True,  "b": True}
    assert cacc["a"]["false"] == {"a": False, "b": True}

# Predicate outcomes must differ in each CACC pair
def test_cacc_and_outcomes_differ():
    lc = LogicCoverage("a & b")
    cacc = lc.cacc()
    for c in lc.clauses:
        if cacc[c]["true"] and cacc[c]["false"]:
            p_true  = lc._evaluate(cacc[c]["true"])
            p_false = lc._evaluate(cacc[c]["false"])
            assert p_true != p_false, f"CACC pair for {c}: predicate value same in both tests"

def test_cacc_or_outcomes_differ():
    lc = LogicCoverage("a | b")
    cacc = lc.cacc()
    for c in lc.clauses:
        if cacc[c]["true"] and cacc[c]["false"]:
            assert lc._evaluate(cacc[c]["true"]) != lc._evaluate(cacc[c]["false"])

def test_cacc_tautology_returns_none():
    lc = LogicCoverage("a | !a")
    cacc = lc.cacc()
    assert cacc["a"]["true"]  is None
    assert cacc["a"]["false"] is None


# ── Restricted Active Clause Coverage (RACC) ─────────────────────────────────

def test_racc_and_clause_a():
    lc = LogicCoverage("a & b")
    racc = lc.racc()
    assert racc["a"]["true"]  == {"a": True,  "b": True}
    assert racc["a"]["false"] == {"a": False, "b": True}

def test_racc_and_clause_b():
    lc = LogicCoverage("a & b")
    racc = lc.racc()
    assert racc["b"]["true"]  == {"a": True, "b": True}
    assert racc["b"]["false"] == {"a": True, "b": False}

def test_racc_or_clause_a():
    lc = LogicCoverage("a | b")
    racc = lc.racc()
    assert racc["a"]["true"]  == {"a": True,  "b": False}
    assert racc["a"]["false"] == {"a": False, "b": False}

def test_racc_or_clause_b():
    lc = LogicCoverage("a | b")
    racc = lc.racc()
    assert racc["b"]["true"]  == {"a": False, "b": True}
    assert racc["b"]["false"] == {"a": False, "b": False}

# Minor clauses must have the same values in both RACC tests
def test_racc_minor_clauses_same():
    lc = LogicCoverage("a & b")
    racc = lc.racc()
    for c in lc.clauses:
        t, f = racc[c]["true"], racc[c]["false"]
        if t and f:
            for other in lc.clauses:
                if other != c:
                    assert t[other] == f[other], \
                        f"RACC minor clause '{other}' differs for major '{c}'"

# RACC implies CACC: p must differ AND minor clauses must be same
def test_racc_implies_cacc():
    lc = LogicCoverage("a & b")
    racc = lc.racc()
    for c in lc.clauses:
        t, f = racc[c]["true"], racc[c]["false"]
        if t and f:
            assert lc._evaluate(t) != lc._evaluate(f)
            for other in lc.clauses:
                if other != c:
                    assert t[other] == f[other]

def test_racc_tautology_returns_none():
    lc = LogicCoverage("a | !a")
    racc = lc.racc()
    assert racc["a"]["true"]  is None
    assert racc["a"]["false"] is None


# ── General Inactive Clause Coverage (GICC) ──────────────────────────────────
# For each clause c_i: one test with c_i=T where c_i is INACTIVE (doesn't
# determine p), and one with c_i=F where c_i is also inactive.

# a is inactive in a&b when b=F (p stays False regardless of a)
def test_gicc_and_clause_a():
    lc = LogicCoverage("a & b")
    gicc = lc.gicc()
    assert gicc["a"]["true"]  == {"a": True,  "b": False}
    assert gicc["a"]["false"] == {"a": False, "b": False}

def test_gicc_and_clause_b():
    lc = LogicCoverage("a & b")
    gicc = lc.gicc()
    assert gicc["b"]["true"]  == {"a": False, "b": True}
    assert gicc["b"]["false"] == {"a": False, "b": False}

# a is inactive in a|b when b=T (p stays True regardless of a)
def test_gicc_or_clause_a():
    lc = LogicCoverage("a | b")
    gicc = lc.gicc()
    assert gicc["a"]["true"]  == {"a": True,  "b": True}
    assert gicc["a"]["false"] == {"a": False, "b": True}

# Each returned GICC test must NOT determine the predicate
def test_gicc_tests_are_actually_inactive():
    lc = LogicCoverage("a & b")
    gicc = lc.gicc()
    for c in lc.clauses:
        for which in ("true", "false"):
            test = gicc[c][which]
            if test:
                assert not lc._determines(c, test), \
                    f"GICC {which}-test for {c} actually determines predicate: {test}"

# Tautology: every test is inactive (a never determines a|!a)
def test_gicc_tautology_always_inactive():
    lc = LogicCoverage("a | !a")
    gicc = lc.gicc()
    assert gicc["a"]["true"]  is not None
    assert gicc["a"]["false"] is not None


# ── Restricted Inactive Clause Coverage (RICC) ───────────────────────────────
# Like GICC but minor clauses must have the same values in both tests.

def test_ricc_and_clause_a():
    lc = LogicCoverage("a & b")
    ricc = lc.ricc()
    assert ricc["a"]["true"]  == {"a": True,  "b": False}
    assert ricc["a"]["false"] == {"a": False, "b": False}

def test_ricc_or_clause_a():
    lc = LogicCoverage("a | b")
    ricc = lc.ricc()
    assert ricc["a"]["true"]  == {"a": True,  "b": True}
    assert ricc["a"]["false"] == {"a": False, "b": True}

# Minor clauses must be the same in both RICC tests
def test_ricc_minor_clauses_same():
    lc = LogicCoverage("a & b")
    ricc = lc.ricc()
    for c in lc.clauses:
        t, f = ricc[c]["true"], ricc[c]["false"]
        if t and f:
            for other in lc.clauses:
                if other != c:
                    assert t[other] == f[other], \
                        f"RICC minor clause '{other}' differs for major '{c}'"

# RICC tests must also be inactive (not determining)
def test_ricc_tests_are_inactive():
    lc = LogicCoverage("a & b")
    ricc = lc.ricc()
    for c in lc.clauses:
        for which in ("true", "false"):
            test = ricc[c][which]
            if test:
                assert not lc._determines(c, test), \
                    f"RICC {which}-test for {c} actually determines predicate: {test}"

def test_ricc_tautology():
    lc = LogicCoverage("a | !a")
    ricc = lc.ricc()
    assert ricc["a"]["true"]  is not None
    assert ricc["a"]["false"] is not None


# ── Subsumption Relationships ─────────────────────────────────────────────────

# CoC subsumes PC
def test_coc_subsumes_pc():
    lc = LogicCoverage("a & b")
    coc_results = [r["result"] for r in lc.combinatorial_coverage()]
    assert True  in coc_results
    assert False in coc_results

# RACC tests satisfy CACC requirements
def test_racc_tests_satisfy_cacc_requirements():
    lc = LogicCoverage("a & b")
    racc = lc.racc()
    for c in lc.clauses:
        t, f = racc[c]["true"], racc[c]["false"]
        if t and f:
            assert t[c] is True
            assert f[c] is False
            assert lc._evaluate(t) != lc._evaluate(f)
