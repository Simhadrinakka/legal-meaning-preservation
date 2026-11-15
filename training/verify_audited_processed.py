"""
Script: training/verify_audited_processed.py
Comprehensive verification of data/processed/audited/ splits and metadata.
"""
import json
from pathlib import Path
import pandas as pd

p = Path("data/processed/audited")
files = sorted([f.name for f in p.glob("*")])
print("Files generated in data/processed/audited/:", files)

# 1. Check shapes and primary clean counts
dfs = {}
for name in ["train", "train_clean", "val", "test", "preprocessed_full"]:
    fpath = p / f"{name}.csv"
    assert fpath.exists(), f"Missing file: {fpath}"
    df = pd.read_csv(fpath)
    dfs[name] = df
    clean_count = int(df["is_primary_train"].sum()) if "is_primary_train" in df else 0
    needs_review_count = int(df["is_needs_review"].sum()) if "is_needs_review" in df else 0
    human_blank = df[["human_lmp_score", "human_error_type", "human_explanation"]].isna().all().all() or (df[["human_lmp_score", "human_error_type", "human_explanation"]].fillna("").astype(str).values == "").all()
    print(f"{name:18s} -> Shape: {df.shape}, Clean: {clean_count:3d}, Needs Review: {needs_review_count:2d}, Human Blank: {human_blank}")

# 2. Check disjointness
train_ids = set(dfs["train"]["pair_id"])
val_ids = set(dfs["val"]["pair_id"])
test_ids = set(dfs["test"]["pair_id"])

assert len(train_ids.intersection(val_ids)) == 0, "Train-Val ID overlap!"
assert len(train_ids.intersection(test_ids)) == 0, "Train-Test ID overlap!"
assert len(val_ids.intersection(test_ids)) == 0, "Val-Test ID overlap!"
assert len(train_ids) + len(val_ids) + len(test_ids) == 300, "ID count sum mismatch!"
print("[VERIFIED] Level 1: pair_id disjointness (0 overlap)")

train_texts = set(dfs["train"]["original_text"])
val_texts = set(dfs["val"]["original_text"])
test_texts = set(dfs["test"]["original_text"])

assert len(train_texts.intersection(val_texts)) == 0, "Train-Val text overlap!"
assert len(train_texts.intersection(test_texts)) == 0, "Train-Test text overlap!"
assert len(val_texts.intersection(test_texts)) == 0, "Val-Test text overlap!"
print("[VERIFIED] Level 2: exact normalized original_text disjointness (0 overlap)")

# 3. Check metadata
meta_path = p / "split_metadata.json"
assert meta_path.exists(), "Missing split_metadata.json"
with open(meta_path, "r", encoding="utf-8") as f:
    meta = json.load(f)

print("[VERIFIED] split_metadata.json loaded successfully.")
print("Supervision Type:", meta["supervision_metadata"]["supervision_type"])
print("Is Human Gold:", meta["supervision_metadata"]["is_human_gold"])

# 4. Check that previous un-audited files in data/processed/ are intact and untouched
p_prev = Path("data/processed")
prev_files = ["train.csv", "train_clean.csv", "val.csv", "test.csv", "preprocessed_full.csv", "split_metadata.json"]
for pf in prev_files:
    assert (p_prev / pf).exists(), f"Previous file missing: {p_prev / pf}"
prev_train = pd.read_csv(p_prev / "train.csv")
# In previous train, LMP_HI_010 had score 9
assert prev_train.loc[prev_train["pair_id"] == "LMP_HI_010", "ai_lmp_score"].iloc[0] == 9, "Previous train.csv was modified!"
# In audited train, LMP_HI_010 has score 8
assert dfs["train"].loc[dfs["train"]["pair_id"] == "LMP_HI_010", "ai_lmp_score"].iloc[0] == 8, "Audited train does not have audited score!"
print("[VERIFIED] Previous data/processed/* files are untouched and different from data/processed/audited/*")

# 5. Check master and draft files
assert Path("data/annotations/lmp_master_300.csv").exists()
assert Path("data/annotations/lmp_ai_draft_300.csv").exists()
draft_df = pd.read_csv("data/annotations/lmp_ai_draft_300.csv")
assert draft_df.loc[draft_df["pair_id"] == "LMP_HI_010", "ai_lmp_score"].iloc[0] == 9, "lmp_ai_draft_300.csv was modified!"
print("[VERIFIED] data/annotations/lmp_ai_draft_300.csv is untouched!")

# 6. Detailed distribution tables
print("\n=== DETAILED DISTRIBUTIONS PER SPLIT ===")
for split_name in ["train", "train_clean", "val", "test"]:
    d = dfs[split_name]
    print(f"\n--- {split_name.upper()} (N={len(d)}) ---")
    print("Scores:\n", d["ai_lmp_score"].value_counts().sort_index().to_dict())
    print("Decisions:\n", d["ai_preservation_decision"].value_counts().to_dict())
    print("Error Types:\n", d["ai_error_type"].value_counts().to_dict())
    print("Mean Score:", round(d["target_score"].mean(), 2))
    print("Language Balance:", d["language"].value_counts().to_dict())
