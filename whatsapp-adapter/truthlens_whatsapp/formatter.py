LABELS = {
    "en": {
        "verified": "Verified",
        "false": "False",
        "partially_true": "Partially true",
        "outdated": "Outdated",
        "misleading_context": "Misleading context",
        "unconfirmed": "Unconfirmed",
    },
    "hi": {
        "verified": "सत्यापित",
        "false": "गलत",
        "partially_true": "आंशिक सच",
        "outdated": "पुरानी जानकारी",
        "misleading_context": "भ्रामक संदर्भ",
        "unconfirmed": "अपुष्ट",
    },
    "mr": {
        "verified": "सत्यापित",
        "false": "चुकीचे",
        "partially_true": "अंशतः सत्य",
        "outdated": "कालबाह्य",
        "misleading_context": "दिशाभूल करणारा संदर्भ",
        "unconfirmed": "अपुष्ट",
    },
}
DEVELOPMENT = "TruthLens DEVELOPMENT TEST: your message was received. Fact-checking is not enabled for this test. No verdict or evidence has been generated."


def split_text(text, limit=3500):
    # Count UTF-16 code units conservatively; preserve complete source URLs across parts.
    parts, current = [], ""
    for line in text.splitlines():
        if len(line.encode("utf-16-le")) // 2 > limit:
            # Only prose can exceed one message; evidence URLs are schema-limited to 2048.
            for start in range(0, len(line), limit // 2):
                if current:
                    parts.append(current)
                    current = ""
                parts.append(line[start : start + limit // 2])
            continue
        candidate = f"{current}\n{line}" if current else line
        if len(candidate.encode("utf-16-le")) // 2 > limit:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def format_reports(reports, *, extraction_warnings=None, sources_only=False):
    lines = ["TruthLens | Claim check"]
    for result in reports:
        language = result["response_language"]
        if result["status"] == "partial":
            lines.append("PARTIAL CHECK: some processing or evidence retrieval was incomplete.")
        lines += [result["summary"], f"Checked: {result['checked_at']}"]
        for index, claim in enumerate(result["claims"], 1):
            lines += [
                f"Claim {index}: {claim['claim_text']}",
                f"Verdict: {LABELS[language][claim['verdict']]}",
            ]
            if not sources_only:
                lines += [claim["explanation"], claim["next_step"]]
            evidence = claim["evidence"] if sources_only else claim["evidence"][:3]
            for source in evidence:
                lines += [
                    f"Source ({source['stance']}): {source['publisher']} — {source['title']}",
                    source["url"],
                ]
            if not evidence:
                lines.append(
                    "No usable evidence sources returned; absence of evidence does not establish falsity."
                )
            if not sources_only and len(claim["evidence"]) > 3:
                lines.append("Reply SOURCES for remaining evidence, including other stances.")
            lines += [f"Limit: {item}" for item in claim["limitations"]]
        lines += [f"Warning: {item}" for item in result["warnings"]]
    lines += [f"Extraction warning: {item}" for item in (extraction_warnings or [])]
    lines.append("HELP | SOURCES | HINDI | MARATHI | ENGLISH | STOP")
    return split_text("\n".join(lines))
