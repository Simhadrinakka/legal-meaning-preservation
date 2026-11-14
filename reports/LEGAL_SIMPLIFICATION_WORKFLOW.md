# Controlled Legal Simplification Workflow Protocol

**Project:** Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT  
**Document:** Operational Workflow for Preparing Plain-Language Legal Passages  
**Target Dataset:** 300-Pair Human-Annotated LMP Corpus (`data/annotations/lmp_annotation_template.csv`)  
**Reference Guidelines:** `reports/LMP_ANNOTATION_GUIDELINES.md`  
**Date:** November 2026  

---

## 1. Executive Summary & Objective

This document defines the controlled, reproducible methodology for generating plain-language simplified versions of the 300 authentic English and Hindi statutory passages in our annotation corpus. 

Simplifying legal text for non-specialists is a high-risk NLP task. If a plain-language rewrite inadvertently weakens a mandatory obligation, drops an exception, or broadens legal liability, it causes severe real-world harm. This workflow establishes strict separation between drafting, verification, and independent evaluation to guarantee that every simplified passage remains **legally sound, normative, and faithful** to the statutory original.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                      THE THREE DISTINCT ARTIFACTS                             │
├───────────────────────────────────────────────────────────────────────────────┤
│ 1. ORIGINAL STATUTORY TEXT                                                    │
│    • Authentic primary law from official Indian enactments (Gazette of India).│
│    • IMMUTABLE: Never modified, edited, or overwritten.                       │
│                                                                               │
│ 2. SIMPLIFIED TEXT                                                            │
│    • Plain-language rewrite produced by the Simplifier and verified by the     │
│      Reviewer.                                                                │
│    • Replaces archaic syntax with clear language while strictly preserving     │
│      every legal invariant.                                                   │
│                                                                               │
│ 3. HUMAN LMP SCORE & ERROR TAXONOMY                                           │
│    • Assigned INDEPENDENTLY by human Annotators on a 1.0–10.0 scale.          │
│    • Never assigned by the Simplifier; never auto-generated.                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. End-to-End Simplification Procedure

Simplification must follow a disciplined, four-phase analytical process. Simplifiers must not simply paraphrase sentences ad-hoc.

```
    Phase 1               Phase 2                 Phase 3                Phase 4
┌──────────────┐     ┌──────────────┐      ┌─────────────────┐     ┌─────────────────┐
│ Statutory    │ ──> │ Invariant    │ ───> │ Controlled      │ ──> │ Peer Quality    │
│ Context &    │     │ Extraction & │      │ Plain-Language  │     │ Review & Pre-   │
│ Deconstruc-  │     │ Boundary     │      │ Drafting        │     │ Annotation Sign-│
│ tion         │     │ Mapping      │      │ (Same Language) │     │ Off             │
└──────────────┘     └──────────────┘      └─────────────────┘     └─────────────────┘
```

### Phase 1: Statutory Context & Deconstruction
1. **Analyze the Full Provision:** Read the passage in its complete statutory context (Act, Section, Subsection, and Heading).
2. **Contextual Completeness:** If the passage is a dependent sub-clause (e.g., *"(m) any other matter which has to be, or may be, prescribed"*), locate the parent clause to ensure the governing actor and power (*"The Central Government may make rules for..."*) are understood. Do not simplify isolated fragments in a conceptual vacuum.

### Phase 2: Invariant Extraction & Boundary Mapping
Before drafting, identify and catalogue the specific legal elements present:
- **Deontic Modals:** Mandatory (*shall, must*) vs. Discretionary (*may, is authorized*).
- **Prohibitions:** Negative obligations (*shall not, no person shall*).
- **Conditions & Provisos:** Trigger events (*provided that, subject to, if, unless*).
- **Exceptions:** Carve-outs (*except, save as otherwise provided*).
- **Scope:** Territorial (*Jammu and Kashmir*), temporal (*commencement*), and institutional boundaries.
- **Parties & Entities:** Exact titles (*Registrar-General, Child Welfare Committee, Court of Session*).
- **Numbers & Durations:** Quantities, limitation periods, age limits, and fines (*3 years, 2,000 rupees*).
- **Statutory Cross-References:** Citations to other codes (*under section 154 of the Code*).
- **Penalties & Liabilities:** Exact punitive outcomes (*imprisonment of either description, fine, or both*).

### Phase 3: Controlled Plain-Language Drafting
Draft the simplified text adhering to these core rules:
- **Language Preservation (Intra-Lingual Only):**
  - English original $\rightarrow$ **Simplified English**.
  - Hindi original $\rightarrow$ **Simplified Hindi**.
  - *Never translate between languages during simplification.* Translation and simplification are separate linguistic tasks.
- **Syntactic Restructuring:**
  - Break long, nested compound sentences into two or three shorter sentences.
  - Move conditions to the front of sentences so readers see prerequisites first (*"If X happens, then the officer must do Y"*).
  - Use active voice where the actor is clear (*"The police officer must submit..."* instead of *"The report shall be submitted by..."*).
  - Replace archaic Latinate terms (*hereinafter, aforesaid, inter alia*) with modern terms.
- **Absolute Prohibition on Extrapolation:**
  - Do **NOT** add interpretations, hypothetical examples, advice, or real-world opinions.
  - Do **NOT** add legal claims, defenses, or rights that are not explicitly stated in the statutory text.

### Phase 4: Peer Quality Review
Submit the draft simplification to the Reviewer for invariant verification against the Quality Checklist.

---

## 3. Quality-Review Checklist

Based on the official rubric in `reports/LMP_ANNOTATION_GUIDELINES.md`, the Reviewer must verify that each legal invariant is fully preserved before any simplified text is approved for annotation.

### Invariant Verification Table

| Invariant Checked | Verification Question | Action if Violated |
| :--- | :--- | :--- |
| **1. Deontic Modals** | Does mandatory stay mandatory (*shall* $\rightarrow$ *must/will*) and discretionary stay discretionary (*may* $\rightarrow$ *can/may*)? | **Immediate Rejection:** Modal drift alters legal duty. |
| **2. Prohibitions** | Are negative commands (*shall not*) preserved with zero ambiguity? | **Immediate Rejection:** Permitting a prohibited act is fatal. |
| **3. Conditions & Provisos** | Are all statutory triggers (*provided that, if, subject to*) preserved? | **Immediate Rejection:** Dropping conditions broadens liability. |
| **4. Statutory Exceptions** | Are all carve-outs and non-obstante overrides preserved? | **Immediate Rejection:** Eliminating exceptions alters legal scope. |
| **5. Parties & Entities** | Are official bodies, officers, and legal capacities accurately named? | **Reject if ambiguous:** e.g., changing *Court of Session* to generic *Court*. |
| **6. Numbers & Deadlines** | Are all time periods, age limits, fines, and quantities exactly equal? | **Immediate Rejection:** Changing *30 days* or *3 years* invalidates law. |
| **7. Penal Sanctions** | Are imprisonment types, durations, and cumulative/disjunctive fines exact? | **Immediate Rejection:** Inaccurate penalty misstates criminal risk. |
| **8. Language Match** | Is the language identical to the source (English $\rightarrow$ English; Hindi $\rightarrow$ Hindi)? | **Immediate Rejection:** No cross-lingual translation permitted. |
| **9. No Extraneous Content** | Did the drafter refrain from adding legal advice, opinions, or commentary? | **Immediate Rejection:** Simplifications must remain objective law. |

> [!CAUTION]
> **Rejection Rule:** If any check fails, the Reviewer must reject the draft and return it to the Simplifier with specific feedback. Only clean drafts proceed to independent annotation.

---

## 4. Roles and Separation of Concerns

To guarantee academic rigor and prevent confirmation bias, team roles are strictly segregated:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   SIMPLIFIER    │ ────> │    REVIEWER     │ ────> │    ANNOTATOR    │
│  (Drafts plain  │       │ (Audits legal   │       │  (Independently │
│   language)     │       │  invariants)    │       │   scores LMP)   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                             │
                                                             ▼ (If Disagreement >= 3.0)
                                                    ┌─────────────────┐
                                                    │   ADJUDICATOR   │
                                                    │ (Final decision │
                                                    │  & precedent)   │
                                                    └─────────────────┘
```

1. **Simplifier:**
   - Deconstructs statutory provisions and drafts plain-language rewrites.
   - Responsible for readability and intra-lingual clarity.
   - **Restriction:** Must *never* assign LMP scores or annotate their own drafts.
2. **Reviewer:**
   - Performs objective pre-annotation auditing using the Quality-Review Checklist.
   - Verifies that no legal invariant was compromised.
   - Approves passage for annotation or flags issues for re-drafting.
   - **Restriction:** Must not evaluate texts they simplified.
3. **Annotator:**
   - Receives approved pairs in `data/annotations/lmp_annotation_template.csv`.
   - Independently scores Legal Meaning Preservation on the **1.0 to 10.0 scale** using `reports/LMP_ANNOTATION_GUIDELINES.md`.
   - Categorizes error type (`NONE`, `MODAL_DRIFT`, `OMISSION`, etc.) and documents scoring notes.
   - **Restriction:** Annotators must work independently without consulting the Simplifier.
4. **Adjudicator (Senior Researcher / Legal Specialist):**
   - Resolves edge cases where independent annotators diverge by $\ge 3.0$ points.
   - Reviews pairs tagged with `[UNCERTAIN]` and establishes authoritative binding precedents.

---

## 5. The 10-Passage Pilot Calibration Study

Before scaling simplification to all 300 passages in the dataset, the team must execute a **10-passage pilot study** (5 English, 5 Hindi) drawn across all 5 Central Acts.

### 5.1 Selected Pilot Passages

The pilot utilizes 10 specific entries already present in `data/annotations/lmp_annotation_template.csv`:

| Task ID | Lang | Act ID | Act Title | Statutory Provision Theme |
| :--- | :---: | :---: | :--- | :--- |
| `LMP_EN_001` | `EN` | `1969_18` | Registration of Births and Deaths Act, 1969 | Rule-making delegated power clause |
| `LMP_EN_031` | `EN` | `1976_19` | Bonded Labour System (Abolition) Act, 1976 | Summary trial jurisdiction of Magistrates |
| `LMP_EN_061` | `EN` | `2006_4` | Commissions for Protection of Child Rights Act, 2005 | Salaries and terms of service of Commission |
| `LMP_EN_091` | `EN` | `2007_56` | Maintenance and Welfare of Parents & Senior Citizens Act, 2007 | Maximum maintenance allowance ceiling |
| `LMP_EN_121` | `EN` | `2008_34` | National Investigation Agency Act, 2008 | Special Court power to transfer cases |
| `LMP_HI_001` | `HI` | `1969_18` | Registration of Births and Deaths Act, 1969 | Proviso on birth/death reporting duty |
| `LMP_HI_031` | `HI` | `1976_19` | Bonded Labour System (Abolition) Act, 1976 | Extinguishment of hereditary debt liability |
| `LMP_HI_061` | `HI` | `2006_4` | Commissions for Protection of Child Rights Act, 2005 | Validity of Commission proceedings |
| `LMP_HI_091` | `HI` | `2007_56` | Maintenance and Welfare of Parents & Senior Citizens Act, 2007 | Service of notice on persons outside India |
| `LMP_HI_121` | `HI` | `2008_34` | National Investigation Agency Act, 2008 | Statutory interpretation of repealed enactments |

> [!NOTE]
> Selecting these 10 passages does **not** alter the sampling seed or structure of `lmp_annotation_template.csv`. The CSV file remains untouched until the pilot review is formally signed off.

### 5.2 Pilot Review and Calibration Steps
1. **Drafting:** The Simplifier prepares plain-language versions for the 10 pilot passages.
2. **Review:** The Reviewer applies the Quality-Review Checklist to all 10 drafts.
3. **Independent Dual Scoring:** Two Annotators independently score each pilot pair on the 1.0–10.0 scale and assign error categories.
4. **Inter-Annotator Agreement (IAA) Calculation:** Calculate Pearson's $r$, Spearman's $\rho$, and Cohen's $\kappa$ across the scores.
5. **Team Retrospective:** The team meets to resolve discrepancies, refine edge-case rules, and calibrate scoring standards before expanding to the remaining 290 passages.

---

## 6. Dataset Integrity & Governance Rules

To maintain scientific integrity for our NLP project:
1. **Source Immutability:** Never overwrite, truncate, or rephrase the `original_text` column. It is our ground-truth statutory anchor.
2. **No Automated Score Guessing:** Do not use heuristic scripts, LLM self-evaluation, or simulated metrics to populate `lmp_score`. Scores must represent genuine human evaluation.
3. **Provenance & Attribution:** Every completed row must record `annotator_id` and brief qualitative justifications in `annotation_notes`.
4. **Uncertainty Logging:** Any passage involving unsettled statutory interpretation must be flagged with `[UNCERTAIN: <Reason>]` in `annotation_notes`.
5. **Version Control Discipline:** The annotation CSV must be version-tracked in Git only upon reaching validated milestones (e.g., post-pilot, 50% completion, 100% completion).

---

## 7. Worked Example (Fictional Rule)

The following example demonstrates how a statutory provision is deconstructed and simplified, and how the invariant checklist is verified.

> [!IMPORTANT]
> This example is **entirely fictional** and created solely for instructional modeling. It is **NOT** from the dataset, and per protocol, **no LMP score is assigned** at the drafting stage.

### 7.1 Original Statutory Text (Fictional)
> *"Section 14(2): If any commercial carrier fails to secure a transit permit under sub-section (1) prior to transporting timber across an interstate border, the designated inspecting officer shall impound the vehicle and timber forthwith, and the owner thereof shall be liable to a civil fine of ten thousand rupees: Provided that where such failure is occasioned by natural disaster or highway blockade, the officer may grant a waiver of twenty-four hours."*

### 7.2 Draft Simplified Text (Plain Language)
> *"Under Section 14(2), commercial transport companies must obtain a transit permit before moving timber across a state border. If a carrier fails to get this permit, the inspecting officer must immediately seize both the vehicle and the timber, and the vehicle owner must pay a fine of 10,000 rupees. However, if the permit was missed because of a natural disaster or road blockade, the officer has discretion to give the carrier a 24-hour extension."*

### 7.3 Reviewer Invariant Checklist

| Invariant | Original Statutory Element | Simplified Text Element | Status |
| :--- | :--- | :--- | :---: |
| **Mandatory Duty 1** | *carrier fails to secure... permit prior to transporting* | *must obtain a transit permit before moving timber* | **Preserved** |
| **Mandatory Sanction 2** | *officer shall impound... forthwith* | *officer must immediately seize...* | **Preserved** |
| **Items Seized** | *the vehicle and timber* | *both the vehicle and the timber* | **Preserved** |
| **Mandatory Fine** | *owner thereof shall be liable to... ten thousand rupees* | *owner must pay a fine of 10,000 rupees* | **Preserved** |
| **Proviso / Exception** | *Provided that where... natural disaster or highway blockade* | *However, if... because of a natural disaster or road blockade* | **Preserved** |
| **Discretionary Power** | *officer may grant a waiver* | *officer has discretion to give...* | **Preserved** |
| **Exact Deadline** | *twenty-four hours* | *24-hour extension* | **Preserved** |
| **Target Entities** | *commercial carrier, inspecting officer, owner* | *commercial transport companies, carrier, inspecting officer, owner* | **Preserved** |

*Conclusion:* The Reviewer signs off on this draft as ready for independent annotation.

---

## 8. Pilot Acceptance Criteria

The team may proceed to full-scale simplification and annotation of the 300-passage dataset **ONLY** when all of the following conditions are met:

- [ ] **1. Complete 10-Passage Drafts:** Plain-language simplifications are written for all 10 pilot passages (5 English, 5 Hindi).
- [ ] **2. Invariant Sign-Off:** The Reviewer has audited every pilot passage against the 9-point Quality-Review Checklist.
- [ ] **3. Zero Critical Legal Meaning Shifts:** No approved pilot draft contains altered modals (*shall* $\leftrightarrow$ *may*), omitted conditions, or corrupted penalties.
- [ ] **4. Explicit Uncertainty Tagging:** Any ambiguous passages carry structured `[UNCERTAIN: ...]` documentation in `annotation_notes`.
- [ ] **5. Independent Dual Scoring Complete:** At least two annotators have independently assigned 1.0–10.0 LMP scores to the pilot pairs without consultation.
- [ ] **6. High Inter-Annotator Agreement:** Pearson correlation $r \ge 0.75$ between independent pilot annotators, with disagreements $\ge 3.0$ adjudicated.
- [ ] **7. Formal Team Authorization:** The Project Lead and NLP Team formally approve the calibration before opening the remaining 290 pairs.

