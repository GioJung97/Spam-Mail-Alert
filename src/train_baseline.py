from __future__ import annotations
import json
from typing import List
from storage import fetch_labeled_data
from classify.baseline import build_pipeline, train, save_model

def main():
    rows = fetch_labeled_data()
    texts: List[str] = []
    labels: List[int] = []
    for r in rows:
        # only train on explicit labels
        if r["label"] in ("spam","ham"):
            # we didn’t store the raw text; approximate with reasons and score for now
            # For better training, you can store subject/snippet too (extend storage.py & main)
            texts.append(r["reasons"])
            labels.append(1 if r["label"] == "spam" else 0)

    if len(labels) < 20:
        print(f"Not enough labeled items yet ({len(labels)}). Aim for at least 50.")
        return

    pipe = build_pipeline()
    train(pipe, texts, labels)
    print(f"Trained on {len(labels)} items and saved model.")

if __name__ == "__main__":
    main()
