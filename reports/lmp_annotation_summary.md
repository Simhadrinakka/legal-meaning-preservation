# LMP Annotation Dataset Summary Report

**Generated File:** `data/annotations/lmp_annotation_template.csv`  
**Date:** November 2026  
**Project:** Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT  

## 1. Overall Dataset Metrics

- **Total Annotation Tasks:** 300
- **English Passages (`EN`):** 150
- **Hindi Passages (`HI`):** 150
- **Total Unique Legal Passages:** 300 (0 overlap between languages)
- **Initial Field State:** `simplified_text`, `lmp_score`, `error_type`, `annotation_notes`, and `annotator_id` are strictly EMPTY.

## 2. Distribution Across Central Acts

| Act ID | Official Act Title | English (`EN`) | Hindi (`HI`) | Total Passages |
| :--- | :--- | :---: | :---: | :---: |
| `1969_18` | The Registration of Births and Deaths Act, 1969 | 30 | 30 | 60 |
| `1976_19` | The Bonded Labour System (Abolition) Act, 1976 | 30 | 30 | 60 |
| `2006_4` | The Commissions for Protection of Child Rights Act, 2005 | 30 | 30 | 60 |
| `2007_56` | The Maintenance and Welfare of Parents and Senior Citizens Act, 2007 | 30 | 30 | 60 |
| `2008_34` | The National Investigation Agency Act, 2008 | 30 | 30 | 60 |
| **Total** | — | **150** | **150** | **300** |

## 3. Passage Length Profile

| Language | Min Words | Max Words | Mean Words | Median Words |
| :--- | :---: | :---: | :---: | :---: |
| **English (`EN`)** | 10 | 127 | 38.0 | 32 |
| **Hindi (`HI`)** | 10 | 159 | 38.7 | 32 |

## 4. Annotation Instructions Overview
- **`original_text`**: Unaltered statutory text extracted from official Indian enactments.
- **`simplified_text`**: Plain-language legal simplification produced by human or model.
- **`lmp_score`**: 1 to 5 Likert scale measuring Legal Meaning Preservation.
- **`error_type`**: Classification of legal meaning discrepancy (`NONE`, `MODAL_DRIFT`, `CONDITION_OMISSION`, `ENTITY_DISTORTION`, `SCOPE_ALTERATION`, `PENALTY_INACCURACY`).
- **`annotation_notes`**: Textual justification for the assigned score.
- **`annotator_id`**: Identifier of the annotator.