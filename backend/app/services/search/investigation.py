"""Deterministic query planning; publisher identity never establishes factual truth."""

import re
from dataclasses import dataclass

from app.schemas.models import AtomicClaim


@dataclass(frozen=True)
class SearchStage:
    name: str
    query: str
    include_domains: tuple[str, ...] = ()


def authority_for(text: str, jurisdiction: str = "IN") -> str | None:
    if re.search(r"\bWHO\b", text) or re.search(r"World Health Organization", text, re.I):
        return "who.int"
    if jurisdiction != "IN":
        return None
    rules = [
        (
            r"banknotes?|\brupees?\s+notes?\b|(?:₹|\bRs\.?|\brupees?)\s*\d+\s*notes?\b|currency|legal tender|demonet|नोट|चलन|नोटबंदी|Reserve Bank|\bRBI\b",
            "rbi.org.in",
        ),
        (r"aadhaar|aadhar|आधार|UIDAI", "uidai.gov.in"),
        (r"election|voter|मतदान|निवडणूक|चुनाव|Election Commission", "eci.gov.in"),
        (r"Supreme Court|सुप्रीम कोर्ट|सर्वोच्च न्यायालय", "sci.gov.in"),
        (r"scholarship|शिष्यवृत्ती|छात्रवृत्ति|Ministry of Education", "education.gov.in"),
        (r"Ministry of Health|स्वास्थ्य मंत्रालय|आरोग्य मंत्रालय", "mohfw.gov.in"),
        (r"PM.?Kisan|पीएम.?किसान", "pmkisan.gov.in"),
        (r"income tax|आयकर", "incometax.gov.in"),
        (r"government scheme|सरकारी योजना|सरकारची योजना|PIB", "pib.gov.in"),
    ]
    return next((domain for pattern, domain in rules if re.search(pattern, text, re.I)), None)


def investigation_plan(claim: AtomicClaim, jurisdiction: str = "IN") -> list[SearchStage]:
    base = re.sub(r"\bsite:\S+", "", claim.queries[0]).strip()
    resolved = [value for value in claim.dates if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)]
    if resolved:
        base += " " + " ".join(resolved[:3])
    domain = authority_for(claim.claim_text, jurisdiction)
    anchor = " ".join('"' + e.replace('"', "")[:80] + '"' for e in claim.entities[:4])[:160]
    wires = ("reuters.com", "apnews.com", "bbc.com")
    independent = f"{anchor} {base[:200]} reporting"
    # Unknown-person/event claims have no government primary authority. Use a
    # neutral wire discovery query rather than implicitly assuming a death hoax.
    primary = (f"site:{domain} {base}" if domain else independent)[:400]
    regional = " तथ्य जांच खंडन" if re.search(r"[\u0900-\u097f]", claim.claim_text) else ""
    corroboration = independent if domain else f"{anchor} {base[:200]} report sources"
    contradiction = (
        anchor + " " + base + " false claim official clarification correction fact check" + regional
    )
    entities = " ".join(claim.entities[:4])
    fallback = (
        f"site:{domain} {entities} {claim.claim_text} clarification circular PDF"
        if domain
        else f"{anchor} {claim.claim_text} report confirmation correction"
    )
    stages = [
        SearchStage("primary", primary, () if domain else wires),
        SearchStage("corroboration", corroboration[:400], wires if domain else ()),
        SearchStage("contradiction", contradiction[:400]),
        SearchStage("fallback", fallback[:400]),
    ]
    seen: set[str] = set()
    planned = []
    for stage in stages:
        if stage.query.strip() and stage.query not in seen:
            seen.add(stage.query)
            planned.append(stage)
    return planned
