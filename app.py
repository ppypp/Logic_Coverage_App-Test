from flask import Flask, render_template, request
from logic_coverage import LogicCoverage

app = Flask(__name__)


def _fmt(assignments: dict | None, clauses: list[str]) -> str | None:
    """Format an assignment dict as a human-readable string, or None."""
    if assignments is None:
        return None
    return "  ".join(
        f"{c}={'T' if assignments[c] else 'F'}" for c in clauses
    )


@app.route("/", methods=["GET", "POST"])
def index():
    predicate = ""
    action = None
    result = None
    error = None

    if request.method == "POST":
        predicate = request.form.get("predicate", "").strip()
        action = request.form.get("action", "truth_table")

        try:
            lc = LogicCoverage(predicate)
            clauses = lc.clauses
            tt = lc.generate_truth_table()

            result = {
                "clauses":  clauses,
                "truth_table": tt,
                "action":   action,
            }

            if action == "truth_table":
                pass  # tt already in result

            elif action == "pc":
                pc = lc.predicate_coverage()
                result["pc"] = {
                    "true":  _fmt(pc["true"],  clauses),
                    "false": _fmt(pc["false"], clauses),
                }

            elif action == "cc":
                cc = lc.clause_coverage()
                result["cc"] = {
                    c: {
                        "true":  _fmt(cc[c]["true"],  clauses),
                        "false": _fmt(cc[c]["false"], clauses),
                    }
                    for c in clauses
                }

            elif action == "coc":
                pass  # full truth table — already included

            elif action == "gacc":
                data = lc.gacc()
                result["gacc"] = {
                    c: {
                        "true":  _fmt(data[c]["true"],  clauses),
                        "false": _fmt(data[c]["false"], clauses),
                    }
                    for c in clauses
                }

            elif action == "cacc":
                data = lc.cacc()
                result["cacc"] = {
                    c: {
                        "true":  _fmt(data[c]["true"],  clauses),
                        "false": _fmt(data[c]["false"], clauses),
                    }
                    for c in clauses
                }

            elif action == "racc":
                data = lc.racc()
                result["racc"] = {
                    c: {
                        "true":  _fmt(data[c]["true"],  clauses),
                        "false": _fmt(data[c]["false"], clauses),
                    }
                    for c in clauses
                }

            elif action == "gicc":
                data = lc.gicc()
                result["gicc"] = {
                    c: {
                        "true":  _fmt(data[c]["true"],  clauses),
                        "false": _fmt(data[c]["false"], clauses),
                    }
                    for c in clauses
                }

            elif action == "ricc":
                data = lc.ricc()
                result["ricc"] = {
                    c: {
                        "true":  _fmt(data[c]["true"],  clauses),
                        "false": _fmt(data[c]["false"], clauses),
                    }
                    for c in clauses
                }

        except ValueError as exc:
            error = str(exc)

    return render_template(
        "index.html",
        predicate=predicate,
        action=action,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
