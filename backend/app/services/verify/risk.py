import re

from app.schemas.models import Risk, RiskFactor

RULES = [
    (
        "otp_request",
        35,
        r"(?:share|send|provide|बताएं|भेजें|पाठवा|सांगा).{0,40}(?:otp|ओटीपी)|(?:otp|ओटीपी).{0,40}(?:share|send|provide|बताएं|भेजें|पाठवा|सांगा)",
        "A request to share an OTP can expose your account.",
    ),
    (
        "payment_demand",
        25,
        r"pay|payment|processing fee|पैसे|शुल्क|भुगतान",
        "A payment or fee request deserves an independent check.",
    ),
    (
        "identity_collection",
        20,
        r"aadhaar|aadhar|\bpan\b|आधार|पॅन",
        "Identity details appear in the message; verify who is requesting them.",
    ),
    (
        "urgency",
        15,
        r"urgent|immediately|last chance|today only|तुरंत|तात्काळ|आज ही|आजच",
        "Urgency can pressure people into acting before checking.",
    ),
    (
        "mass_forward",
        10,
        r"forward|share with everyone|फॉरवर्ड|सर्वांना|सबको भेज",
        "The message asks readers to spread it.",
    ),
    (
        "authority_appeal",
        10,
        r"government approved|official notice|सरकारी|शासन|government scheme",
        "An authority claim should be checked at the institution's original site.",
    ),
]


def risk_for(text: str) -> Risk:
    factors = [
        RiskFactor(rule=rule, weight=weight, description=description)
        for rule, weight, pattern, description in RULES
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    ]
    score = min(100, sum(f.weight for f in factors))
    return Risk(
        score=score,
        level="high" if score >= 60 else "medium" if score >= 25 else "low",
        factors=factors,
    )
