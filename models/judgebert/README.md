# JUDGEBERT Model Artifacts

This directory contains the architecture metadata and configuration for the fine-tuned **JUDGEBERT** multi-task legal language model.

## Model Checkpoint (`judgebert_weights.pt`)

The fine-tuned binary weights file `judgebert_weights.pt` (~1.11 GB) is excluded from version control to adhere to GitHub's file size limits (>100 MB).

### Architecture Specification
- **Transformer Backbone**: `FacebookAI/xlm-roberta-base` (278M parameters, vocabulary size 250,002)
- **Multi-Task Heads**:
  1. `reg_head`: Linear regression head predicting the continuous Legal Meaning Preservation (LMP) score ($0.0 - 10.0$).
  2. `dec_head`: 5-class classification head (`PRESERVED`, `MOSTLY_PRESERVED`, `PARTIALLY_PRESERVED`, `MAJOR_LOSS`, `FUNDAMENTALLY_ALTERED`).
  3. `err_head`: 8-class classification head (`NONE`, `OMISSION`, `HALLUCINATION_ADDITION`, `CONTRADICTION`, `MODALITY_CHANGE`, `CONDITION_EXCEPTION_LOSS`, `SCOPE_CHANGE`, `NUMERIC_ENTITY_REFERENCE_ERROR`).

### Training & Checkpoint Generation
To train and produce the checkpoint from scratch:
```bash
# Ensure preprocessed partitions are generated
python training/preprocessing.py

# Train JUDGEBERT multi-task model
python training/train_judgebert.py --epochs 8 --batch_size 4 --device cuda
```
Weights will be saved to `models/judgebert/judgebert_weights.pt` alongside `metadata.json`.

### Tokenizer Configuration
The application automatically pulls and instantiates the `FacebookAI/xlm-roberta-base` tokenizer from Hugging Face Hub using the local `tokenizer_config.json` if serialized files (`tokenizer.json`) are not present locally.
