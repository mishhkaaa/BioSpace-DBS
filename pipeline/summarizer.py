# pipeline/summarizer.py
"""
Microstep 3:
Batch summarization for all papers.
"""

import pandas as pd
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from tqdm import tqdm

MODEL_NAME = "sshleifer/distilbart-cnn-12-6"

print(f"[Summarizer] Loading model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)


def summarize_text(text: str, max_len=150):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=max_len,
        min_length=40,
        length_penalty=2.0,
        num_beams=4,
        early_stopping=True
    )
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)


def generate_summaries(df, text_column="abstract"):
    summaries = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Summarizing papers"):
        text = row[text_column]
        summary = summarize_text(text)
        summaries.append(summary)

    df_out = df.copy()
    df_out["summary"] = summaries
    df_out["summary_model"] = MODEL_NAME

    return df_out
