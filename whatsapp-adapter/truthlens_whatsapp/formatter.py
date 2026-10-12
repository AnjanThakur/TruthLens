from datetime import datetime, timedelta, timezone

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
        try:
            checked = (
                datetime.fromisoformat(result["checked_at"].replace("Z", "+00:00"))
                .astimezone(timezone(timedelta(hours=5, minutes=30)))
                .strftime("%d %b %Y, %H:%M IST")
            )
        except (ValueError, TypeError):
            checked = "Date not established"
        lines.append(f"Checked: {checked}")
        for index, claim in enumerate(result["claims"], 1):
            lines += [
                f"Claim {index}: {claim['claim_text']}",
                f"Verdict: {LABELS[language][claim['verdict']]}",
            ]
            if not sources_only:
                lines += [claim["explanation"][:1000], claim["next_step"][:350]]
            relevant = [
                source
                for source in claim["evidence"]
                if source.get("directly_relevant")
                and source.get("source_type") in {"primary", "secondary", "fact_check"}
                and "incomplete_content:" not in source.get("authority_basis", "")
                and source.get("excerpt_provenance") == "fetched_page"
                and source["stance"] in {"supports", "contradicts", "context"}
            ]
            evidence = claim["evidence"] if sources_only else relevant[:3]
            if not sources_only and not evidence:
                # An unassessed retrieval is explicitly separated from verdict evidence.
                evidence = [
                    source for source in claim["evidence"] if source["stance"] == "unclear"
                ][:1]
            for source in evidence:
                label = (
                    f"Source ({source['stance']})"
                    if source in relevant
                    else "Unassessed retrieved link (not verdict evidence)"
                )
                lines += [
                    f"{label}: {source['publisher']} — {source['title']}",
                    source["url"],
                ]
            if not evidence:
                lines.append(
                    "No usable evidence sources returned; absence of evidence does not establish falsity."
                )
            if not sources_only and len(claim["evidence"]) > 3:
                lines.append("Reply SOURCES for remaining evidence, including other stances.")
            lines += [f"Limit: {item}" for item in claim["limitations"][:2]]
        if result["warnings"]:
            lines.append(
                {
                    "en": "Some processing could not complete. An unassessed claim has no definitive verdict; try again later.",
                    "hi": "कुछ प्रक्रिया अधूरी रही। बिना मूल्यांकन का दावा निर्णायक नहीं है; बाद में प्रयास करें।",
                    "mr": "काही प्रक्रिया अपूर्ण राहिली. मूल्यांकन न झालेल्या दाव्याचा निर्णायक निष्कर्ष नाही; नंतर प्रयत्न करा.",
                }[language]
            )
    if extraction_warnings:
        lines.append(
            "Extraction was incomplete. Review the visible extracted text on the website before relying on a whole-document check."
        )
    lines.append("HELP | SOURCES | HINDI | MARATHI | ENGLISH | STOP")
    return split_text("\n".join(lines))
