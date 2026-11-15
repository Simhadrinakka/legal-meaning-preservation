"""
Script: training/apply_audit.py
Generates data/annotations/lmp_ai_audited_300.csv with audited annotations
and outputs verification statistics.
"""
import pandas as pd
from pathlib import Path

# Load original AI draft dataset
input_path = Path("data/annotations/lmp_ai_draft_300.csv")
output_path = Path("data/annotations/lmp_ai_audited_300.csv")

df = pd.read_csv(input_path, encoding="utf-8-sig")

# Define the exact audited changes
# Map of pair_id -> {score, decision, error_type, explanation, confidence}
AUDIT_CHANGES = {
    # Category 1: विचारण (trial) -> सुनवाई (hearing) procedural dilution in Hindi
    "LMP_HI_010": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "SCOPE_CHANGE",
        "ai_explanation": (
            "दंड प्रक्रिया संहिता, 1898 के होते हुए भी अपराध का मजिस्ट्रेट द्वारा संक्षिप्त विचारण अनिवार्य ('किया जाएगा') सुरक्षित है। "
            "परंतु प्रक्रियात्मक पद 'विचारण' (trial) को शिथिल करके 'सुनवाई' (hearing) किया गया है, तथा सांविधिक अधिनियम संदर्भ '(1898 का 5)' "
            "छूटा है, जो प्रक्रियात्मक दायरा बदलता है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_035": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "SCOPE_CHANGE",
        "ai_explanation": (
            "राज्य सरकार की शक्ति कार्यपालक मजिस्ट्रेट को न्यायिक मजिस्ट्रेट की शक्तियां सौंपने की सुरक्षित है। "
            "परंतु 'अपराधों के विचारण' (trial of offences) को सामान्य 'सुनवाई' (hearing) में बदला गया है, "
            "तथा संहिता का उद्धरण '(1974 का 2)' छोड़ा गया है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_092": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "SCOPE_CHANGE",
        "ai_explanation": (
            "मजिस्ट्रेट द्वारा संक्षिप्त विचारण अनिवार्य ('किया जाएगा') सुरक्षित है। "
            "किंतु आपराधिक विधिक प्रक्रिया 'संक्षिप्त विचारण' (summary trial) को सामान्य 'सुनवाई' (hearing) से प्रतिस्थापित किया गया है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_147": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "SCOPE_CHANGE",
        "ai_explanation": (
            "परंतुक में 'संक्षिप्त विचारण' को 'संक्षिप्त सुनवाई' में बदला गया है, और सांविधिक आदेश "
            "'मामले की पुनः सुनवाई करने के लिए अग्रसर होगा' (shall proceed to re-hear) को शिथिल करके 'नियमित सुनवाई करेगा' कर दिया गया है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_150": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "SCOPE_CHANGE",
        "ai_explanation": (
            "आश्रित उपखंड में 'विचारण' (trial) को 'सुनवाई' (hearing) में बदला गया है, तथा विधिक पद 'ऋजु' को 'उचित' किया गया है। "
            "मुख्य शासित खंड के अभाव में प्रक्रियात्मक दायरा प्रभावित होता है।"
        ),
        "ai_confidence": "MEDIUM",
    },

    # Category 2: Corrupted source text reconstructions & editorial modifications
    "LMP_HI_022": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "ai_explanation": (
            "मूल राजपत्र पाठ में वर्ष मुद्रण-दोष '886 (886 का 6)' अंकित था; सरलीकरण ने इसे मौन रूप से '1886 (1886 का 6)' पुनर्निर्मित किया है। "
            "यद्यपि ऐतिहासिक संदर्भ से सुसंगत है, प्रदत्त पाठ में यह संख्यात्मक संशोधन है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_033": {
        "ai_lmp_score": 7,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "ai_explanation": (
            "मूल पाठ में धारा संख्या 'धारा 0' मुद्रण-दोष युक्त थी; सरलीकरण ने संपादकीय कोष्ठक जोड़कर इसे 'धारा 10' पुनर्निर्मित किया। "
            "LMP_HI_023 के अनुरूप इसे संख्यात्मक संदर्भ संशोधन के रूप में वर्गीकृत किया गया है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_123": {
        "ai_lmp_score": 7,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "ai_explanation": (
            "मूल सांविधिक पाठ में 'धारा 5' अंकित है; सरलीकरण ने संपादकीय टिप्पणी जोड़कर धारा संदर्भ को 'धारा 15' में बदल दिया है। "
            "प्रदत्त मूल पाठ के सीधे विपरीत संख्यात्मक संशोधन।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_129": {
        "ai_lmp_score": 7,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "ai_explanation": (
            "मूल पाठ में मुद्रण त्रुटि 'धारा !' अंकित है; सरलीकरण ने संपादकीय कोष्ठक जोड़कर 'धारा 11' की संख्यात्मक प्रविष्टि की है। "
            "प्रदत्त स्रोत पाठ से भिन्न संख्यात्मक संदर्भ प्रविष्टि।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_130": {
        "ai_lmp_score": 7,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "ai_explanation": (
            "मूल पाठ में उपधारा कोष्ठक रिक्त था 'उपधारा ()'; सरलीकरण ने संपादकीय टिप्पणी के साथ उपधारा संख्या '(1)' की प्रविष्टि की है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_138": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "ai_explanation": (
            "मूल पाठ में वर्ष मुद्रण दोष '973 (974 का 2)' था; सरलीकरण ने इसे मौन रूप से '1973 (1974 का 2)' के रूप में सुधारा है। "
            "प्रदत्त मूल पाठ की तुलना में संख्यात्मक संशोधन।"
        ),
        "ai_confidence": "MEDIUM",
    },

    # Category 3: Modal weakening in mandatory statutory execution
    "LMP_EN_050": {
        "ai_lmp_score": 7,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "MODALITY_CHANGE",
        "ai_explanation": (
            "The mandatory statutory command that the order 'shall be executed by the court' was softened to "
            "permissive discretion 'may be executed by the court having local jurisdiction', fundamentally weakening "
            "the executing court's mandatory enforcement obligation."
        ),
        "ai_confidence": "HIGH",
    },

    # Category 4: Over-assigned Score 10s with shifted modal phrasing
    "LMP_EN_014": {
        "ai_lmp_score": 9,
        "ai_preservation_decision": "PRESERVED",
        "ai_error_type": "NONE",
        "ai_explanation": (
            "Discharge upon payment of composition sum is preserved. The mandatory prohibition 'no further proceedings "
            "shall be taken' was rendered as 'no further proceedings may be taken'. Legally effective but represents "
            "modal rephrasing rather than near-verbatim preservation (Score 9 instead of 10)."
        ),
        "ai_confidence": "HIGH",
    },
    "LMP_EN_090": {
        "ai_lmp_score": 9,
        "ai_preservation_decision": "PRESERVED",
        "ai_error_type": "NONE",
        "ai_explanation": (
            "Two-year time bar on order-making is preserved. The mandatory prohibition 'no order shall be made' was "
            "rephrased as 'no order may be made'. Faithful paraphrase with minor modal rephrasing (Score 9 instead of 10)."
        ),
        "ai_confidence": "HIGH",
    },
    "LMP_EN_099": {
        "ai_lmp_score": 9,
        "ai_preservation_decision": "PRESERVED",
        "ai_error_type": "NONE",
        "ai_explanation": (
            "Two-year commencement time bar is preserved. The mandatory prohibition 'no such order shall be made' was "
            "rephrased as 'no such order may be made'. Faithful paraphrase with minor modal rephrasing (Score 9 instead of 10)."
        ),
        "ai_confidence": "HIGH",
    },

    # Category 5: Statutory citation omissions, incomplete fragments & ungrounded additions
    "LMP_EN_031": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "NUMERIC_ENTITY_REFERENCE_ERROR",
        "ai_explanation": (
            "Magistrate's summary trial power is preserved, but the simplification dropped the statutory subsection citation "
            "number '(2)', converting a numbered statutory subsection into an unnumbered general proposition."
        ),
        "ai_confidence": "HIGH",
    },
    "LMP_EN_078": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "HALLUCINATION_ADDITION",
        "ai_explanation": (
            "Incomplete fragment specifying appointment of six Members (at least two women). The simplification introduced "
            "'appointed by the Central Government' which was absent in the provided fragment, while the qualification categories remain unsupplied."
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_EN_047": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "OMISSION",
        "ai_explanation": (
            "Incomplete rule-making introductory formula ending in 'namely:—'. While the introductory text is translated, "
            "the entire operative schedule of rule-making powers is omitted in the source passage."
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_EN_116": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "OMISSION",
        "ai_explanation": (
            "Incomplete jurisdictional clause ending with an em-dash ('in any district—'). All territorial venue sub-clauses (a)–(c) "
            "are omitted from the supplied passage."
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_124": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "CONDITION_EXCEPTION_LOSS",
        "ai_explanation": (
            "अपूर्ण वैधानिक खंड जो 'कि:--' पर समाप्त होता है। पूर्ववर्ती शर्त का अनुवाद उपलब्ध है किंतु मुख्य परिणामी अधिकारिता "
            "(उपखंड क और ख) अनुपस्थित है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_127": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "SCOPE_CHANGE",
        "ai_explanation": (
            "अपूर्ण परिणामी खंड जो 'तो' से प्रारंभ होता है (पूर्ववर्ती शर्त अनुपस्थित)। विशेष न्यायालय के अंतरण की शक्ति में "
            "'विशेष न्यायालय' को सामान्य 'विशेष अदालत' में बदला गया है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_137": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "OMISSION",
        "ai_explanation": (
            "अपूर्ण परिचयात्मक खंड जो 'हुए,--' पर समाप्त होता है। अन्वेषण के अंतरण से संबंधित मुख्य सांविधिक निर्देश अनुपस्थित है।"
        ),
        "ai_confidence": "MEDIUM",
    },
    "LMP_HI_144": {
        "ai_lmp_score": 8,
        "ai_preservation_decision": "MOSTLY_PRESERVED",
        "ai_error_type": "OMISSION",
        "ai_explanation": (
            "अपूर्ण नियम-निर्माण परिचयात्मक सूत्र जो 'अर्थात् :--' पर समाप्त होता है। नियम-निर्माण के सभी उपखंड अनुपस्थित हैं।"
        ),
        "ai_confidence": "MEDIUM",
    },
}

# Apply audited changes
df_audited = df.copy()
change_records = []

for idx, row in df_audited.iterrows():
    pid = row["pair_id"]
    if pid in AUDIT_CHANGES:
        change = AUDIT_CHANGES[pid]
        old_score = row["ai_lmp_score"]
        old_decision = row["ai_preservation_decision"]
        old_error = row["ai_error_type"]

        df_audited.at[idx, "ai_lmp_score"] = change["ai_lmp_score"]
        df_audited.at[idx, "ai_preservation_decision"] = change["ai_preservation_decision"]
        df_audited.at[idx, "ai_error_type"] = change["ai_error_type"]
        df_audited.at[idx, "ai_explanation"] = change["ai_explanation"]
        df_audited.at[idx, "ai_confidence"] = change["ai_confidence"]

        change_records.append({
            "pair_id": pid,
            "language": row["language"],
            "act_id": row["act_id"],
            "old_score": old_score,
            "new_score": change["ai_lmp_score"],
            "old_decision": old_decision,
            "new_decision": change["ai_preservation_decision"],
            "old_error_type": old_error,
            "new_error_type": change["ai_error_type"],
            "justification": change["ai_explanation"]
        })

# Set annotation_status to AI_AUDITED
df_audited["annotation_status"] = "AI_AUDITED"

# Save audited CSV
df_audited.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"[SUCCESS] Saved audited annotations to {output_path}")
print(f"Total rows: {len(df_audited)}, Audited changes: {len(change_records)}")
