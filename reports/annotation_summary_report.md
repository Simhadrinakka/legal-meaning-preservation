# LMP AI-Assisted Annotation — Summary Report

**Status:** AI-assisted annotation *drafts* for human verification. Not independent human gold labels, and not objectively validated.

## 1. Coverage and validation
- Rows annotated: **300 / 300** (150 EN, 150 HI; 60 per Act). All pair IDs unique, original order kept.
- Validation failures: **none**. Checked: schema identical to workspace; `pair_id`, `language`, `act_id`, `original_text`, `simplified_text`, `context_note`, `simplification_status` byte-identical to master and draft; human fields blank on all rows; scores integer 1–10; decision matches score band; error labels in the allowed set; no 9–10 with an error label and no score <9 labelled `NONE`; `annotation_status = AI_DRAFTED` on all rows.
- Batches saved in `batches/` (6 files × 50 rows: EN_001–050 … HI_101–150). Annotation itself was done in 25-row reading batches.

## 2. Score distribution (1–10)
| Score | Rows |
|---|---|
| 4 | 1 |
| 6 | 4 |
| 7 | 3 |
| 8 | 19 |
| 9 | 241 |
| 10 | 32 |

| Decision | Rows |
|---|---|
| PRESERVED | 273 |
| MOSTLY_PRESERVED | 22 |
| PARTIALLY_PRESERVED | 4 |
| MAJOR_LOSS | 1 |

| Primary error type | Rows |
|---|---|
| NONE | 273 |
| SCOPE_CHANGE | 12 |
| OMISSION | 7 |
| NUMERIC_ENTITY_REFERENCE_ERROR | 3 |
| MODALITY_CHANGE | 2 |
| CONDITION_EXCEPTION_LOSS | 2 |
| HALLUCINATION_ADDITION | 1 |

## 3. English vs Hindi
Mean score: EN **9.03**, HI **8.90**.

| Score | EN | HI |
|---|---|---|
| 4 | 1 | 0 |
| 6 | 1 | 3 |
| 7 | 2 | 1 |
| 8 | 10 | 9 |
| 9 | 109 | 132 |
| 10 | 27 | 5 |

Hindi is not scored systematically lower; the gap comes mainly from more 9s and fewer 10s (Hindi rewording is rarely verbatim). Hindi explanations are written in Hindi.

## 4. Confidence
| Confidence | Rows |
|---|---|
| HIGH | 230 |
| MEDIUM | 70 |

No row was rated LOW. MEDIUM was used for incomplete fragments/headings, source typos, and rows with a minor judgment call.

## 5. NEEDS_REVIEW and flagged rows
- `NEEDS_REVIEW` passages: **50** (scores: {7: 1, 8: 4, 9: 45}). Source gaps were never reconstructed; they are noted in the explanation and reflected in confidence rather than in the score.
- Uncertain annotations (confidence MEDIUM): **70**.
- Priority human review list: **20** rows (`priority_human_review.csv`).

## 6. Caveats on score pattern (please read)
- **273 of 300 rows (91%) scored 9–10.** This is the "suspicious pattern" the task warns about, so it deserves scrutiny. My read is that most simplifications in this dataset are close, faithful paraphrases, but I cannot rule out leniency on subtle items. I used 9 as the default for "preserved with minor non-material wording differences" and reserved 10 for near-verbatim or trivially restated text.
- To reduce misses I ran an automated audit (digit/number mismatches, shall/may/must counts, provisos/exceptions, Hindi modality markers, length ratios) after annotating. It surfaced one further issue (HI_122), which I corrected. It cannot catch subtle semantic drift, so human spot-checking of the 9s is recommended, especially Hindi legal terminology (e.g. विचारण→सुनवाई, असंगत→विपरीत).
- Recurring pattern worth adjudicating: in several Hindi rows the simplification replaces trial-related 'विचारण' with 'सुनवाई'. I treated this as acceptable in context; a stricter reviewer may not.
- Several NEEDS_REVIEW Hindi rows contain source typos that the simplification corrected silently or with a parenthetical note (HI_022, 023, 033, 123, 129, 130, 138). Whether such corrections count as errors is a policy decision for the project.
- Error labels: `NONE` is 273 rows, so the other labels have small counts; distribution comparisons across labels are not meaningful.

## 7. Methodology note
Each pair was compared clause by clause for modality, conditions/exceptions, scope, parties, numbers and references, and penalties/consequences, following the project guidelines (scores 9–10 only with no material loss; error label required below 9). Where original and simplified texts relied on a missing governing clause, I evaluated only the supplied text. **These are AI-assisted annotation drafts that require human verification**; they were produced by a single AI pass without legal-expert adjudication, may contain errors in Hindi legal terminology and statutory context, and should not be cited as objective or human-validated labels. Where the Hindi source may differ from the official English text (e.g. HI_116 'प्रवृत्त किया जाएगा' vs 'enforceable'), I scored against the supplied Hindi and flagged the issue.
