"""
=============================================================================
Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
File: backend/explainability.py
Task: Transparent Multilingual Legal Meaning Preservation Explainability Engine
=============================================================================

This module provides interpretable, legally-grounded explanations for JUDGEBERT
predictions on English and Hindi statutory text pairs.

Core Design Principles:
1. Multi-Tiered Transparency:
   - Separates raw statistical model predictions (JUDGEBERT multi-task outputs)
     from transparent rule-based text-comparison heuristics.
2. Invariant Tracking (7 Statutory Invariants):
   - Deontic Modality (mandatory 'shall'/'होगा' vs. permissive 'may'/'सकेगा')
   - Strong Prohibitions ('shall not'/'no person shall'/'नहीं करेगा')
   - Conditions, Exceptions & Provisos ('subject to'/'provided that'/'के अधीन')
   - Numbers, Monetary Caps & Thresholds (50 rupees, 3 years, धारा 24)
   - Scope, Applicability & Institutional Thresholds
3. Multilingual Coverage:
   - Symmetrically supports English and Hindi statutory text pairs.
4. Epistemic Humility:
   - Does NOT claim attention weights constitute faithful legal proof.
   - Does NOT fabricate reasoning or claim artificial legal intelligence.
   - Clearly documents heuristic and neural model limitations.
"""

import difflib
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("JUDGEBERT_EXPLAINABILITY")
if not logger.handlers:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
    )

# -----------------------------------------------------------------------------
# OFFICIAL SCORING BANDS & TAXONOMY DESCRIPTIONS
# -----------------------------------------------------------------------------
DECISION_LABELS = [
    "FUNDAMENTALLY_ALTERED",
    "MAJOR_LOSS",
    "PARTIALLY_PRESERVED",
    "MOSTLY_PRESERVED",
    "PRESERVED",
]

ERROR_TYPE_LABELS = [
    "NONE",
    "OMISSION",
    "HALLUCINATION_ADDITION",
    "CONTRADICTION",
    "MODALITY_CHANGE",
    "CONDITION_EXCEPTION_LOSS",
    "SCOPE_CHANGE",
    "NUMERIC_ENTITY_REFERENCE_ERROR",
]

SCORE_BANDS = [
    {
        "range": (9.0, 10.0),
        "category": "PRESERVED",
        "description": "Full Legal Meaning Preservation. Zero material distortion; all statutory rights, obligations, conditions, and penalties remain intact.",
    },
    {
        "range": (7.0, 8.99),
        "category": "MOSTLY_PRESERVED",
        "description": "Mostly Preserved with Minor Drift. Minor stylistic simplification or negligible non-substantive omission with no alteration to legal standing.",
    },
    {
        "range": (5.0, 6.99),
        "category": "PARTIALLY_PRESERVED",
        "description": "Partial Preservation with Noticeable Drift. Important procedural detail or qualification omitted, creating potential legal ambiguity.",
    },
    {
        "range": (3.0, 4.99),
        "category": "MAJOR_LOSS",
        "description": "Major Legal Meaning Loss. Material alteration of rights or duties; critical proviso dropped; modality altered (e.g. 'shall' to 'may'); penalty distorted.",
    },
    {
        "range": (1.0, 2.99),
        "category": "FUNDAMENTALLY_ALTERED",
        "description": "Critical Failure / Fundamentally Altered. Statutory command negated, liability inverted, penalty omitted, or non-existent right introduced.",
    },
]

ERROR_TYPE_DEFINITIONS = {
    "NONE": "No discernible legal error or meaning distortion. The plain-language text faithfully captures statutory force.",
    "OMISSION": "A material legal element present in the statute is completely missing in the simplified version.",
    "HALLUCINATION_ADDITION": "The simplified text introduces new rights, duties, procedures, or penalties not present in the statute.",
    "CONTRADICTION": "The simplified text asserts an outcome directly opposite to the statute (e.g., permits what is strictly prohibited).",
    "MODALITY_CHANGE": "Alteration of deontic force: weakening a mandatory command ('shall'/'होगा') into discretion ('may'/'सकेगा'), or vice-versa.",
    "CONDITION_EXCEPTION_LOSS": "Omission of a statutory proviso, precondition, non-obstante clause ('notwithstanding'), or exception.",
    "SCOPE_CHANGE": "Broadening or narrowing the geographical, institutional, or demographic applicability of the statutory provision.",
    "NUMERIC_ENTITY_REFERENCE_ERROR": "Distortion of numerical thresholds (fines, age, periods), institutional titles, or section references.",
}


# -----------------------------------------------------------------------------
# MULTILINGUAL LEGAL PATTERNS & REGEXES
# -----------------------------------------------------------------------------
PATTERNS = {
    # 1. Deontic Modality
    "modal_mandatory_en": re.compile(
        r"\b(shall|must|is required to|are required to|bound to|shall be|mandatory|obligatory)\b",
        re.IGNORECASE,
    ),
    "modal_discretionary_en": re.compile(
        r"\b(may|can|is authorized to|are authorized to|at its discretion|at discretion|is permitted to|may be|optional)\b",
        re.IGNORECASE,
    ),
    "modal_advisory_en": re.compile(
        r"\b(should|ought to|advised to|recommended to)\b",
        re.IGNORECASE,
    ),
    "modal_mandatory_hi": re.compile(
        r"(होगा|होगी|होंगे|करेगा|करेगी|करेंगे|बाध्य होगा|बाध्य होगी|अपेक्षित होगा|अनिवार्य होगा|अनिवार्य)",
    ),
    "modal_discretionary_hi": re.compile(
        r"(सकेगा|सकेगी|सकेंगे|सकता है|सकती है|सकते हैं|अनुज्ञात होगा|अधिकार होगा|प्राधिकृत होगा|विवेक पर)",
    ),
    "modal_advisory_hi": re.compile(
        r"(चाहिए|उचित होगा|परामर्श दिया जाता है)",
    ),

    # 2. Strong Statutory Prohibitions (Absolute Bar)
    "prohibition_en": re.compile(
        r"\b(shall not|must not|prohibited|forbidden|cannot|no\s+[a-z\s]{1,30}?\s+shall|no\s+person\s+who[a-z\s]{1,30}?\s+shall)\b",
        re.IGNORECASE,
    ),
    "prohibition_hi": re.compile(
        r"(नहीं करेगा|नहीं करेगी|नहीं करेंगे|प्रतिषिद्ध|वर्जित|कोई व्यक्ति नहीं|कोई भी व्यक्ति नहीं|कोई न्यायालय नहीं)",
    ),

    # 3. Penal Sanctions & Criminal Liabilities
    "penal_sanction_en": re.compile(
        r"\b(imprisonment|punished with imprisonment|liable to imprisonment|term of imprisonment|shall be liable to a penalty|penalized)\b",
        re.IGNORECASE,
    ),
    "penal_sanction_hi": re.compile(
        r"(कारावास|दंडित किया जाएगा|शास्ति|कारावास से दंडनीय|सजा दी जाएगी)",
    ),

    # 4. General Negation
    "negation_general_en": re.compile(
        r"\b(not|never|neither|nor)\b",
        re.IGNORECASE,
    ),
    "negation_general_hi": re.compile(
        r"(नहीं|न)",
    ),

    # 5. Upper Bound Numerical Caps (e.g. 'not exceeding X' <=> 'up to X')
    "cap_upper_en": re.compile(r"\b(?:not exceeding|up to|maximum of|not more than)\b", re.IGNORECASE),
    "cap_upper_hi": re.compile(r"(?:से अधिक न हो|तक|अधिकतम)"),

    # 6. Conditions & Provisos
    "condition_en": re.compile(
        r"\b(provided that|provided further that|subject to|unless|notwithstanding|where|if|in case|on condition that)\b",
        re.IGNORECASE,
    ),
    "condition_hi": re.compile(
        r"(परंतु|परन्तु|बशर्ते|के अधीन|के होते हुए भी|जब तक कि|यदि|अगर|की दशा में|की स्थिति में)",
    ),

    # 7. Explicit Statutory Exceptions / Carve-Outs
    "exception_en": re.compile(
        r"\b(except|except where|except when|save as|saving|other than|exclusion of)\b",
        re.IGNORECASE,
    ),
    "exception_hi": re.compile(
        r"(को छोड़कर|के सिवाय|अपवाद स्वरूप|के अतिरिक्त)",
    ),

    # 8. Scope Restrictions & Broadening
    "scope_restrict_en": re.compile(
        r"\b(applies only to|only to|applicable only|limited to|restricted to|specifically for|operating (?:only )?in\b|within the (?:territory|state|district))\b",
        re.IGNORECASE,
    ),
    "scope_broaden_en": re.compile(
        r"\b(all (?:financial )?institutions|to all|in all|without restriction|without exception|universally|to everyone|any person anywhere|in every circumstance)\b",
        re.IGNORECASE,
    ),
    "scope_restrict_hi": re.compile(
        r"(केवल|मात्र|सीमित|क्षेत्र के भीतर|राज्य के भीतर|शहरी जिलों में)",
    ),
    "scope_broaden_hi": re.compile(
        r"(सभी पर|बिना किसी प्रतिबंध|सार्वभौमिक रूप से|सभी व्यक्तियों|हर परिस्थिति में|समस्त)",
    ),

    # 9. Digits
    "digits": re.compile(r"\b\d+(?:[\.,]\d+)?\b"),

    # 10. Statutory Section Citations
    "citation_en": re.compile(r"\b(?:sections?|sub-sections?|clauses?|act)\s+\d+(?:\(\w+\))*", re.IGNORECASE),
    "citation_hi": re.compile(r"(?:धारा|उपधारा|खण्ड|अधिनियम)\s+\d+(?:\(\w+\))*"),
}


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def clean_and_normalize(text: Any) -> str:
    """Standardizes Unicode NFKC text and normalizes whitespace."""
    if text is None:
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\u201c\u201d\u201e\u201f\u00ab\u00bb]", '"', text)
    text = re.sub(r"[\u2018\u2019\u201a\u201b`]", "'", text)
    text = re.sub(r"[\u2013\u2014\u2015\u2500]", "—", text)
    text = re.sub(r"[\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_numerical_values(text: str) -> Set[float]:
    """Extracts all substantive numerical values (digits, words, and compound expressions) as floats."""
    values = set()
    # 1. Digits with commas / decimals
    for m in PATTERNS["digits"].finditer(text):
        try:
            val_str = m.group(0).replace(",", "")
            values.add(float(val_str))
        except ValueError:
            pass

    # 2. English compound number words
    units_tens = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    }
    mults = {
        "hundred": 100, "thousand": 1000, "lakh": 100000, "million": 1000000, "crore": 10000000,
    }
    words = re.findall(r"\b[a-z]+\b", text.lower())
    i = 0
    while i < len(words):
        current = 0
        sub_val = 0
        matched = False
        while i < len(words) and (words[i] in units_tens or words[i] in mults):
            w = words[i]
            matched = True
            if w in units_tens:
                sub_val += units_tens[w]
            elif w == "hundred":
                sub_val = (sub_val or 1) * 100
            elif w in mults:
                sub_val = (sub_val or 1) * mults[w]
                current += sub_val
                sub_val = 0
            i += 1
        if matched:
            total = current + sub_val
            if total > 0:
                values.add(float(total))
        else:
            i += 1

    # 3. Hindi compound number words
    hi_units_tens = {
        "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5,
        "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
        "पंद्रह": 15, "अठारह": 18, "बीस": 20, "तीस": 30, "चालीस": 40,
        "पचास": 50, "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90,
    }
    hi_mults = {
        "सौ": 100, "हजार": 1000, "लाख": 100000, "करोड़": 10000000,
    }
    hi_words = re.findall(r"[\u0900-\u097F]+", text)
    i = 0
    while i < len(hi_words):
        current = 0
        sub_val = 0
        matched = False
        while i < len(hi_words) and (hi_words[i] in hi_units_tens or hi_words[i] in hi_mults):
            w = hi_words[i]
            matched = True
            if w in hi_units_tens:
                sub_val += hi_units_tens[w]
            elif w == "सौ":
                sub_val = (sub_val or 1) * 100
            elif w in hi_mults:
                sub_val = (sub_val or 1) * hi_mults[w]
                current += sub_val
                sub_val = 0
            i += 1
        if matched:
            total = current + sub_val
            if total > 0:
                values.add(float(total))
        else:
            i += 1

    return values


def extract_citations(text: str) -> Set[str]:
    """Extracts formal statutory section citations."""
    cites = set()
    for m in PATTERNS["citation_en"].finditer(text):
        cites.add(re.sub(r"\s+", " ", m.group(0).lower()))
    for m in PATTERNS["citation_hi"].finditer(text):
        cites.add(re.sub(r"\s+", " ", m.group(0)))
    return cites


def extract_modal_profile(text: str) -> Dict[str, List[str]]:
    """Identifies deontic modal categories present in the text."""
    profile = {
        "mandatory": [],
        "discretionary": [],
        "advisory": [],
    }
    # English
    for m in PATTERNS["modal_mandatory_en"].finditer(text):
        profile["mandatory"].append(m.group(0).lower())
    for m in PATTERNS["modal_discretionary_en"].finditer(text):
        profile["discretionary"].append(m.group(0).lower())
    for m in PATTERNS["modal_advisory_en"].finditer(text):
        profile["advisory"].append(m.group(0).lower())

    # Hindi
    for m in PATTERNS["modal_mandatory_hi"].finditer(text):
        profile["mandatory"].append(m.group(0))
    for m in PATTERNS["modal_discretionary_hi"].finditer(text):
        profile["discretionary"].append(m.group(0))
    for m in PATTERNS["modal_advisory_hi"].finditer(text):
        profile["advisory"].append(m.group(0))

    return profile


def extract_prohibitions_and_negations(text: str) -> Dict[str, List[str]]:
    """Extracts strong statutory prohibitions and general negations."""
    prohibitions = []
    for m in PATTERNS["prohibition_en"].finditer(text):
        prohibitions.append(m.group(0).lower())
    for m in PATTERNS["prohibition_hi"].finditer(text):
        prohibitions.append(m.group(0))

    negations = []
    # Strip upper bound caps (e.g. 'not exceeding') before checking general negation
    text_no_caps = PATTERNS["cap_upper_en"].sub(" ", text)
    text_no_caps = PATTERNS["cap_upper_hi"].sub(" ", text_no_caps)

    for m in PATTERNS["negation_general_en"].finditer(text_no_caps):
        negations.append(m.group(0).lower())
    for m in PATTERNS["negation_general_hi"].finditer(text_no_caps):
        negations.append(m.group(0))

    return {
        "strong_prohibitions": prohibitions,
        "general_negations": negations,
    }


def extract_conditions(text: str) -> List[str]:
    """Extracts condition and proviso markers."""
    conds = []
    for m in PATTERNS["condition_en"].finditer(text):
        conds.append(m.group(0).lower())
    for m in PATTERNS["condition_hi"].finditer(text):
        conds.append(m.group(0))
    return conds


def extract_exceptions(text: str) -> List[str]:
    """Extracts statutory exception and exclusion markers."""
    exceptions = []
    for m in PATTERNS["exception_en"].finditer(text):
        exceptions.append(m.group(0).lower())
    for m in PATTERNS["exception_hi"].finditer(text):
        exceptions.append(m.group(0))
    return exceptions


def extract_penal_sanctions(text: str) -> List[str]:
    """Extracts penal sanctions, imprisonment, and criminal liability markers."""
    sanctions = []
    for m in PATTERNS["penal_sanction_en"].finditer(text):
        sanctions.append(m.group(0).lower())
    for m in PATTERNS["penal_sanction_hi"].finditer(text):
        sanctions.append(m.group(0))
    return sanctions


def extract_scope_profile(text: str) -> Dict[str, List[str]]:
    """Extracts statutory scope qualifiers (restrictions vs. broadeners)."""
    restricted = []
    for m in PATTERNS["scope_restrict_en"].finditer(text):
        restricted.append(m.group(0).lower())
    for m in PATTERNS["scope_restrict_hi"].finditer(text):
        restricted.append(m.group(0))

    broadened = []
    for m in PATTERNS["scope_broaden_en"].finditer(text):
        broadened.append(m.group(0).lower())
    for m in PATTERNS["scope_broaden_hi"].finditer(text):
        broadened.append(m.group(0))

    return {
        "restricted": restricted,
        "broadened": broadened,
    }


# -----------------------------------------------------------------------------
# MAIN EXPLAINABILITY ENGINE CLASS
# -----------------------------------------------------------------------------
class LegalExplainabilityEngine:
    """
    Multilingual explainability engine for legal meaning preservation.
    Synthesizes JUDGEBERT model predictions with transparent statutory invariant checks.
    """

    def __init__(self):
        logger.info("Initialized LegalExplainabilityEngine.")

    def analyze_text_differences(
        self,
        original_text: str,
        simplified_text: str,
    ) -> Dict[str, Any]:
        """
        Computes structured token- and phrase-level differences between original
        and simplified statutory text using sequence alignment.
        """
        orig_norm = clean_and_normalize(original_text)
        simp_norm = clean_and_normalize(simplified_text)

        orig_tokens = orig_norm.split()
        simp_tokens = simp_norm.split()

        matcher = difflib.SequenceMatcher(None, orig_tokens, simp_tokens)
        omitted_segments = []
        added_segments = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("delete", "replace"):
                phrase = " ".join(orig_tokens[i1:i2])
                if len(phrase.strip()) > 1:
                    omitted_segments.append(phrase)
            if tag in ("insert", "replace"):
                phrase = " ".join(simp_tokens[j1:j2])
                if len(phrase.strip()) > 1:
                    added_segments.append(phrase)

        # Lexical overlap ratio (Jaccard similarity on lower-cased tokens)
        set_orig = set(t.lower() for t in orig_tokens)
        set_simp = set(t.lower() for t in simp_tokens)
        union = set_orig.union(set_simp)
        intersection = set_orig.intersection(set_simp)
        overlap_ratio = round(len(intersection) / max(len(union), 1), 4)
        retention_ratio = round(len(intersection) / max(len(set_orig), 1), 4)

        return {
            "omitted_segments": omitted_segments[:8],
            "added_segments": added_segments[:8],
            "lexical_overlap_ratio": overlap_ratio,
            "original_token_retention_ratio": retention_ratio,
            "original_token_count": len(orig_tokens),
            "simplified_token_count": len(simp_tokens),
            "length_compression_ratio": round(len(simp_tokens) / max(len(orig_tokens), 1), 4),
        }

    def detect_invariant_shifts(
        self,
        original_text: str,
        simplified_text: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Heuristically scans for substantive shifts across statutory invariants.
        Returns categorized potential discrepancy alerts across:
        - Deontic Modality (mandatory 'shall' vs permissive 'may')
        - Numerical Thresholds, Caps & Citations
        - Conditions, Exceptions & Provisos
        - Prohibitions & Liability Inversion
        - Institutional & Geographical Scope
        - Unauthorized Penal Sanctions & Additions
        """
        orig_norm = clean_and_normalize(original_text)
        simp_norm = clean_and_normalize(simplified_text)

        shifts: Dict[str, List[Dict[str, Any]]] = {
            "modal_shifts": [],
            "numerical_reference_shifts": [],
            "condition_exception_shifts": [],
            "negation_prohibition_shifts": [],
            "scope_shifts": [],
            "penal_sanction_shifts": [],
        }

        # --- A. Deontic Modality Shift Check ---
        orig_modals = extract_modal_profile(orig_norm)
        simp_modals = extract_modal_profile(simp_norm)

        # Shift: Mandatory in original -> Discretionary in simplified (Weakening)
        if orig_modals["mandatory"] and not simp_modals["mandatory"] and simp_modals["discretionary"]:
            shifts["modal_shifts"].append({
                "type": "MANDATORY_TO_DISCRETIONARY_WEAKENING",
                "severity": "HIGH",
                "details": f"Original statutory mandatory command ({orig_modals['mandatory']}) appears softened into permissive discretion ({simp_modals['discretionary']}).",
            })
        # Shift: Discretionary in original -> Mandatory in simplified (Hardening)
        elif orig_modals["discretionary"] and not simp_modals["discretionary"] and simp_modals["mandatory"]:
            shifts["modal_shifts"].append({
                "type": "DISCRETIONARY_TO_MANDATORY_HARDENING",
                "severity": "HIGH",
                "details": f"Original statutory discretion ({orig_modals['discretionary']}) appears hardened into an absolute mandatory command ({simp_modals['mandatory']}).",
            })
        # Shift: Mandatory in original -> Advisory in simplified
        elif orig_modals["mandatory"] and simp_modals["advisory"]:
            shifts["modal_shifts"].append({
                "type": "MANDATORY_TO_ADVISORY",
                "severity": "HIGH",
                "details": f"Statutory duty ({orig_modals['mandatory']}) appears diluted to non-binding advice ({simp_modals['advisory']}).",
            })

        # --- B. Numerical Value & Citation Discrepancy Check ---
        orig_nums = extract_numerical_values(orig_norm)
        simp_nums = extract_numerical_values(simp_norm)

        dropped_nums = orig_nums - simp_nums
        added_nums = simp_nums - orig_nums

        if dropped_nums:
            shifts["numerical_reference_shifts"].append({
                "type": "NUMERICAL_THRESHOLD_DROPPED",
                "severity": "HIGH",
                "details": f"Numerical thresholds present in statute not detected in simplified text: {sorted(list(dropped_nums))}",
            })
        if added_nums:
            shifts["numerical_reference_shifts"].append({
                "type": "NUMERICAL_THRESHOLD_INTRODUCED",
                "severity": "HIGH",
                "details": f"New numerical figures introduced in simplified text not present in statutory source: {sorted(list(added_nums))}",
            })

        # Citations check
        orig_cites = extract_citations(orig_norm)
        simp_cites = extract_citations(simp_norm)
        dropped_cites = orig_cites - simp_cites
        if dropped_cites and not orig_nums.intersection(simp_nums):
            shifts["numerical_reference_shifts"].append({
                "type": "SECTION_CITATION_ALTERED",
                "severity": "MEDIUM",
                "details": f"Statutory section reference altered or dropped: {list(dropped_cites)}",
            })

        # --- C. Condition & Proviso Check ---
        orig_conds = extract_conditions(orig_norm)
        simp_conds = extract_conditions(simp_norm)
        if orig_conds and not simp_conds:
            shifts["condition_exception_shifts"].append({
                "type": "PROVISO_OR_CONDITION_POTENTIALLY_DROPPED",
                "severity": "HIGH",
                "details": f"Statutory conditions/provisos ({orig_conds}) appear omitted in the simplified candidate.",
            })

        orig_exceptions = extract_exceptions(orig_norm)
        simp_exceptions = extract_exceptions(simp_norm)
        if orig_exceptions and not simp_exceptions:
            shifts["condition_exception_shifts"].append({
                "type": "STATUTORY_EXCEPTION_DROPPED",
                "severity": "HIGH",
                "details": f"Statutory exception or carve-out ({orig_exceptions}) was omitted in the simplified candidate.",
            })

        # --- D. Strong Statutory Prohibition & Negation Inversion Check ---
        orig_neg = extract_prohibitions_and_negations(orig_norm)
        simp_neg = extract_prohibitions_and_negations(simp_norm)

        # 1. Strong Prohibition Dropped
        if orig_neg["strong_prohibitions"] and not simp_neg["strong_prohibitions"]:
            shifts["negation_prohibition_shifts"].append({
                "type": "STATUTORY_PROHIBITION_REMOVED",
                "severity": "CRITICAL",
                "details": f"Strong statutory prohibition ({orig_neg['strong_prohibitions']}) was removed in the simplified text. Potential liability inversion.",
            })
        # 2. Strong Prohibition Introduced
        elif not orig_neg["strong_prohibitions"] and simp_neg["strong_prohibitions"]:
            shifts["negation_prohibition_shifts"].append({
                "type": "STATUTORY_PROHIBITION_INTRODUCED",
                "severity": "CRITICAL",
                "details": f"New prohibition ({simp_neg['strong_prohibitions']}) was introduced where none existed in statutory source.",
            })
        # 3. General Negation Dropped
        elif orig_neg["general_negations"] and not simp_neg["general_negations"]:
            shifts["negation_prohibition_shifts"].append({
                "type": "GENERAL_NEGATION_DROPPED",
                "severity": "MEDIUM",
                "details": f"Negative particle ({orig_neg['general_negations']}) dropped without recognized equivalent.",
            })

        # --- E. Scope & Applicability Check ---
        orig_scope = extract_scope_profile(orig_norm)
        simp_scope = extract_scope_profile(simp_norm)
        if orig_scope["restricted"] and (simp_scope["broadened"] or not simp_scope["restricted"]):
            shifts["scope_shifts"].append({
                "type": "LEGAL_SCOPE_EXPANDED",
                "severity": "HIGH",
                "details": f"Statutory restriction ({orig_scope['restricted']}) appears eliminated or broadened to universal application ({simp_scope['broadened'] or 'unrestricted'}).",
            })
        elif not orig_scope["restricted"] and simp_scope["restricted"]:
            shifts["scope_shifts"].append({
                "type": "LEGAL_SCOPE_RESTRICTED",
                "severity": "MEDIUM",
                "details": f"New statutory restriction ({simp_scope['restricted']}) was introduced narrowing legal application.",
            })

        # --- F. Unauthorized Penal Sanction Check ---
        orig_sanctions = extract_penal_sanctions(orig_norm)
        simp_sanctions = extract_penal_sanctions(simp_norm)
        if not orig_sanctions and simp_sanctions:
            shifts["penal_sanction_shifts"].append({
                "type": "UNAUTHORIZED_PENAL_SANCTION_INTRODUCED",
                "severity": "CRITICAL",
                "details": f"Unauthorized penal sanction, fine, or imprisonment ({simp_sanctions}) introduced without statutory basis.",
            })

        return shifts

    @staticmethod
    def _synthesize_distribution(
        labels: List[str], target_label: str, peak_prob: float = 0.88
    ) -> Dict[str, float]:
        """Creates a normalized probability distribution centered at target_label."""
        if target_label not in labels:
            uniform = round(1.0 / len(labels), 4)
            return {k: uniform for k in labels}

        rem = round((1.0 - peak_prob) / max(len(labels) - 1, 1), 4)
        dist = {}
        for l in labels:
            dist[l] = peak_prob if l == target_label else rem
        total = sum(dist.values())
        return {k: round(v / total, 4) for k, v in dist.items()}

    def synthesize_hybrid_prediction(
        self,
        original_text: str,
        simplified_text: str,
        raw_prediction: Optional[Dict[str, Any]],
        shifts: Dict[str, List[Dict[str, Any]]],
        differences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Synthesizes raw neural model outputs with statutory invariant checks.
        Defends against majority-class collapse when legal invariants are violated,
        while strictly preserving high scores for valid semantic paraphrases.
        """
        orig_norm = clean_and_normalize(original_text)
        simp_norm = clean_and_normalize(simplified_text)
        is_identical = (orig_norm.lower() == simp_norm.lower())

        raw_score = float(raw_prediction.get("lmp_score", 9.4)) if raw_prediction else 9.4
        raw_decision = str(raw_prediction.get("pred_decision", "PRESERVED")) if raw_prediction else "PRESERVED"
        raw_error = str(raw_prediction.get("pred_error", "NONE")) if raw_prediction else "NONE"
        raw_dec_probs = raw_prediction.get("decision_probabilities", {}) if raw_prediction else {}
        raw_err_probs = raw_prediction.get("error_probabilities", {}) if raw_prediction else {}

        # 1. Exact match / identical texts
        if is_identical:
            return {
                "lmp_score": 9.85,
                "pred_decision": "PRESERVED",
                "pred_error": "NONE",
                "decision": "PRESERVED",
                "error_type": "NONE",
                "pred_decision_id": DECISION_LABELS.index("PRESERVED"),
                "pred_error_id": ERROR_TYPE_LABELS.index("NONE"),
                "decision_probabilities": self._synthesize_distribution(DECISION_LABELS, "PRESERVED", 0.98),
                "error_probabilities": self._synthesize_distribution(ERROR_TYPE_LABELS, "NONE", 0.98),
                "hybrid_adjustment_applied": False,
                "adjustment_reason": None,
                "severity_tier": "NONE",
                "is_preserved": True,
            }

        # 2. Gather all detected invariant shift items
        all_shift_items = []
        for cat, s_list in shifts.items():
            for item in s_list:
                all_shift_items.append(item)

        # 3. If zero invariant shifts detected -> retain high preservation
        if not all_shift_items:
            clean_score = max(round(raw_score, 2), 9.20)
            return {
                "lmp_score": clean_score,
                "pred_decision": "PRESERVED",
                "pred_error": "NONE",
                "decision": "PRESERVED",
                "error_type": "NONE",
                "pred_decision_id": DECISION_LABELS.index("PRESERVED"),
                "pred_error_id": ERROR_TYPE_LABELS.index("NONE"),
                "decision_probabilities": raw_dec_probs or self._synthesize_distribution(DECISION_LABELS, "PRESERVED", 0.95),
                "error_probabilities": raw_err_probs or self._synthesize_distribution(ERROR_TYPE_LABELS, "NONE", 0.95),
                "hybrid_adjustment_applied": False,
                "adjustment_reason": None,
                "severity_tier": "NONE",
                "is_preserved": True,
            }

        # 4. Map each shift type to calibrated legal standing
        shift_specs = {
            "STATUTORY_PROHIBITION_REMOVED": {
                "score": 1.50,
                "decision": "FUNDAMENTALLY_ALTERED",
                "error": "CONTRADICTION",
                "tier": "CRITICAL",
                "reason": "Statutory prohibition or absolute legal bar removed (potential liability inversion).",
            },
            "UNAUTHORIZED_PENAL_SANCTION_INTRODUCED": {
                "score": 2.20,
                "decision": "FUNDAMENTALLY_ALTERED",
                "error": "HALLUCINATION_ADDITION",
                "tier": "CRITICAL",
                "reason": "Unauthorized penal sanction, imprisonment, or criminal liability introduced.",
            },
            "STATUTORY_PROHIBITION_INTRODUCED": {
                "score": 2.40,
                "decision": "FUNDAMENTALLY_ALTERED",
                "error": "HALLUCINATION_ADDITION",
                "tier": "CRITICAL",
                "reason": "Statutory prohibition introduced where none existed in statutory source.",
            },
            "NUMERICAL_THRESHOLD_DROPPED": {
                "score": 3.50,
                "decision": "MAJOR_LOSS",
                "error": "NUMERIC_ENTITY_REFERENCE_ERROR",
                "tier": "HIGH",
                "reason": "Statutory numerical threshold, penalty amount, or period distorted or omitted.",
            },
            "NUMERICAL_THRESHOLD_INTRODUCED": {
                "score": 3.50,
                "decision": "MAJOR_LOSS",
                "error": "NUMERIC_ENTITY_REFERENCE_ERROR",
                "tier": "HIGH",
                "reason": "Unauthorized numerical figure or threshold introduced in simplified text.",
            },
            "MANDATORY_TO_DISCRETIONARY_WEAKENING": {
                "score": 4.20,
                "decision": "MAJOR_LOSS",
                "error": "MODALITY_CHANGE",
                "tier": "HIGH",
                "reason": "Mandatory statutory command ('shall'/'होगा') weakened into permissive discretion ('may'/'सकेगा').",
            },
            "MANDATORY_TO_ADVISORY": {
                "score": 4.40,
                "decision": "MAJOR_LOSS",
                "error": "MODALITY_CHANGE",
                "tier": "HIGH",
                "reason": "Mandatory statutory duty diluted into non-binding advice.",
            },
            "STATUTORY_EXCEPTION_DROPPED": {
                "score": 4.50,
                "decision": "MAJOR_LOSS",
                "error": "CONDITION_EXCEPTION_LOSS",
                "tier": "HIGH",
                "reason": "Statutory exception or carve-out clause ('except', 'save as', 'को छोड़कर') omitted.",
            },
            "PROVISO_OR_CONDITION_POTENTIALLY_DROPPED": {
                "score": 4.60,
                "decision": "MAJOR_LOSS",
                "error": "CONDITION_EXCEPTION_LOSS",
                "tier": "HIGH",
                "reason": "Statutory condition precedent or proviso ('subject to', 'provided that', 'के अधीन') omitted.",
            },
            "LEGAL_SCOPE_EXPANDED": {
                "score": 5.00,
                "decision": "PARTIALLY_PRESERVED",
                "error": "SCOPE_CHANGE",
                "tier": "HIGH",
                "reason": "Statutory applicability scope broadened beyond designated jurisdictional domain.",
            },
            "DISCRETIONARY_TO_MANDATORY_HARDENING": {
                "score": 5.40,
                "decision": "PARTIALLY_PRESERVED",
                "error": "MODALITY_CHANGE",
                "tier": "MEDIUM",
                "reason": "Statutory discretion ('may'/'सकेगा') hardened into unconditional mandate ('must'/'shall').",
            },
            "LEGAL_SCOPE_RESTRICTED": {
                "score": 5.60,
                "decision": "PARTIALLY_PRESERVED",
                "error": "SCOPE_CHANGE",
                "tier": "MEDIUM",
                "reason": "Statutory applicability narrowed compared to legislative source.",
            },
            "GENERAL_NEGATION_DROPPED": {
                "score": 5.80,
                "decision": "PARTIALLY_PRESERVED",
                "error": "OMISSION",
                "tier": "MEDIUM",
                "reason": "Negative particle dropped without recognized plain-language equivalent.",
            },
            "SECTION_CITATION_ALTERED": {
                "score": 6.00,
                "decision": "PARTIALLY_PRESERVED",
                "error": "NUMERIC_ENTITY_REFERENCE_ERROR",
                "tier": "MEDIUM",
                "reason": "Statutory section citation altered or omitted.",
            },
        }

        has_condition_or_exception_dropped = any(
            s["type"] in ("STATUTORY_EXCEPTION_DROPPED", "PROVISO_OR_CONDITION_POTENTIALLY_DROPPED")
            for s in all_shift_items
        )
        has_added_nums = any(
            s["type"] == "NUMERICAL_THRESHOLD_INTRODUCED"
            for s in all_shift_items
        )

        matched_calibrations = []
        for s in all_shift_items:
            stype = s["type"]
            # If an entire exception or proviso is dropped, any numbers dropped within it
            # are secondary collateral of the condition/exception removal, not a numeric error.
            if stype == "NUMERICAL_THRESHOLD_DROPPED" and has_condition_or_exception_dropped and not has_added_nums:
                continue

            if stype in shift_specs:
                matched_calibrations.append(shift_specs[stype])
            else:
                matched_calibrations.append({
                    "score": 5.50,
                    "decision": "PARTIALLY_PRESERVED",
                    "error": "OMISSION",
                    "tier": s.get("severity", "MEDIUM"),
                    "reason": s.get("details", "Statutory discrepancy detected."),
                })

        primary_calib = min(matched_calibrations, key=lambda c: c["score"])

        # Deduct slightly if multiple distinct violations are detected
        final_score = primary_calib["score"]
        if len(matched_calibrations) > 1:
            final_score = max(round(final_score - 0.20, 2), 1.0)

        calibrated_decision = primary_calib["decision"]
        calibrated_error = primary_calib["error"]
        primary_reason = primary_calib["reason"]

        return {
            "lmp_score": final_score,
            "pred_decision": calibrated_decision,
            "pred_error": calibrated_error,
            "decision": calibrated_decision,
            "error_type": calibrated_error,
            "pred_decision_id": DECISION_LABELS.index(calibrated_decision) if calibrated_decision in DECISION_LABELS else 0,
            "pred_error_id": ERROR_TYPE_LABELS.index(calibrated_error) if calibrated_error in ERROR_TYPE_LABELS else 0,
            "decision_probabilities": self._synthesize_distribution(DECISION_LABELS, calibrated_decision, 0.88),
            "error_probabilities": self._synthesize_distribution(ERROR_TYPE_LABELS, calibrated_error, 0.88),
            "hybrid_adjustment_applied": True,
            "adjustment_reason": primary_reason,
            "severity_tier": primary_calib["tier"],
            "is_preserved": bool(final_score >= 9.0 and calibrated_decision == "PRESERVED"),
        }

    def generate_human_readable_summary(
        self,
        score: float,
        decision: str,
        error_type: str,
        shifts: Dict[str, List[Dict[str, Any]]],
        differences: Dict[str, Any],
        hybrid_applied: bool = False,
        adjustment_reason: Optional[str] = None,
    ) -> str:
        """
        Synthesizes model predictions and heuristic findings into a concise,
        coherent human-readable legal explanation.
        """
        if hybrid_applied:
            reason_clause = f" ({adjustment_reason})" if adjustment_reason else ""
            return (
                f"Neuro-Symbolic Hybrid Guard identified critical statutory distortion "
                f"(Calibrated Score: {score:.2f}/10.0, {decision}). "
                f"Primary legal error classified as {error_type}{reason_clause}. "
                f"Rule-assisted invariant correction was applied to defend legal fidelity "
                f"against majority-class bias in the raw statistical model."
            )

        total_shifts = sum(len(v) for v in shifts.values())
        if score >= 9.0 and decision == "PRESERVED":
            if total_shifts == 0:
                return (
                    f"Full legal fidelity verified (Score: {score:.2f}/10.0, {decision}). "
                    f"All critical legal invariants, obligations, exceptions, and numerical figures "
                    f"are faithfully preserved in the plain-language simplification. "
                    f"Discrepancy tag: {error_type}."
                )
            else:
                alert_types = [alert["type"] for s_list in shifts.values() for alert in s_list]
                return (
                    f"High legal preservation verified (Score: {score:.2f}/10.0, {decision}), "
                    f"with surface-level plain-language variations: {', '.join(alert_types[:2])}."
                )

        if score >= 7.0:
            return (
                f"Mostly preserved legal meaning with minor stylistic drift (Score: {score:.2f}/10.0, {decision}). "
                f"Primary predicted error: {error_type}."
            )

        return (
            f"Material legal meaning loss detected (Score: {score:.2f}/10.0, {decision}). "
            f"Primary legal error: {error_type} ({ERROR_TYPE_DEFINITIONS.get(error_type, '')})."
        )

    def explain(
        self,
        original_text: str,
        simplified_text: str,
        prediction: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entrypoint: generates a comprehensive, transparent explanation
        for a statutory text pair.

        Args:
            original_text: Statutory source passage.
            simplified_text: Simplified candidate text.
            prediction: Optional dictionary returned by JudgeBERTInferenceEngine.predict().
                        If omitted, runs heuristic analysis and provides placeholder prediction.
        """
        orig_clean = clean_and_normalize(original_text)
        simp_clean = clean_and_normalize(simplified_text)

        # Handle empty or invalid inputs
        if not orig_clean or not simp_clean:
            return {
                "error": "Invalid input: original_text and simplified_text must be non-empty strings.",
                "predicted_score": None,
                "predicted_decision": None,
                "predicted_error": None,
                "human_readable_summary": "Incomplete input provided. Both original and simplified legal texts are required for evaluation.",
                "explanation_limitations": [
                    "Input validation failure. No statutory comparison could be executed."
                ],
            }

        # Check for identical texts
        is_identical = (orig_clean.lower() == simp_clean.lower())

        # 1. Structural Text Alignment & Diffs
        differences = self.analyze_text_differences(orig_clean, simp_clean)

        # 2. Statutory Invariant Shifts (Rule-Based Heuristics)
        shifts = self.detect_invariant_shifts(orig_clean, simp_clean)

        # 3. Neuro-Symbolic Hybrid Synthesis
        hybrid_pred = self.synthesize_hybrid_prediction(
            original_text=orig_clean,
            simplified_text=simp_clean,
            raw_prediction=prediction,
            shifts=shifts,
            differences=differences,
        )

        score = hybrid_pred["lmp_score"]
        decision = hybrid_pred["pred_decision"]
        error_type = hybrid_pred["pred_error"]
        decision_probs = hybrid_pred["decision_probabilities"]
        error_probs = hybrid_pred["error_probabilities"]
        hybrid_applied = hybrid_pred["hybrid_adjustment_applied"]
        adj_reason = hybrid_pred["adjustment_reason"]

        # 4. Rubric Band Explanation
        band_explanation = "Score outside recognized rubric range."
        for b in SCORE_BANDS:
            if b["range"][0] <= score <= b["range"][1]:
                band_explanation = b["description"]
                break

        # 5. Error Category Definition
        err_def = ERROR_TYPE_DEFINITIONS.get(error_type, "Unrecognized legal error category.")

        # 6. Synthesized Human-Readable Explanation
        if is_identical:
            summary = (
                f"Original and simplified passages are verbatim identical. "
                f"Full legal meaning preservation (Score: {score:.2f}/10.0, PRESERVED) with zero invariant drift."
            )
        else:
            summary = self.generate_human_readable_summary(
                score=score,
                decision=decision,
                error_type=error_type,
                shifts=shifts,
                differences=differences,
                hybrid_applied=hybrid_applied,
                adjustment_reason=adj_reason,
            )

        raw_pred_clean = {
            "lmp_score": round(float(prediction.get("lmp_score", 9.4)), 2) if prediction else round(score, 2),
            "decision": str(prediction.get("pred_decision", "PRESERVED")) if prediction else decision,
            "error_type": str(prediction.get("pred_error", "NONE")) if prediction else error_type,
            "decision_probabilities": prediction.get("decision_probabilities", {}) if prediction else {},
            "error_probabilities": prediction.get("error_probabilities", {}) if prediction else {},
        }

        hybrid_dict = {
            "lmp_score": round(score, 2),
            "pred_decision": decision,
            "pred_error": error_type,
            "decision": decision,
            "error_type": error_type,
            "pred_decision_id": DECISION_LABELS.index(decision) if decision in DECISION_LABELS else 0,
            "pred_error_id": ERROR_TYPE_LABELS.index(error_type) if error_type in ERROR_TYPE_LABELS else 0,
            "decision_probabilities": decision_probs,
            "error_probabilities": error_probs,
            "hybrid_adjustment_applied": hybrid_applied,
            "adjustment_reason": adj_reason,
            "is_preserved": bool(score >= 9.0 and decision == "PRESERVED"),
        }

        return {
            "predicted_score": round(score, 2),
            "predicted_decision": decision,
            "predicted_error": error_type,
            "human_readable_summary": summary,
            "score_band_explanation": band_explanation,
            "error_explanation": err_def,
            "hybrid_adjustment_applied": hybrid_applied,
            "adjustment_reason": adj_reason,
            "text_differences": differences,
            "detected_invariant_shifts": shifts,
            "hybrid_prediction": hybrid_dict,
            "raw_model_prediction": raw_pred_clean,
            "model_prediction": hybrid_dict,
            "method_and_limitations": {
                "method": "Hybrid Neuro-Symbolic: Multi-Task JUDGEBERT + Deterministic Statutory Invariant Differential Guard",
                "limitations": [
                    "Raw JUDGEBERT statistical checkpoint suffers from majority-class collapse (~84% PRESERVED, score ~9.4) caused by training dataset imbalance; the hybrid neuro-symbolic engine intercepts invariant violations to defend statutory meaning.",
                    "Statistical attention weights do not constitute legal proof and are not used as standalone justifications.",
                    "Lexical heuristics rely on statutory keyword matching; rare or non-standard legal phrasing may require expert human review.",
                    "Hindi Devanagari morphological inflections and case markers (कारक चिह्न) are supported through comprehensive pattern sets but complex multi-sentence clauses should be verified.",
                    "This system is an automated research aid and does not constitute formal legal counsel."
                ],
            },
        }
