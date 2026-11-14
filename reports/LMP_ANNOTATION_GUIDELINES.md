# Legal Meaning Preservation (LMP) Annotation Guidelines

**Project:** Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT  
**Document:** Official Human Annotation & Quality Assessment Protocol  
**Scale:** 1.0 – 10.0 Integer / Continuous Scoring Scale  
**Applicability:** English (`EN`) and Hindi (`HI`) Statutory Legal Simplification Tasks  

---

## 1. Overview and Core Philosophy

The goal of this project is to evaluate how accurately a plain-language legal simplification preserves the authentic legal force, obligations, rights, and conditions of an original statutory passage.

### Meaning Preservation vs. Lexical Similarity
Annotators must evaluate **substantive legal meaning**, **NOT surface-level wording similarity**:
- **High Lexical Overlap $\neq$ High Legal Meaning:** A simplified passage that retains 95% of original words but alters *"shall"* to *"may"* has high lexical overlap but suffers a **catastrophic legal distortion** (changing a non-negotiable legal command into voluntary discretion).
- **Low Lexical Overlap $\neq$ Low Legal Meaning:** A passage that replaces archaic legalese (*"hereinafter referred to as"*, *"without prejudice to the generality of the foregoing"*) with direct, modern prose may share very few n-grams with the source, but achieves **near-perfect legal preservation**.

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    THE CORE ANNOTATION PRINCIPLE                          │
│                                                                           │
│   "Does the simplified text produce the EXACT SAME legal consequence,     │
│    bind the same parties, establish identical rights and obligations,     │
│    and apply under the same exact conditions as the statutory source?"    │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The 7 Essential Legal Invariants

When simplifying a statute, plain language is encouraged, but legal force must never be compromised. Annotators must inspect every pair for the preservation of these seven invariants:

1. **Obligations and Permissions (Deontic Modals)**
   - *Obligations (Mandatory):* Words such as *"shall"*, *"must"*, *"is required to"*, and Hindi *"होगा"*, *"करेगा"*, *"बाध्य होगा"*. Simplification must not weaken these into suggestions.
   - *Permissions (Discretionary):* Words such as *"may"*, *"is authorized to"*, *"at its discretion"*, and Hindi *"सकेगा"*, *"अनुज्ञात होगा"*. Simplification must not harden these into mandatory commands.
2. **Prohibitions**
   - Negative commands such as *"shall not"*, *"no person shall"*, *"prohibited"*, and Hindi *"नहीं करेगा"*, *"प्रतिषिद्ध"*, *"कोई व्यक्ति नहीं..."*. Prohibitions must remain absolute and unequivocal.
3. **Conditions and Exceptions (Provisos & Non-Obstante Clauses)**
   - Preconditions (*"Provided that"*, *"Subject to"*, *"Where"*, *"यदि"*, *"जब तक कि"*).
   - Exemptions (*"Except"*, *"Save as otherwise provided"*, *"को छोड़कर"*, *"के सिवाय"*).
   - Overriding clauses (*"Notwithstanding anything contained in..."*, *"के होते हुए भी"*).
   - Omitting an exception unlawfully broadens legal liability.
4. **Scope and Applicability**
   - Territorial limits (e.g., *"whole of India except..."*, *"within a registration division"*).
   - Temporal thresholds (e.g., *"on or after the commencement of this Act"*, *"within sixty days"*).
   - Institutional boundaries (e.g., applying only to *"scheduled offences"* or *"custodial institutions"*).
5. **Parties and Legal Entities**
   - Precise identification of rights-holders, duty-bearers, and authorities (e.g., *"Registrar-General"*, *"Child Welfare Committee"*, *"Court of Session"*, *"relative"*, *"guardian"*).
   - Replacing a specific legal authority with a generic term (e.g., replacing *"Special Court"* with *"any court"*) is a critical defect.
6. **Numbers, Dates, Deadlines, and Statutory References**
   - Strict numerical fidelity: age cutoffs (*"18 years"*), limitation periods (*"30 days"*, *"3 months"*), quorum sizes, monetary fines (*"five thousand rupees"*).
   - Statutory citations: cross-references to other sections (e.g., *"under section 154 of the Code"*) must be accurately identified or functionally preserved.
7. **Penalties and Legal Consequences**
   - Exact nature of sanctions: imprisonment type (*"simple or rigorous"*), sentence duration (*"extend to 3 years"*), cumulative or disjunctive fines (*"and also with fine"* vs. *"or with both"*), civil invalidation, or asset forfeiture.

---

## 3. Official LMP Scoring Rubric (1–10 Scale)

Annotators assign a single composite score from **1.0 to 10.0** reflecting the degree of legal meaning preservation.

| Score Band | Category | Legal Description & Decision Criteria |
| :---: | :--- | :--- |
| **9.0 – 10.0** | **Fully or Almost Fully Preserved** | **Zero legal discrepancy.** All obligations, rights, conditions, exceptions, entities, and penalties are completely preserved. The simplification achieves clarity without sacrificing any legal nuance or statutory consequence. |
| **7.0 – 8.9** | **Mostly Preserved with Minor Loss** | **Negligible legal impact.** Minor stylistic dilution or minor non-substantive omission that does not change the rights, duties, or liabilities of any party. A judge or legal practitioner would reach identical legal conclusions. |
| **5.0 – 6.9** | **Partial Preservation with Important Omissions** | **Noticeable legal drift.** One non-critical condition omitted, a minor ambiguity introduced regarding deadlines, or imprecise entity naming that could cause confusion. Core intent is recognizable, but legal precision is compromised. |
| **3.0 – 4.9** | **Major Legal Meaning Loss** | **Significant distortion of rights/duties.** Critical exception or proviso dropped; modality altered (e.g., *"shall"* rendered as *"should"*); substantial change in penalty bounds; or material narrowing/broadening of applicability. |
| **1.0 – 2.9** | **Meaning Largely Lost / Fundamentally Altered** | **Critical failure / legal contradiction.** Inversion of liability; command negated; fabricated legal right or duty (hallucination); total omission of penal consequences; or severe statutory misstatement. Legally misleading or dangerous. |

---

## 4. Error Taxonomy and Classification

When assigning an LMP score below 9.0, annotators must tag the primary error in the `error_type` column using one of the following standard categories:

1. **`OMISSION`**
   - A material legal element present in the original is completely absent in the simplified text (e.g., omitting the penalty clause or failing to mention that parents must be unable to maintain themselves).
2. **`HALLUCINATION_ADDITION`**
   - The simplified text introduces new rights, duties, procedures, or conditions not present or implied in the original statute.
3. **`CONTRADICTION`**
   - The simplified text directly asserts the opposite or mutually exclusive legal outcome (e.g., stating an act is lawful when the statute explicitly prohibits it).
4. **`MODALITY_CHANGE`**
   - Distortion of deontic modal force:
     - Weakening a statutory obligation into discretion (*"shall" $\rightarrow$ "may"* / *"can"* / *"should"*).
     - Converting executive discretion into an absolute command (*"may" $\rightarrow$ "must"*).
     - Diluting a statutory prohibition into voluntary avoidance.
5. **`CONDITION_EXCEPTION_LOSS`**
   - Dropping provisos, preconditions, jurisdictional bars, or qualifying clauses (e.g., removing *"unless the context otherwise requires"* or omitting *"provided the child is not a minor"*).
6. **`SCOPE_CHANGE`**
   - Altering the geographical, institutional, or demographic applicability (e.g., turning a law applicable only to *"Special Courts"* into a general law for *"all courts"*, or expanding a provision for *"senior citizens"* to *"all citizens"*).
7. **`NUMERIC_ENTITY_REFERENCE_ERROR`**
   - Errors in numerical figures, time periods, monetary fines, official titles, or statutory cross-references (e.g., changing *"three years"* to *"two years"*, or mistranslating *"Registrar"* as *"Magistrate"*).

*Note:* If the score is 9.0 or higher with no material error, record `error_type` as **`NONE`**.

---

## 5. Multilingual Considerations: English and Hindi

### 5.1 English Considerations
- **Archaic Syntax & Subordinate Provisos:** English statutes frequently feature multi-layered sentences with nested provisos (*"Provided further that..."*). Simplification often breaks these into shorter sentences; annotators must verify that the conditional link between the main clause and the proviso is preserved.
- **Deontic Nuance:** Distinguish between *"shall"* (mandatory), *"may"* (discretionary), and *"deemed to be"* (legal fiction).

### 5.2 Hindi Considerations
- **High-Register Sanskritized Legal Vocabulary (*राजभाषा विधिक शब्दावली*):**
  Official Hindi enactments use standardized terminology. A simplification may replace obscure Sanskrit terms with simpler words, provided the legal meaning does not slip:
  - *उत्सादन* (Abolition) $\rightarrow$ Plain: *समाप्त करना* (**Acceptable** if total legal end is conveyed).
  - *उन्मोचन* (Discharge) $\rightarrow$ Plain: *मुक्त करना / जिम्मेदारी से बरी करना* (**Acceptable**).
  - *संज्ञान* (Cognizance) $\rightarrow$ Plain: *मामले की सुनवाई / संज्ञान लेना* (**Caution:** must not imply trial completion).
  - *अभिप्रेत है* (Means) vs. *अन्तर्गत है* (Includes): *"अभिप्रेत"* denotes an exhaustive definition; *"अन्तर्गत"* denotes an illustrative/inclusive definition. Conflating the two is an error.
- **Hindi Modality Markers:**
  - Mandatory: *होगा*, *करेगा*, *बाध्य होगा*, *अपेक्षित होगा*.
  - Discretionary: *सकेगा*, *अनुज्ञात होगा*, *अधिकार होगा*.
  - Substituting *सकेगा* for *होगा* represents a serious `MODALITY_CHANGE`.
- **Punctuation and Dandas:**
  - Devanagari Danda (`।`) functions as a full stop; Double Danda (`॥`) marks structural completion. Ensure sentence-boundary simplifications in Hindi do not alter the relationship between statutory clauses.

---

## 6. Illustrative Evaluation Examples

> [!IMPORTANT]
> The three examples below are strictly **illustrative benchmark scenarios** provided to train annotators on the scoring scale and error taxonomy. They are **NOT** taken from the annotation dataset.

---

### Illustrative Example 1: Full Legal Meaning Preservation
- **Original Passage (English):**  
  *"Whoever, after the commencement of this Act, compels any person to render any bonded labour shall be punishable with imprisonment for a term which may extend to three years and also with fine which may extend to two thousand rupees."*
- **Simplified Candidate:**  
  *"Anyone who forces a person to do bonded labour after this law begins will be punished with up to three years in prison, and must also pay a fine of up to two thousand rupees."*
- **Annotation Assessment:**
  - **LMP Score:** **9.5 / 10.0**
  - **Error Type:** `NONE`
  - **Justification:** Perfect preservation of legal force. The mandatory penalty (*"will be punished"*), sentence ceiling (*"up to three years"*), mandatory cumulative fine (*"and must also pay"*), and temporal condition (*"after this law begins"*) are completely intact despite modern simplified phrasing.

---

### Illustrative Example 2: Partial Preservation with Important Omission
- **Original Passage (Hindi):**  
  *"कोई वरिष्ठ नागरिक, जिसके अन्तर्गत माता-पिता हैं, जो स्वयं के अर्जन से या उसके स्वामित्वाधीन संपत्ति में से स्वयं का भरणपोषण करने में असमर्थ है, अपने एक या अधिक बालकों के विरुद्ध, जो अवयस्क नहीं हैं, भरणपोषण के लिए आवेदन करने का हकदार होगा।"*
- **Simplified Candidate:**  
  *"वरिष्ठ नागरिक और माता-पिता अपने भरण-पोषण के लिए अपने बच्चों के खिलाफ आवेदन दे सकते हैं।"*
- **Annotation Assessment:**
  - **LMP Score:** **5.5 / 10.0**
  - **Error Type:** `CONDITION_EXCEPTION_LOSS`
  - **Justification:** Two major statutory preconditions were omitted: (1) the condition that the claimant must be *unable to maintain themselves from their own earnings or property*, and (2) the restriction that claims can only be filed against adult children (*"जो अवयस्क नहीं हैं"*). Omitting these conditions fundamentally expands the eligible applicant pool and allows lawsuits against minors, causing substantial legal drift.

---

### Illustrative Example 3: Severe Distortion / Critical Failure
- **Original Passage (English):**  
  *"On receipt of information under section 154 of the Code relating to any Scheduled Offence, the officer-in-charge of the police station shall forward the report to the State Government forthwith."*
- **Simplified Candidate:**  
  *"When a police officer receives a report about a crime, they may send the report to the State Government if they consider it necessary."*
- **Annotation Assessment:**
  - **LMP Score:** **1.5 / 10.0**
  - **Error Type:** `MODALITY_CHANGE`
  - **Justification:** Three critical legal failures: (1) The mandatory statutory duty (*"shall forward... forthwith"*) is degraded into subjective discretion (*"may send... if they consider it necessary"*); (2) The promptness requirement (*"forthwith"* / immediate) is erased; (3) The scope is erroneously dilated from specific *"Scheduled Offences"* under the Act to any general *"crime"*.

---

## 7. Protocol for Flagging Uncertain Cases and Adjudication

Legal interpretation can occasionally involve genuine textual ambiguity. Annotators should follow this protocol when uncertain:

1. **Do Not Guess Arbitrarily:** If the legal scope of a simplified rephrasing is genuinely ambiguous, do not assign a rushed score.
2. **Flagging Mechanism in `annotation_notes`:**
   Prefix the qualitative notes with the tag `[UNCERTAIN: <Issue>]`.
   *Example:*
   ```text
   [UNCERTAIN: Entity Ambiguity] Original specifies 'Court of Session', simplified uses 'District Court'. In this state, the Court of Session is situated in the District Court complex, but the jurisdictional capacity differs. Request legal review.
   ```
3. **Dual-Annotator Review:**
   - Any pair flagged with `[UNCERTAIN]` or where independent annotators differ by $\ge 3.0$ points is automatically queued for secondary adjudication by the project legal supervisor.
4. **Resolution:**
   - Adjudicated cases will be documented in project notes to maintain a consistent interpretation precedent across the entire corpus.

