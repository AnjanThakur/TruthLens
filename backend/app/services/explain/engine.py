import re

from app.errors import AppError
from app.schemas.models import Audience, ClaimResult, Language, VerificationResult, Wording
from app.services.providers import LLM

LABELS = {
    "en": {
        "verified": "The retrieved evidence supports this claim.",
        "false": "The retrieved evidence contradicts this claim.",
        "partially_true": "Only part of this claim is supported.",
        "outdated": "Dated evidence shows this claim is old and no longer applies as stated.",
        "misleading_context": "The claim leaves out context that changes its meaning.",
        "unconfirmed": "We could not confirm this claim.",
    },
    "hi": {
        "verified": "मिले प्रमाण इस दावे का समर्थन करते हैं।",
        "false": "मिले प्रमाण इस दावे को गलत बताते हैं।",
        "partially_true": "इस दावे का केवल कुछ हिस्सा सही पाया गया है।",
        "outdated": "तारीख वाले प्रमाण बताते हैं कि यह पुरानी बात है और अब ऐसे लागू नहीं होती।",
        "misleading_context": "इस दावे में ज़रूरी संदर्भ छूट गया है, जिससे अर्थ बदलता है।",
        "unconfirmed": "हम इस दावे की पुष्टि नहीं कर पाए।",
    },
    "mr": {
        "verified": "मिळालेले पुरावे या दाव्याला आधार देतात.",
        "false": "मिळालेले पुरावे हा दावा चुकीचा असल्याचे दाखवतात.",
        "partially_true": "या दाव्यातील फक्त काही भागाला आधार मिळाला आहे.",
        "outdated": "तारखेसह मिळालेले पुरावे ही माहिती जुनी आहे आणि आता अशी लागू होत नाही असे दाखवतात.",
        "misleading_context": "या दाव्यात महत्त्वाचा संदर्भ गाळला आहे, त्यामुळे अर्थ बदलतो.",
        "unconfirmed": "आम्हाला या दाव्याची खात्री करता आली नाही.",
    },
}
CAUTION = {
    "en": "Missing or conflicting evidence is not proof that a claim is false. Check the original source before forwarding.",
    "hi": "प्रमाण न मिलना या प्रमाणों में मतभेद होना दावे के गलत होने का सबूत नहीं है। आगे भेजने से पहले मूल स्रोत देखें।",
    "mr": "पुरावे न मिळणे किंवा त्यांत मतभेद असणे म्हणजे दावा चुकीचा आहे असा पुरावा नाही. पुढे पाठवण्याआधी मूळ स्रोत पाहा.",
}
NEXT_STEP = {
    "en": "Read the original source before acting or forwarding. Never share an OTP.",
    "hi": "कुछ करने या आगे भेजने से पहले मूल स्रोत पढ़ें। अपना ओटीपी कभी साझा न करें।",
    "mr": "कृती करण्याआधी किंवा पुढे पाठवण्याआधी मूळ स्रोत वाचा. आपला ओटीपी कोणालाही सांगू नका.",
}
EMPTY = {
    "en": "No checkable factual claims were found in this text.",
    "hi": "इस संदेश में जाँचने योग्य तथ्य वाला दावा नहीं मिला।",
    "mr": "या संदेशात तपासता येईल असा तथ्यात्मक दावा आढळला नाही.",
}
UNCONFIRMED_REASONS = {
    "en": {
        "empty": "No usable source evidence was retrieved.",
        "conflict": "The retrieved sources disagree about this claim.",
        "weak": "The available sources do not establish this exact claim.",
        "assessment_failed": "Source evidence was retrieved, but AI assessment failed. The evidence has not been accepted as supporting or contradicting this claim.",
    },
    "hi": {
        "empty": "काम आने वाला स्रोत प्रमाण नहीं मिला।",
        "conflict": "मिले स्रोतों में इस दावे पर मतभेद है।",
        "weak": "उपलब्ध स्रोत इस पूरे दावे की पुष्टि नहीं करते।",
        "assessment_failed": "स्रोत प्रमाण मिले, लेकिन AI मूल्यांकन विफल हुआ। दावे के समर्थन या विरोध का निष्कर्ष स्वीकार नहीं हुआ।",
    },
    "mr": {
        "empty": "वापरता येईल असा स्रोत पुरावा मिळाला नाही.",
        "conflict": "मिळालेल्या स्रोतांत या दाव्याबद्दल मतभेद आहेत.",
        "weak": "उपलब्ध स्रोत या संपूर्ण दाव्याची खात्री देत नाहीत.",
        "assessment_failed": "स्रोत पुरावे मिळाले, पण AI मूल्यांकन अयशस्वी झाले. दाव्याला आधार किंवा विरोध असल्याचा निष्कर्ष स्वीकारलेला नाही.",
    },
}
CHILD_STEP = {
    "en": "Ask a trusted adult to read the original source with you.",
    "hi": "किसी भरोसेमंद बड़े से मूल स्रोत आपके साथ पढ़ने को कहें।",
    "mr": "विश्वासू मोठ्या व्यक्तीला तुमच्यासोबत मूळ स्रोत वाचायला सांगा.",
}


def fallback_wording(claim: ClaimResult, language: Language) -> Wording:
    statement = LABELS[language][claim.verdict]
    return Wording(
        explanation=statement + " " + CAUTION[language],
        short_summary=statement,
        key_points=[statement],
        next_step=NEXT_STEP[language],
    )


async def format_claim(
    llm: LLM, claim: ClaimResult, language: Language, audience: Audience
) -> Wording:
    if claim.verdict == "unconfirmed":
        stances = {
            e.stance
            for e in claim.evidence
            if e.source_type != "other"
            and e.excerpt_provenance == "fetched_page"
            and e.directly_relevant
            and "incomplete_content:" not in e.authority_basis
            and "entity_mismatch:" not in e.authority_basis
        }
        kind = (
            "assessment_failed"
            if any(note.startswith("Evidence assessment failed;") for note in claim.limitations)
            else "empty"
            if not claim.evidence
            else "conflict"
            if {"supports", "contradicts"} <= stances
            else "weak"
        )
        reason = UNCONFIRMED_REASONS[language][kind]
        checked = sum(
            e.source_type != "other"
            and e.excerpt_provenance == "fetched_page"
            and "incomplete_content:" not in e.authority_basis
            and "entity_mismatch:" not in e.authority_basis
            for e in claim.evidence
        )
        subject = claim.claim_text[:280]
        context = {
            "en": f"For “{subject}”, {checked} complete reviewed source(s) were retrieved.",
            "hi": f"“{subject}” के लिए {checked} पूर्ण, पहचाने गए स्रोत मिले।",
            "mr": f"“{subject}” साठी {checked} पूर्ण, ओळखलेले स्रोत मिळाले.",
        }[language]
        return Wording(
            explanation=context + " " + reason + " " + CAUTION[language],
            short_summary=LABELS[language]["unconfirmed"],
            key_points=[reason],
            next_step=CHILD_STEP[language] if audience == "child" else NEXT_STEP[language],
        )
    if language == "en" and audience == "adult":
        # The validated Decision already supplies the grounded English explanation.
        return Wording(
            explanation=claim.grounded_explanation,
            short_summary=LABELS["en"][claim.verdict],
            key_points=claim.key_points[:3],
            next_step=NEXT_STEP["en"],
        )
    # Evidence and classification never pass through a writable response schema.
    wording = await llm.structured(
        "Reword the supplied GROUNDED English explanation into the target language (en/hi/mr). Use only 1-2 short, plain sentences about the evidence; the server adds a verdict sentence and uncertainty warning to produce a 2-5 sentence explanation. Child uses everyday words and an adult-help step, teen concise practical wording, senior short sentences without jargon, adult plain language. The verdict is immutable. Preserve every qualification, especially unconfirmed. Do not add facts, sources, dates, URLs or quotations. key_points are at most 3 brief read-aloud lines. Source stances and notes are read-only. Do not translate original_span. Return wording only.",
        {
            "language": language,
            "audience": audience,
            "claim_text": claim.claim_text,
            "verdict": claim.verdict,
            "grounded_explanation": claim.grounded_explanation,
            "short_summary": claim.short_summary,
            "limitations": claim.limitations,
            "evidence": [
                {"excerpt": e.excerpt, "stance": e.stance, "publisher": e.publisher}
                for e in claim.evidence
            ],
        },
        Wording,
    )
    combined = " ".join(
        [wording.explanation, wording.short_summary, wording.next_step, *wording.key_points]
    )
    if re.search(r"https?://|www\.", combined):
        raise AppError(
            "explanation_invalid",
            "The explanation provider added a new link; original evidence was preserved.",
            502,
        )
    if len([s for s in re.split(r"[.!?।]+(?:\s+|$)", wording.explanation) if s.strip()]) > 2:
        raise AppError(
            "explanation_invalid",
            "The explanation was too long; the factual result was preserved.",
            502,
        )
    # Keep an unambiguous, deterministic verdict sentence even if translation drifts.
    wording.explanation = LABELS[language][claim.verdict] + " " + wording.explanation
    if claim.verdict == "unconfirmed":
        wording.explanation += " " + CAUTION[language]
        wording.short_summary = LABELS[language][claim.verdict]
    return wording


async def reexplain(
    llm: LLM, result: VerificationResult, language: Language, audience: Audience
) -> VerificationResult:
    changed = result.model_copy(deep=True)
    for original, claim in zip(result.claims, changed.claims, strict=True):
        wording = await format_claim(llm, original, language, audience)
        for field in ("explanation", "short_summary", "key_points", "next_step"):
            setattr(claim, field, getattr(wording, field))
    changed.response_language, changed.audience = language, audience
    changed.summary = (
        " ".join(c.short_summary for c in changed.claims) if changed.claims else EMPTY[language]
    )
    return changed
