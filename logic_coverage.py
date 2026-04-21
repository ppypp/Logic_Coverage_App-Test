"""
Logic Coverage Criteria Engine
================================
Supports operators matching the Offutt companion site:
  !   NOT
  &   AND  (also &&)
  |   OR   (also ||)
  >   Implication
  ^   Exclusive Or
  =   Equivalence

Operator precedence (high → low): ! > & > | > ^ > > > =
"""

import itertools
import re


# ── Tokenizer ──────────────────────────────────────────────────────────────


def _tokenize(expr: str) -> list[str]:
    """Return a flat list of tokens: variable-names, operators, parentheses."""
    tokens: list[str] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
        elif c == '&':
            tokens.append('&')
            i += 2 if i + 1 < n and expr[i + 1] == '&' else 1
        elif c == '|':
            tokens.append('|')
            i += 2 if i + 1 < n and expr[i + 1] == '|' else 1
        elif c in ('!', '>', '^', '=', '(', ')'):
            tokens.append(c)
            i += 1
        elif c.isalpha() or c == '_':
            j = i
            while j < n and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            tokens.append(expr[i:j])
            i = j
        else:
            raise ValueError(f"Invalid character {c!r} at position {i}")
    return tokens


# ── Recursive-Descent Parser ───────────────────────────────────────────────


_OPERATORS = frozenset({'!', '&', '|', '>', '^', '=', '(', ')'})


class _Parser:
    """Evaluate a tokenized boolean expression given a variable assignment."""

    def __init__(self, tokens: list[str], assignments: dict[str, bool]):
        self.tokens = tokens
        self.pos = 0
        self.assignments = assignments

    def _peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self, expected: str | None = None) -> str:
        t = self.tokens[self.pos]
        if expected is not None and t != expected:
            raise ValueError(f"Expected {expected!r}, got {t!r}")
        self.pos += 1
        return t

    def parse(self) -> bool:
        result = self._equiv()
        if self.pos < len(self.tokens):
            raise ValueError(f"Unexpected token {self.tokens[self.pos]!r}")
        return result

    def _equiv(self) -> bool:            # lowest precedence: =
        left = self._impl()
        while self._peek() == '=':
            self._consume()
            right = self._impl()
            left = (left == right)
        return left

    def _impl(self) -> bool:             # >  right-associative
        left = self._xor()
        if self._peek() == '>':
            self._consume()
            right = self._impl()         # right-recursive for right-assoc
            return (not left) or right
        return left

    def _xor(self) -> bool:              # ^
        left = self._or()
        while self._peek() == '^':
            self._consume()
            right = self._or()
            left = left != right
        return left

    def _or(self) -> bool:               # |
        left = self._and()
        while self._peek() == '|':
            self._consume()
            right = self._and()
            left = left or right
        return left

    def _and(self) -> bool:              # &
        left = self._not()
        while self._peek() == '&':
            self._consume()
            right = self._not()
            left = left and right
        return left

    def _not(self) -> bool:              # !  right-associative / prefix
        if self._peek() == '!':
            self._consume()
            return not self._not()
        return self._atom()

    def _atom(self) -> bool:
        t = self._peek()
        if t is None:
            raise ValueError("Unexpected end of expression")
        if t == '(':
            self._consume()
            result = self._equiv()
            if self._peek() != ')':
                raise ValueError("Expected closing ')'")
            self._consume()
            return result
        if t in _OPERATORS:
            raise ValueError(f"Expected variable, got operator {t!r}")
        self._consume()
        if t not in self.assignments:
            raise ValueError(f"Unknown variable: {t!r}")
        return bool(self.assignments[t])


# ── Main Class ─────────────────────────────────────────────────────────────


class LogicCoverage:
    def __init__(self, predicate: str):
        self.predicate = predicate.strip()
        self.clauses: list[str] = []
        self._tokens: list[str] = []
        self._validate_and_parse()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _validate_and_parse(self):
        if not self.predicate:
            raise ValueError("Predicate cannot be empty")

        try:
            self._tokens = _tokenize(self.predicate)
        except ValueError:
            raise

        # Extract unique variable names (non-operator, non-paren tokens)
        seen: dict[str, None] = {}
        for t in self._tokens:
            if t not in _OPERATORS and not t.startswith('('):
                seen[t] = None
        self.clauses = list(seen.keys())

        if not self.clauses:
            raise ValueError("No clauses found in predicate")

        # Validate syntax by a full evaluation with all-True
        try:
            self._evaluate({c: True for c in self.clauses})
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Invalid predicate syntax: {exc}") from exc

    def _evaluate(self, assignments: dict[str, bool]) -> bool:
        parser = _Parser(list(self._tokens), assignments)
        return parser.parse()

    def _determines(self, clause: str, assignments: dict[str, bool]) -> bool:
        """True iff flipping *clause* changes the predicate's value."""
        flipped = dict(assignments)
        flipped[clause] = not assignments[clause]
        return self._evaluate(assignments) != self._evaluate(flipped)

    # ── Truth table ───────────────────────────────────────────────────────

    def generate_truth_table(self) -> list[dict]:
        """All 2^n assignments in lexicographic (F→T) order per clause."""
        table = []
        for values in itertools.product([False, True], repeat=len(self.clauses)):
            assignments = dict(zip(self.clauses, values))
            table.append({"assignments": assignments, "result": self._evaluate(assignments)})
        return table

    # ── Predicate Coverage (PC) ───────────────────────────────────────────

    def predicate_coverage(self) -> dict:
        """Return the first row where p=True and the first where p=False."""
        true_test = false_test = None
        for row in self.generate_truth_table():
            if row["result"] and true_test is None:
                true_test = dict(row["assignments"])
            if not row["result"] and false_test is None:
                false_test = dict(row["assignments"])
        return {"true": true_test, "false": false_test}

    # ── Clause Coverage (CC) ──────────────────────────────────────────────

    def clause_coverage(self) -> dict:
        """For each clause, one test where it is True and one where False."""
        result = {c: {"true": None, "false": None} for c in self.clauses}
        for row in self.generate_truth_table():
            for c in self.clauses:
                if row["assignments"][c] and result[c]["true"] is None:
                    result[c]["true"] = dict(row["assignments"])
                if not row["assignments"][c] and result[c]["false"] is None:
                    result[c]["false"] = dict(row["assignments"])
        return result

    # ── Combinatorial Coverage (CoC) ──────────────────────────────────────

    def combinatorial_coverage(self) -> list[dict]:
        """All 2^n combinations — identical to the full truth table."""
        return self.generate_truth_table()

    # ── GACC ──────────────────────────────────────────────────────────────

    def gacc(self) -> dict:
        """
        General Active Clause Coverage.
        For each clause c: one test where c=T and c determines p,
        one test where c=F and c determines p.
        Minor clause values may differ between the two tests.
        """
        result = {}
        for c in self.clauses:
            true_test = false_test = None
            for row in self.generate_truth_table():
                if self._determines(c, row["assignments"]):
                    if row["assignments"][c] and true_test is None:
                        true_test = dict(row["assignments"])
                    if not row["assignments"][c] and false_test is None:
                        false_test = dict(row["assignments"])
            result[c] = {"true": true_test, "false": false_test}
        return result

    # ── CACC ──────────────────────────────────────────────────────────────

    def cacc(self) -> dict:
        """
        Correlated Active Clause Coverage.
        Like GACC but the predicate must evaluate to different values in
        the true-test and the false-test.
        """
        result = {}
        for c in self.clauses:
            table = self.generate_truth_table()
            true_cands  = [r for r in table if     r["assignments"][c] and self._determines(c, r["assignments"])]
            false_cands = [r for r in table if not r["assignments"][c] and self._determines(c, r["assignments"])]

            found = None
            for tr in true_cands:
                for fr in false_cands:
                    if tr["result"] != fr["result"]:
                        found = {"true": dict(tr["assignments"]), "false": dict(fr["assignments"])}
                        break
                if found:
                    break
            result[c] = found or {"true": None, "false": None}
        return result

    # ── RACC ──────────────────────────────────────────────────────────────

    def racc(self) -> dict:
        """
        Restricted Active Clause Coverage.
        For each clause c: find a minor-clause assignment such that c
        determines p.  The test pair shares that assignment; only c differs.
        (p automatically differs in the pair because c determines p.)
        """
        result = {}
        for c in self.clauses:
            found = None
            for row in self.generate_truth_table():
                if row["assignments"][c] and self._determines(c, row["assignments"]):
                    true_a  = dict(row["assignments"])
                    false_a = dict(row["assignments"])
                    false_a[c] = False
                    found = {"true": true_a, "false": false_a}
                    break
            result[c] = found or {"true": None, "false": None}
        return result

    # ── GICC ──────────────────────────────────────────────────────────────

    def gicc(self) -> dict:
        """
        General Inactive Clause Coverage.
        For each clause c: one test where c=T and c does NOT determine p,
        one test where c=F and c does NOT determine p.
        Minor clause values may differ between the two tests.
        """
        result = {}
        for c in self.clauses:
            true_test = false_test = None
            for row in self.generate_truth_table():
                if not self._determines(c, row["assignments"]):
                    if row["assignments"][c] and true_test is None:
                        true_test = dict(row["assignments"])
                    if not row["assignments"][c] and false_test is None:
                        false_test = dict(row["assignments"])
            result[c] = {"true": true_test, "false": false_test}
        return result

    # ── RICC ──────────────────────────────────────────────────────────────

    def ricc(self) -> dict:
        """
        Restricted Inactive Clause Coverage.
        Like GICC but minor clauses must have the same values in both tests.
        Find a minor-clause assignment where c is inactive; the pair differs
        only in c.
        """
        result = {}
        for c in self.clauses:
            found = None
            for row in self.generate_truth_table():
                if row["assignments"][c] and not self._determines(c, row["assignments"]):
                    true_a  = dict(row["assignments"])
                    false_a = dict(row["assignments"])
                    false_a[c] = False
                    found = {"true": true_a, "false": false_a}
                    break
            result[c] = found or {"true": None, "false": None}
        return result
