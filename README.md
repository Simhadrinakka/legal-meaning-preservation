# Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT

An AI-powered system that evaluates whether simplified legal texts preserve the original meaning of English and Hindi legal provisions using multilingual language models and rule-based legal analysis.

## Problem Statement

Simplifying legal documents makes them easier to understand, but important legal meanings can be unintentionally altered. Changes in obligations, permissions, prohibitions, conditions, exceptions, or scope can significantly affect how a legal provision is interpreted.

Our project aims to identify such meaning changes and provide interpretable feedback when comparing original legal provisions with simplified versions.

## Our Solution

We developed a JUDGEBERT-inspired hybrid system combining multilingual transformer-based analysis with rule-based statutory invariant checking.

The system compares an original legal provision with its simplified version and generates a Legal Meaning Preservation (LMP) score, preservation classification, detected legal errors, and explainability insights.

The project supports legal text analysis in both English and Hindi.

## Key Features

- **Multilingual Legal Analysis:** Supports English and Hindi legal provisions.
- **LMP Score:** Evaluates legal meaning preservation on a scale of 1–10.
- **Preservation Classification:** Classifies simplified provisions into five preservation categories.
- **Legal Error Detection:** Identifies potential omissions, contradictions, hallucinated additions, modality changes, condition or exception losses, scope changes, and numeric/reference errors.
- **Explainability:** Highlights potential legal meaning changes using rule-based statutory invariant checks.
- **Hybrid Analysis:** Combines multilingual model predictions with rule-based calibration.
- **Interactive Web Interface:** Provides a user-friendly interface for comparing legal texts and understanding analysis results.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript |
| Backend | Python, Flask |
| Deep Learning | PyTorch |
| NLP | Hugging Face Transformers, XLM-R |
| Explainability | Rule-based statutory invariant checking |
| Model | JUDGEBERT-inspired multilingual architecture |

## System Architecture

```text
Original Legal Text + Simplified Legal Text
                  |
                  v
       React Frontend Interface
                  |
                  v
           Flask Backend
                  |
         +--------+--------+
         |                 |
         v                 v
 Multilingual Model   Rule-Based Analysis
      (XLM-R)        (Legal Invariants)
         |                 |
         +--------+--------+
                  |
                  v
       Hybrid Calibration
                  |
                  v
     Legal Meaning Preservation
              Results
                  |
                  v
     Score + Classification
       + Error Detection
       + Explainability
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js and npm
- Git

### Clone the Repository

```bash
git clone https://github.com/Simhadrinakka/legal-meaning-preservation.git
cd Legal-Meaning-Preservation
```

### Backend Setup

```bash
python -m venv .venv
```

Activate the virtual environment on Windows:

```cmd
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
python backend/main.py
```

### Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local frontend URL displayed by Vite.

## Dataset

The project uses a 300-pair multilingual legal simplification dataset covering English and Hindi legal provisions from five Central Acts.


## Limitations

- The system is an experimental research prototype, not a production legal assessment tool.
- The dataset is limited in size and diversity.
- Rule-based checks cover selected legal invariants and may miss subtle or unrecognized meaning changes.
- Model predictions are not guaranteed to establish legal equivalence.
- The system is not a substitute for professional legal review or legal advice.

## Future Improvements

- Expand the dataset with expert-annotated legal examples.
- Improve multilingual legal understanding and error detection.
- Extend statutory invariant coverage.
- Improve model calibration and evaluation.
- Explore additional Indian languages.

## Disclaimer

This project is intended for academic and research purposes only. Its outputs should not be treated as legal advice or authoritative interpretations of legislation.
