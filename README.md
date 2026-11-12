# Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT

## Project Overview
This project focuses on evaluating and preserving the semantic and legal meaning of multilingual legal texts. By leveraging domain-specific language modeling (JUDGEBERT) alongside explainability techniques, the system assesses cross-lingual legal fidelity and highlights critical discrepancies to support transparent and reliable legal NLP tasks.

## Project Structure
- `data/`: Raw, processed, and annotated legal datasets.
- `training/`: Pipelines for data preprocessing, baseline model training, JUDGEBERT fine-tuning, and model evaluation.
- `models/`: Storage for baseline and JUDGEBERT trained model checkpoints and configurations.
- `backend/`: API services, inference logic, explainability modules, and runtime evaluations.
- `frontend/`: User interface for interactive testing, comparison, and explanation visualization.
- `reports/`: Experimental reports, evaluation metrics, logs, and research documentation.

---

## Legal Meaning Preservation (LMP) Annotation Guidelines

### Overview
The annotation dataset is located at:
`data/annotations/lmp_annotation_template.csv`

This template contains **300 unique statutory passages** (150 English, 150 Hindi) sampled evenly across 5 Indian Central Acts. The goal of the annotation process is to evaluate how accurately a plain-language legal simplification preserves the exact statutory meaning, normative obligations, rights, and liabilities of the original passage.

### Annotation Schema & Columns

| Column | Description | Instructions / Allowed Values |
| :--- | :--- | :--- |
| `pair_id` | Unique identifier | `LMP_EN_001` to `LMP_EN_150` for English; `LMP_HI_001` to `LMP_HI_150` for Hindi. *(Pre-filled)* |
| `language` | Language code | `EN` (English) or `HI` (Hindi). *(Pre-filled)* |
| `act_id` | Act identifier | Code for the enactment (e.g., `2006_4`, `2007_56`, `1969_18`, `1976_19`, `2008_34`). *(Pre-filled)* |
| `original_text` | Source passage | Unaltered statutory text from the official legislation. *(Pre-filled)* |
| `simplified_text` | Plain-language version | Enter the plain-language simplified version of the legal passage. Ensure it remains legally sound. |
| `lmp_score` | Meaning Preservation Score | Numeric scale from **1.0 to 10.0** evaluating fidelity of legal meaning (see Scoring Scale below). |
| `error_type` | Discrepancy taxonomy | Categorize the primary legal error if `lmp_score` < 9.0 (see Error Taxonomy below). If score is 9.0+, set to `NONE`. |
| `annotation_notes` | Qualitative justification | Brief explanation highlighting why points were deducted or which legal nuance was lost/preserved. |
| `annotator_id` | Annotator tag | Unique identifier of the legal annotator (e.g., `ANN_01`, `ANN_02`). |

### LMP Scoring Scale (1 to 10)
- **9.0 – 10.0 (Perfect Preservation):** Complete semantic and normative legal equivalence. All rights, duties, deontic modals, exceptions, conditions, and penalties remain strictly intact.
- **7.0 – 8.9 (Minor Semantic Drift):** Minor syntactic rephrasing or stylistic simplification with zero alteration to legal standing, rights, or obligations.
- **5.0 – 6.9 (Moderate Loss):** Ambiguous rephrasing of statutory conditions or obligations that creates interpretative uncertainty.
- **3.0 – 4.9 (Significant Distortion):** Omission of a statutory proviso, alteration of a mandatory command ("shall" $\rightarrow$ "may"), or distortion of procedural scope.
- **1.0 – 2.9 (Critical Failure):** Direct contradiction of the statute, inverted legal liability, omitted criminal sanctions, or introduction of non-existent legal rights.

### Error Taxonomy (`error_type`)
- `NONE`: No legal distortion (used when `lmp_score` >= 9.0).
- `MODAL_DRIFT`: Inappropriate change of deontic modality (e.g., changing mandatory "shall" to permissive "may" or "should").
- `CONDITION_OMISSION`: Dropping provisos, statutory preconditions, or jurisdictional exceptions (e.g., omitting "except the State of Jammu and Kashmir").
- `ENTITY_DISTORTION`: Inaccurate legal terms, officer designations, or institutional names (e.g., mistranslating "Court of Session").
- `SCOPE_ALTERATION`: Unduly broadening or restricting the application of the legal provision.
- `PENALTY_INACCURACY`: Misrepresenting imprisonment duration, monetary fines, or compounding provisions.

### Execution Instructions

#### 1. Generate / Regenerate Annotation Template
To regenerate the balanced 300-passage annotation template from raw statutory data:
```powershell
python training/prepare_pairs.py
```
Outputs:
- Annotation template: `data/annotations/lmp_annotation_template.csv`
- Summary report: `reports/lmp_annotation_summary.md`

#### 2. Run Preprocessing, Validation & Splitting Pipeline
To normalize text, validate dataset integrity, and generate reproducible train/val/test partitions:
```powershell
# Standard execution (70% Train, 15% Val, 15% Test, Seed 42)
python training/preprocessing.py

# Custom ratios or seed
python training/preprocessing.py --train_ratio 0.70 --val_ratio 0.15 --test_ratio 0.15 --seed 42

# Validation & normalization only (without splitting)
python training/preprocessing.py --skip_split
```
Outputs in `data/processed/`:
- `train.csv`: 210 records (70% stratified partition, 21 per stratum)
- `val.csv`: 45 records (15% stratified partition)
- `test.csv`: 45 records (15% stratified partition)
- `preprocessed_full.csv`: 300 normalized records
- `split_metadata.json`: Comprehensive partition statistics, strata counts, and leakage check results.

#### 3. Run Preprocessing Unit Tests
To run the automated test suite verifying Unicode NFKC normalization, whitespace processing, legal term preservation, validation constraints, and leakage-free splitting:
```powershell
python tests/test_preprocessing.py -v
# or via unittest discovery:
python -m unittest discover tests
```



