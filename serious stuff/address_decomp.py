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
from batch_mistral_api import send_batch_prompts

def open_file(file_path,first_col,last_col,n_rows):
    """
    Opens an Excel file and returns the DataFrame.
    """
    df = pd.read_excel(file_path, engine='openpyxl')
    return df.iloc[:n_rows, first_col:last_col]


def build_prompt(address: str, pays: str, context: str, template: Template) -> str:
    """
    Builds a prompt using the provided address, pays, and template.

    Args:
        address (str): The address to include in the prompt.
        pays (str): The pays to include in the prompt.
        template (Template): The Jinja2 template to use for building the prompt.

    Returns:
        str: The constructed prompt.
    """
    # Set pays to "FRANCE" if it is empty or NaN
    if not isinstance(pays, str) or pays.strip() == "":
        pays = "FRANCE"
    # Pass the address and pays to the jinja2 prompt template
    return template.render(address=address, pays=pays, context=context)

def extract_keywords(address_concat: str,keywords:dict) -> dict:
    """
    Extracts keywords from the concatenated address string.

    Args:
        address_concat (str): The concatenated address string.
        keywords (dict): A dictionary of keywords to extract.

    Returns:
        dict: A dictionary containing the extracted keywords.
    """
    address=address_concat.lower().split(" ")
    keywords_found = {}
    for index, keyword_list in keywords.items():
        for keyword in keyword_list:
            if keyword.lower() in address:
                keywords_found[index] = keyword
    
    context_parts = []
    for key, value in keywords_found.items():
        if value:
            context_parts.append(f"{str(value).capitalize()} = {key}")
    if len(context_parts) > 0:
        return ", ".join(context_parts)
    return ""

def build_all_prompts(PROMPT_FILE: str, addresses: list, pays_liste: list, keywords: list) -> tuple:

    # Read the prompt template from the file
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_template = Template(f.read().strip())
        prompts = []
        for address, pays in zip(addresses, pays_liste):
            context = extract_keywords(address, keywords)
            prompts.append(build_prompt(address, pays, context=context, template=prompt_template))

        return prompts
    
def is_answer_true(answer_str,true_comparaison:list):
    answer_str=str(answer_str).split(";")
    true_comparaison=str(true_comparaison).split(";")
    answer_str=[set(str(ans).lower().split(" ")) for ans in answer_str]
    true_comparaison=[set(str(ans).lower().split(" ")) for ans in true_comparaison]
    for ans, true_ans in zip(answer_str,true_comparaison):
        if ans != true_ans:
            return False
    return True

def accuracy_calc(df,answers):
    correct_comparaisons = (
        df[['Numero de voie et voie', 'immeuble residence', 'Appartement / etage', 'mention speciale / lieu dit']]
        .fillna("")
        .astype(str)
        .agg(';'.join, axis=1)
        .tolist()
    )
    true=0
    false=0
    for i in range(len(answers)):
        if is_answer_true(answers[i], correct_comparaisons[i]):
            true += 1
        else:
            false += 1
    return 100*true/(true+false)

def main():
    
    with open('keys.json', 'r', encoding='utf-8') as f:
        api_keys = json.load(f)
    with open('common_words.json', 'r', encoding='utf-8') as f:
        keywords = json.load(f)

    CORRECT_FILE = "Adresses_test_correct.xlsx"
    N_LINES = 100
    MODEL = "ministral-8b-latest"

    PROMPT_FILE = "prompt_7.j2"
    API_KEYS = api_keys["mistral_api_key"]
    LOG_FILE = "asynchronus_requests_log.txt"

    df = pd.read_excel(CORRECT_FILE, engine='calamine')
    df = df.loc[:N_LINES-1, :]

    start_time = time.time()
    prompts = build_all_prompts(PROMPT_FILE, addresses=df['Adresse concat'], pays_liste=df['ADRESSPAY'], keywords=keywords)

    answers = send_batch_prompts(prompts, API_KEYS, MODEL)
    end_time = time.time()
    elapsed_time = end_time - start_time

    accuracy = accuracy_calc(df, answers)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"Rows processed: {len(prompts)}, Model: {MODEL}")
        f.write(f", Time: {elapsed_time:.2f} seconds, Prompt: {PROMPT_FILE}\n")
        if accuracy is not None:
            f.write(f"accuracy: {accuracy:.2f}%, ")
        f.write("\n\n")

if __name__ == "__main__":
    main()