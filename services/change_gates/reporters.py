import json


def json_report(evaluation: dict) -> str:
    return json.dumps(evaluation, indent=2, sort_keys=True)


def markdown_report(evaluation: dict) -> str:
    risk = evaluation["overall_risk"]["risk_score"]
    lines = [
        "# DataObs Change Gate",
        "",
        f"Status: **{evaluation['status'].upper()}**",
        f"Risk: **{risk if risk is not None else 'unknown'}/100**",
        f"Confidence: **{evaluation['confidence']:.2f}**",
        "",
        f"Changed models: **{evaluation['changed_model_count']}**",
        "",
        "## Blocking evidence",
    ]
    lines += [f"- `{reason}`" for reason in evaluation["blocking_reasons"]] or ["- None observed."]
    lines += ["", "## Warnings"] + (
        [f"- `{reason}`" for reason in evaluation["warning_reasons"]] or ["- None observed."]
    )
    lines += ["", "_Downstream relationships indicate potential impact, not a proven failure._", ""]
    return "\n".join(lines)
