import pandas as pd
import asyncio
import aiohttp
import ssl
import certifi
import time 
import os
from jinja2 import Template
import json
import xlwings as xw
from address_decomp import build_all_prompts  

def process_answer(rue,apart,etage,post):
    def clean(val):
        # If val is NaN, return empty string
        if pd.isna(val):
            return ""
        return str(val).replace("\n", " ").replace("\r", " ").strip()
    str_rue = clean(rue)
    str_apart = clean(apart)
    str_etage = clean(etage)
    str_post = clean(post)

    return f"{str_rue};{str_apart};{str_etage};{str_post}"

def main():
    with open('common_words.json', 'r', encoding='utf-8') as f:
        keywords = json.load(f)

    file = "Adresses_test_correct.xlsx"
    prompt_file="prompt_7.j2"
    df = pd.read_excel(file, engine='openpyxl')
    df = df.loc[:200, :]
    answers=[]
    for index, row in df.iterrows():
        processed = process_answer(row['Numero de voie et voie'], row['immeuble residence'], row['Appartement / etage'], row['mention speciale / lieu dit'])
        answers.append(processed)

    prompts=build_all_prompts(prompt_file, addresses=df['Adresse concat'], pays_liste=df['ADRESSPAY'], keywords=keywords)

    

    # Create a list of message dictionaries
    data = []
    for prompt, answer in zip(prompts, answers):
        entry = {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": answer}
            ]
        }
        data.append(entry)

    # Write to a .jsonl file
    with open("fine_tune_dataset.jsonl", "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")




main()