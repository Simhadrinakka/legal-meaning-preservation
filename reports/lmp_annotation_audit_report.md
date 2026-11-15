# Legal Meaning Preservation (LMP) — Comprehensive Annotation Audit Report

> [!IMPORTANT]
> **Disclaimer on Supervision Status:**
> All annotations documented in this report—including both original and audited labels—are **AI-assisted synthetic drafts** created for model supervision and human-in-the-loop triage. They do **NOT** represent human expert legal ground truth, have not undergone judicial adjudication, and must not be cited as objective gold labels.

---

## 1. Executive Summary

A comprehensive legal and linguistic audit of all **300 statutory passage pairs** across five Central Acts in English (`EN`, N=150) and Hindi (`HI`, N=150) was conducted. The audit specifically investigated the suspicious concentration of 273/300 (91.0%) pairs scored 9.0–10.0 in the initial AI draft.

### Key Audit Outcomes:
- **Total Passages Audited:** 300 / 300 (100% coverage)
- **Scores Changed:** **23 pairs** (7.7%)
- **Scores Unchanged:** **277 pairs** (92.3%)
- **Sub-9.0 Error Detection:** Increased from **27 pairs (9.0%)** to **47 pairs (15.7%)**—a **74.1% increase** in detected legal defects.
- **`PRESERVED` Category:** Re-calibrated from **273 pairs (91.0%)** down to **253 pairs (84.3%)**.
- **`MOSTLY_PRESERVED` Category:** Expanded from **22 pairs (7.3%)** up to **42 pairs (14.0%)**.
- **Overall Mean Score:** Adjusted from **8.96** to **8.87** (English: 8.97, Hindi: 8.77).

---

## 2. Original vs. Audited Distribution Comparisons

### 2.1 Score Distribution (Scale 1–10)

| LMP Score | Original AI Draft | Audited AI Dataset | Net Change | Interpretation & Rubric Band |
| :---: | :---: | :---: | :---: | :--- |
| **4** | 1 (0.3%) | 1 (0.3%) | `0` | MAJOR_LOSS |
| **6** | 4 (1.3%) | 4 (1.3%) | `0` | PARTIALLY_PRESERVED |
| **7** | 3 (1.0%) | 8 (2.7%) | `+5` | MOSTLY_PRESERVED |
| **8** | 19 (6.3%) | 34 (11.3%) | `+15` | MOSTLY_PRESERVED |
| **9** | 241 (80.3%) | 224 (74.7%) | `-17` | PRESERVED |
| **10** | 32 (10.7%) | 29 (9.7%) | `-3` | PRESERVED |

### 2.2 Preservation Decision Distribution

| Preservation Decision | Original Count | Audited Count | Net Change | Percentage (Audited) |
| :--- | :---: | :---: | :---: | :---: |
| **`PRESERVED`** | 273 | 253 | `-20` | 84.3% |
| **`MOSTLY_PRESERVED`** | 22 | 42 | `+20` | 14.0% |
| **`PARTIALLY_PRESERVED`** | 4 | 4 | `0` | 1.3% |
| **`MAJOR_LOSS`** | 1 | 1 | `0` | 0.3% |
| **`FUNDAMENTALLY_ALTERED`** | 0 | 0 | `0` | 0.0% |

### 2.3 Error Type Distribution

| Primary Error Type | Original Count | Audited Count | Net Change | Primary Drivers of Re-Attribution |
| :--- | :---: | :---: | :---: | :--- |
| **`NONE`** | 273 | 253 | `-20` | Re-assigned to specific defect categories upon scrutiny |
| **`SCOPE_CHANGE`** | 12 | 18 | `+6` | Hindi criminal trial ('विचारण') diluted to hearing ('सुनवाई'); jurisdiction transfer |
| **`OMISSION`** | 7 | 11 | `+4` | Incomplete rule-making schedules ('namely:—'); venue clauses omitted |
| **`NUMERIC_ENTITY_REFERENCE_ERROR`** | 3 | 10 | `+7` | Corrupted source citations ('धारा 0', 'धारा !', '886', '973'); dropped subsection '(2)' |
| **`MODALITY_CHANGE`** | 2 | 3 | `+1` | Mandatory civil execution ('shall be executed') softened to discretion ('may be executed') |
| **`CONDITION_EXCEPTION_LOSS`** | 2 | 3 | `+1` | Incomplete conditional clauses ('यदि... कि:--') lacking operative consequence |
| **`HALLUCINATION_ADDITION`** | 1 | 2 | `+1` | Unauthorized insertion of appointing authority in incomplete fragment |
| **`CONTRADICTION`** | 0 | 0 | `0` | Zero contradictions observed across corpus |

---

## 3. Detailed Register of All 23 Changed Annotations

The table below documents every single passage pair where the score, decision, or error type was adjusted during the audit:

| Pair ID | Lang | Act | Old Score / Error | New Score / Error | New Decision | Exact Legal Justification |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| **LMP_EN_014** | `EN` | `1969_18` | 10 (`NONE`) | **9** (`NONE`) | `PRESERVED` | Discharge upon payment of composition sum is preserved. The mandatory prohibition 'no further proceedings shall be taken' was rendered as 'no further proceedings may be taken'. Legally effective but represents modal rephrasing rather than near-verbatim preservation (Score 9 instead of 10). |
| **LMP_EN_031** | `EN` | `1976_19` | 9 (`NONE`) | **8** (`NUMERIC_ENTITY_REFERENCE_ERROR`) | `MOSTLY_PRESERVED` | Magistrate's summary trial power is preserved, but the simplification dropped the statutory subsection citation number '(2)', converting a numbered statutory subsection into an unnumbered general proposition. |
| **LMP_EN_047** | `EN` | `1976_19` | 9 (`NONE`) | **8** (`OMISSION`) | `MOSTLY_PRESERVED` | Incomplete rule-making introductory formula ending in 'namely:—'. While the introductory text is translated, the entire operative schedule of rule-making powers is omitted in the source passage. |
| **LMP_EN_050** | `EN` | `1976_19` | 9 (`NONE`) | **7** (`MODALITY_CHANGE`) | `MOSTLY_PRESERVED` | The mandatory statutory command that the order 'shall be executed by the court' was softened to permissive discretion 'may be executed by the court having local jurisdiction', fundamentally weakening the executing court's mandatory enforcement obligation. |
| **LMP_EN_078** | `EN` | `2006_4` | 9 (`NONE`) | **8** (`HALLUCINATION_ADDITION`) | `MOSTLY_PRESERVED` | Incomplete fragment specifying appointment of six Members (at least two women). The simplification introduced 'appointed by the Central Government' which was absent in the provided fragment, while the qualification categories remain unsupplied. |
| **LMP_EN_090** | `EN` | `2006_4` | 10 (`NONE`) | **9** (`NONE`) | `PRESERVED` | Two-year time bar on order-making is preserved. The mandatory prohibition 'no order shall be made' was rephrased as 'no order may be made'. Faithful paraphrase with minor modal rephrasing (Score 9 instead of 10). |
| **LMP_EN_099** | `EN` | `2007_56` | 10 (`NONE`) | **9** (`NONE`) | `PRESERVED` | Two-year commencement time bar is preserved. The mandatory prohibition 'no such order shall be made' was rephrased as 'no such order may be made'. Faithful paraphrase with minor modal rephrasing (Score 9 instead of 10). |
| **LMP_EN_116** | `EN` | `2007_56` | 9 (`NONE`) | **8** (`OMISSION`) | `MOSTLY_PRESERVED` | Incomplete jurisdictional clause ending with an em-dash ('in any district—'). All territorial venue sub-clauses (a)–(c) are omitted from the supplied passage. |
| **LMP_HI_010** | `HI` | `1969_18` | 9 (`NONE`) | **8** (`SCOPE_CHANGE`) | `MOSTLY_PRESERVED` | दंड प्रक्रिया संहिता, 1898 के होते हुए भी अपराध का मजिस्ट्रेट द्वारा संक्षिप्त विचारण अनिवार्य ('किया जाएगा') सुरक्षित है। परंतु प्रक्रियात्मक पद 'विचारण' (trial) को शिथिल करके 'सुनवाई' (hearing) किया गया है, तथा सांविधिक अधिनियम संदर्भ '(1898 का 5)' छूटा है, जो प्रक्रियात्मक दायरा बदलता है। |
| **LMP_HI_022** | `HI` | `1969_18` | 9 (`NONE`) | **8** (`NUMERIC_ENTITY_REFERENCE_ERROR`) | `MOSTLY_PRESERVED` | मूल राजपत्र पाठ में वर्ष मुद्रण-दोष '886 (886 का 6)' अंकित था; सरलीकरण ने इसे मौन रूप से '1886 (1886 का 6)' पुनर्निर्मित किया है। यद्यपि ऐतिहासिक संदर्भ से सुसंगत है, प्रदत्त पाठ में यह संख्यात्मक संशोधन है। |
| **LMP_HI_033** | `HI` | `1976_19` | 9 (`NONE`) | **7** (`NUMERIC_ENTITY_REFERENCE_ERROR`) | `MOSTLY_PRESERVED` | मूल पाठ में धारा संख्या 'धारा 0' मुद्रण-दोष युक्त थी; सरलीकरण ने संपादकीय कोष्ठक जोड़कर इसे 'धारा 10' पुनर्निर्मित किया। LMP_HI_023 के अनुरूप इसे संख्यात्मक संदर्भ संशोधन के रूप में वर्गीकृत किया गया है। |
| **LMP_HI_035** | `HI` | `1976_19` | 9 (`NONE`) | **8** (`SCOPE_CHANGE`) | `MOSTLY_PRESERVED` | राज्य सरकार की शक्ति कार्यपालक मजिस्ट्रेट को न्यायिक मजिस्ट्रेट की शक्तियां सौंपने की सुरक्षित है। परंतु 'अपराधों के विचारण' (trial of offences) को सामान्य 'सुनवाई' (hearing) में बदला गया है, तथा संहिता का उद्धरण '(1974 का 2)' छोड़ा गया है। |
| **LMP_HI_092** | `HI` | `2007_56` | 9 (`NONE`) | **8** (`SCOPE_CHANGE`) | `MOSTLY_PRESERVED` | मजिस्ट्रेट द्वारा संक्षिप्त विचारण अनिवार्य ('किया जाएगा') सुरक्षित है। किंतु आपराधिक विधिक प्रक्रिया 'संक्षिप्त विचारण' (summary trial) को सामान्य 'सुनवाई' (hearing) से प्रतिस्थापित किया गया है। |
| **LMP_HI_123** | `HI` | `2008_34` | 9 (`NONE`) | **7** (`NUMERIC_ENTITY_REFERENCE_ERROR`) | `MOSTLY_PRESERVED` | मूल सांविधिक पाठ में 'धारा 5' अंकित है; सरलीकरण ने संपादकीय टिप्पणी जोड़कर धारा संदर्भ को 'धारा 15' में बदल दिया है। प्रदत्त मूल पाठ के सीधे विपरीत संख्यात्मक संशोधन। |
| **LMP_HI_124** | `HI` | `2008_34` | 9 (`NONE`) | **8** (`CONDITION_EXCEPTION_LOSS`) | `MOSTLY_PRESERVED` | अपूर्ण वैधानिक खंड जो 'कि:--' पर समाप्त होता है। पूर्ववर्ती शर्त का अनुवाद उपलब्ध है किंतु मुख्य परिणामी अधिकारिता (उपखंड क और ख) अनुपस्थित है। |
| **LMP_HI_127** | `HI` | `2008_34` | 9 (`NONE`) | **8** (`SCOPE_CHANGE`) | `MOSTLY_PRESERVED` | अपूर्ण परिणामी खंड जो 'तो' से प्रारंभ होता है (पूर्ववर्ती शर्त अनुपस्थित)। विशेष न्यायालय के अंतरण की शक्ति में 'विशेष न्यायालय' को सामान्य 'विशेष अदालत' में बदला गया है। |
| **LMP_HI_129** | `HI` | `2008_34` | 9 (`NONE`) | **7** (`NUMERIC_ENTITY_REFERENCE_ERROR`) | `MOSTLY_PRESERVED` | मूल पाठ में मुद्रण त्रुटि 'धारा !' अंकित है; सरलीकरण ने संपादकीय कोष्ठक जोड़कर 'धारा 11' की संख्यात्मक प्रविष्टि की है। प्रदत्त स्रोत पाठ से भिन्न संख्यात्मक संदर्भ प्रविष्टि। |
| **LMP_HI_130** | `HI` | `2008_34` | 9 (`NONE`) | **7** (`NUMERIC_ENTITY_REFERENCE_ERROR`) | `MOSTLY_PRESERVED` | मूल पाठ में उपधारा कोष्ठक रिक्त था 'उपधारा ()'; सरलीकरण ने संपादकीय टिप्पणी के साथ उपधारा संख्या '(1)' की प्रविष्टि की है। |
| **LMP_HI_137** | `HI` | `2008_34` | 9 (`NONE`) | **8** (`OMISSION`) | `MOSTLY_PRESERVED` | अपूर्ण परिचयात्मक खंड जो 'हुए,--' पर समाप्त होता है। अन्वेषण के अंतरण से संबंधित मुख्य सांविधिक निर्देश अनुपस्थित है। |
| **LMP_HI_138** | `HI` | `2008_34` | 9 (`NONE`) | **8** (`NUMERIC_ENTITY_REFERENCE_ERROR`) | `MOSTLY_PRESERVED` | मूल पाठ में वर्ष मुद्रण दोष '973 (974 का 2)' था; सरलीकरण ने इसे मौन रूप से '1973 (1974 का 2)' के रूप में सुधारा है। प्रदत्त मूल पाठ की तुलना में संख्यात्मक संशोधन। |
| **LMP_HI_144** | `HI` | `2008_34` | 9 (`NONE`) | **8** (`OMISSION`) | `MOSTLY_PRESERVED` | अपूर्ण नियम-निर्माण परिचयात्मक सूत्र जो 'अर्थात् :--' पर समाप्त होता है। नियम-निर्माण के सभी उपखंड अनुपस्थित हैं। |
| **LMP_HI_147** | `HI` | `2008_34` | 9 (`NONE`) | **8** (`SCOPE_CHANGE`) | `MOSTLY_PRESERVED` | परंतुक में 'संक्षिप्त विचारण' को 'संक्षिप्त सुनवाई' में बदला गया है, और सांविधिक आदेश 'मामले की पुनः सुनवाई करने के लिए अग्रसर होगा' (shall proceed to re-hear) को शिथिल करके 'नियमित सुनवाई करेगा' कर दिया गया है। |
| **LMP_HI_150** | `HI` | `2008_34` | 9 (`NONE`) | **8** (`SCOPE_CHANGE`) | `MOSTLY_PRESERVED` | आश्रित उपखंड में 'विचारण' (trial) को 'सुनवाई' (hearing) में बदला गया है, तथा विधिक पद 'ऋजु' को 'उचित' किया गया है। मुख्य शासित खंड के अभाव में प्रक्रियात्मक दायरा प्रभावित होता है। |

---

## 4. English vs. Hindi Comparative Analysis

| Metric | English (`EN`, N=150) | Hindi (`HI`, N=150) | Entire Corpus (N=300) |
| :--- | :---: | :---: | :---: |
| **Original Mean Score** | 9.03 | 8.90 | 8.97 |
| **Audited Mean Score** | **8.97** | **8.77** | **8.87** |
| **Audited Scores 9–10 (`PRESERVED`)** | 131 (87.3%) | 122 (81.3%) | 253 (84.3%) |
| **Audited Scores 7–8 (`MOSTLY_PRESERVED`)** | 17 (11.3%) | 25 (16.7%) | 42 (14.0%) |
| **Audited Scores 5–6 (`PARTIALLY_PRESERVED`)** | 1 (0.7%) | 3 (2.0%) | 4 (1.3%) |
| **Audited Scores 3–4 (`MAJOR_LOSS`)** | 1 (0.7%) | 0 (0.0%) | 1 (0.3%) |
| **Audited Error Count (Scores < 9)** | 19 (12.7%) | 28 (18.7%) | 47 (15.7%) |

### Key Linguistic Drivers of English vs. Hindi Differences:
1. **Procedural Terminology Asymmetry in Hindi:** Hindi statutory drafters use high-register terms of art (e.g., *विचारण* for trial, *सुनवाई* for hearing, *संज्ञान* for cognizance, *प्रवृत्त* for enforceable). Simplifications frequently collapsed *विचारण* into *सुनवाई*. In criminal statutes (CrPC, NIA Act), this constitutes a noticeable procedural scope shift.
2. **Corrupted Gazette Source Text Predominance in Hindi:** 32 of the 50 `NEEDS_REVIEW` passages occur in the Hindi corpus, featuring OCR/typesetting anomalies (*धारा 0*, *धारा !*, *886*, *973*, *उपधारा ()*). In the original draft, simplifications that editorialized or corrected these numbers were given lenient 9s; the audit strictly re-classified them as `NUMERIC_ENTITY_REFERENCE_ERROR` in the 7–8 range.
3. **English Deontic Precision:** English simplifications generally retained deontic modals with high fidelity (*must* for *shall*), though the audit detected one critical failure in `LMP_EN_050` where mandatory civil execution (*shall be executed*) was weakened to discretion (*may be executed*).

---

## 5. Was the Original 91% PRESERVED Distribution Justified?

The audit reveals that **the original 91.0% concentration in Scores 9–10 was partially artificial and driven by four distinct forms of AI leniency**:

1. **Leniency on Reconstructed Typographical Errors (6 rows):** In Hindi passages with corrupted Gazette text, the original annotator treated simplifications that 'helpfully' reconstructed corrupt section numbers (*धारा 0* -> *धारा 10*) as flawless (Score 9, `NONE`), while penalizing `LMP_HI_023` to Score 7 for the exact same pattern. The audit restored cross-corpus consistency by assigning Score 7–8 with `NUMERIC_ENTITY_REFERENCE_ERROR`.
2. **Leniency on Legal Terms of Art (5 rows):** The original annotator acknowledged in its report that replacing *विचारण* (trial) with *सुनवाई* (hearing) was 'slightly loose' but gave Score 9. Under strict legal guidelines, shifting a procedural trial stage to a general hearing changes statutory applicability and warrants Score 8 (`SCOPE_CHANGE`).
3. **Leniency on Incomplete Sentence Fragments (7 rows):** Seven truncated rule-making formulas and jurisdictional clauses ending in colons or dashes lacked their entire operative lists. The original pass rated them 9; the audit re-scored them to 8 with `OMISSION` / `HALLUCINATION_ADDITION` / `CONDITION_EXCEPTION_LOSS` because their operative legal effect cannot be verified in isolation.
4. **Leniency on Mandatory Deontic Softening (1 row):** In `LMP_EN_050`, softening *shall be executed* to *may be executed* in civil decree enforcement was overlooked as non-material; the audit properly tagged it as a critical `MODALITY_CHANGE` (Score 7).
5. **Leniency on Score 10 Criteria (3 rows):** Score 10 was assigned to `LMP_EN_014`, `090`, and `099` despite *shall* being rephrased to *may* in negative time bars. The audit adjusted these to Score 9.

> **Verdict:** While roughly **84% of the simplifications in this corpus are indeed faithful and legally sound paraphrases** (justifying high scores), the initial 91% rate resulted from systematic leniency on subtle procedural terms, corrupted citations, and incomplete fragments. The audited rate of **84.3% PRESERVED** and **15.7% with identified defects** reflects a rigorous, legally principled evaluation.

---

## 6. Passages Requiring Human Legal Review

A total of **74 passages** are queued for priority human-in-the-loop legal review, categorized by review rationale:

### 6.1 Critical Legal Drift / Significant Defect (Score <= 7, 13 pairs)
- `LMP_EN_148` (Score 4, `HALLUCINATION_ADDITION`): Statutory immunity clause narrowed by adding unauthorized 'in good faith' qualifier.
- `LMP_EN_045` (Score 6, `SCOPE_CHANGE`): Offence descriptor changed from 'extracting' to 'enforcing' bonded labour.
- `LMP_HI_028` (Score 6, `SCOPE_CHANGE`): Territorial jurisdiction omitted; subjective discretion ('अपने उचित समझे गए') added.
- `LMP_HI_116` (Score 6, `MODALITY_CHANGE`): Enforceability modality softened from mandatory to discretionary.
- `LMP_HI_140` (Score 6, `SCOPE_CHANGE`): Superannuation qualification shift for Special Court judges.
- `LMP_EN_050` (Score 7, `MODALITY_CHANGE`): Mandatory civil execution softened to discretion.
- `LMP_EN_091` (Score 7, `NUMERIC_ENTITY_REFERENCE_ERROR`): Maintenance ceiling rule cross-reference dropped.
- `LMP_EN_121` (Score 7, `OMISSION`): Special Court *suo motu* witness protection power omitted.
- `LMP_HI_023` (Score 7, `NUMERIC_ENTITY_REFERENCE_ERROR`): Reconstructed section reference for 'धारा 0'.
- `LMP_HI_033` (Score 7, `NUMERIC_ENTITY_REFERENCE_ERROR`): Reconstructed section reference for 'धारा 0'.
- `LMP_HI_123` (Score 7, `NUMERIC_ENTITY_REFERENCE_ERROR`): Substituted 'धारा 15' for original 'धारा 5'.
- `LMP_HI_129` (Score 7, `NUMERIC_ENTITY_REFERENCE_ERROR`): Reconstructed 'धारा 11' for original 'धारा !'.
- `LMP_HI_130` (Score 7, `NUMERIC_ENTITY_REFERENCE_ERROR`): Supplied subsection '(1)' for blank 'उपधारा ()'.

### 6.2 Procedural Term of Art Dilution (Score 8, 6 pairs)
- `LMP_HI_010`, `LMP_HI_035`, `LMP_HI_092`, `LMP_HI_122`, `LMP_HI_147`, `LMP_HI_150` (*विचारण* -> *सुनवाई*). Reviewers should decide project policy on whether 'hearing' is acceptable plain Hindi for criminal 'trial'.

### 6.3 Reconstructed Typographical Years (Score 8, 2 pairs)
- `LMP_HI_022` ('886' -> '1886') and `LMP_HI_138` ('973' -> '1973'). Reviewers should establish formal policy on whether correcting obvious Gazette printing errors counts as an error or valid cleaning.

### 6.4 Incomplete Statutory Fragments (Score 8, 7 pairs)
- `LMP_EN_047`, `LMP_EN_078`, `LMP_EN_116`, `LMP_HI_124`, `LMP_HI_127`, `LMP_HI_137`, `LMP_HI_144`. Reviewers should confirm evaluation policy for passages that terminate in colons or dashes without their operative lists.

---

## 7. Remaining Limitations and Recommendations for Model Training

1. **Weak Supervision Nature of AI-Audited Labels:** The audited dataset (`lmp_ai_audited_300.csv`) represents high-quality *AI-assisted supervision targets*, not gold labels validated by human legal scholars. The `human_*` columns remain completely blank.
2. **Remaining Class Imbalance:** Although sub-9.0 errors increased from 27 to 47 pairs (+74%), 84.3% of passages remain `PRESERVED` (Score >= 9). Downstream model training must employ weighted loss functions or focal loss to prevent the model from collapsing to a trivial 'always predict 9' majority classifier.
3. **Handling of NEEDS_REVIEW Rows in Training:** The 50 `NEEDS_REVIEW` passages should either be excluded from initial training (Option A: `train_clean.csv`) or down-weighted using `sample_weight_soft` (Option B) to avoid reinforcing noise from incomplete fragments.
4. **Human Validation Next Step:** Priority human review should adjudicate the 13 critical cases (Section 6.1) and the project policy questions regarding Hindi legal terminology and Gazette typos.