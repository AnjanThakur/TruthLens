import hashlib
import json
from datetime import datetime
from typing import Protocol, TypedDict

from app.schemas.models import Language
from app.services.alerts.models import AlertDraft, Observation


class LocaleText(TypedDict):
    title: str
    claim_contradicted: str
    claim_needs_context: str
    suspicious_indicators: str
    scope: str
    actions: list[str]
    signals: dict[str, str]


TEXT: dict[Language, LocaleText] = {
    "en": {
        "title": "TruthLens: recurring claim alert",
        "claim_contradicted": "Reviewed fact-check evidence contradicts this claim. This finding alone does not establish criminal fraud.",
        "claim_needs_context": "Reviewed evidence establishes important qualifications or changed context. This finding alone does not establish criminal fraud.",
        "suspicious_indicators": "The underlying claim remains unconfirmed. Suspicious indicators warrant caution; they do not prove fraud.",
        "scope": "Based on {count} independent consented submissions within {hours} hours. This is a local sample, not a WhatsApp-wide trend.",
        "actions": [
            "Do not share OTPs, passwords or identity documents.",
            "Check the linked original source before paying or forwarding.",
        ],
        "signals": {
            "otp_request": "Request to share an OTP",
            "payment_demand": "Payment request",
            "identity_collection": "Identity details requested",
            "urgency": "Pressure to act quickly",
            "mass_forward": "Request to forward widely",
            "authority_appeal": "Claim of official authority",
        },
    },
    "hi": {
        "title": "TruthLens: बार-बार मिले दावे की सूचना",
        "claim_contradicted": "समीक्षित तथ्य-जाँच के साक्ष्य इस दावे का खंडन करते हैं। केवल इससे आपराधिक धोखाधड़ी सिद्ध नहीं होती।",
        "claim_needs_context": "समीक्षित साक्ष्य महत्वपूर्ण शर्तें या बदला हुआ संदर्भ बताते हैं। केवल इससे आपराधिक धोखाधड़ी सिद्ध नहीं होती।",
        "suspicious_indicators": "मूल दावा अभी अपुष्ट है। संदिग्ध संकेतों पर सावधानी रखें; वे धोखाधड़ी का प्रमाण नहीं हैं।",
        "scope": "यह {hours} घंटों में सहमति से मिले {count} स्वतंत्र प्रेषकों के नमूने पर आधारित है; पूरे WhatsApp का रुझान नहीं है।",
        "actions": [
            "ओटीपी, पासवर्ड या पहचान के दस्तावेज साझा न करें।",
            "भुगतान या संदेश आगे भेजने से पहले दिए गए मूल स्रोत को जाँचें।",
        ],
        "signals": {
            "otp_request": "ओटीपी साझा करने का अनुरोध",
            "payment_demand": "भुगतान का अनुरोध",
            "identity_collection": "पहचान की जानकारी माँगी गई",
            "urgency": "जल्दी करने का दबाव",
            "mass_forward": "संदेश फैलाने का अनुरोध",
            "authority_appeal": "सरकारी अधिकार का दावा",
        },
    },
    "mr": {
        "title": "TruthLens: वारंवार मिळालेल्या दाव्याची सूचना",
        "claim_contradicted": "तपासलेल्या तथ्य-पडताळणीच्या पुराव्यांनुसार हा दावा चुकीचा आहे. केवळ यावरून गुन्हेगारी फसवणूक सिद्ध होत नाही.",
        "claim_needs_context": "तपासलेले पुरावे महत्त्वाच्या अटी किंवा बदललेला संदर्भ दाखवतात. केवळ यावरून गुन्हेगारी फसवणूक सिद्ध होत नाही.",
        "suspicious_indicators": "मूळ दावा अजून अपुष्ट आहे. संशयास्पद संकेतांबाबत सावध राहा; ते फसवणुकीचा पुरावा नाहीत.",
        "scope": "हे {hours} तासांत संमतीने मिळालेल्या {count} स्वतंत्र पाठवणाऱ्यांच्या नमुन्यावर आधारित आहे; संपूर्ण WhatsApp चा कल नाही.",
        "actions": [
            "ओटीपी, पासवर्ड किंवा ओळखपत्रे शेअर करू नका.",
            "पैसे भरण्यापूर्वी किंवा संदेश पुढे पाठवण्यापूर्वी दिलेला मूळ स्रोत तपासा.",
        ],
        "signals": {
            "otp_request": "ओटीपी शेअर करण्याची विनंती",
            "payment_demand": "पैसे भरण्याची विनंती",
            "identity_collection": "ओळखीची माहिती मागितली",
            "urgency": "घाई करण्याचा दबाव",
            "mass_forward": "संदेश पसरवण्याची विनंती",
            "authority_appeal": "अधिकृत असल्याचा दावा",
        },
    },
}


class ClaimTranslator(Protocol):
    """Optional injected adapter; none by default. Tests use deterministic fixtures."""

    def translate(
        self, text: str, source_language: str, target_language: Language
    ) -> str | None: ...


def fingerprint(observations: list[Observation], window_start: datetime) -> str:
    # Sources, stances, check dates and sample membership all invalidate prior approval.
    data = [
        {
            "record": o.model_dump(mode="json", exclude={"source_hash", "last_seen_at"}),
            "in_current_window": o.received_at >= window_start,
        }
        for o in sorted(observations, key=lambda x: str(x.observation_id))
    ]
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def content_hash(draft: AlertDraft) -> str:
    data = draft.model_dump(mode="json", exclude={"approval_status", "review", "review_history"})
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def channel_text(draft: AlertDraft) -> str:
    return "\n\n".join(
        [
            draft.title,
            draft.claim_summary or "",
            draft.explanation,
            "\n".join(draft.scam_warning_signs),
            "\n".join(draft.recommended_user_actions),
            "\n".join(draft.authoritative_source_links),
            draft.scope_note,
        ]
    )
