import pandas as pd
import time 
from jinja2 import Template
import json
from batch_mistral_api import send_batch_prompts
from jsonschema import validate, ValidationError

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
    answer_bool=[]
    for i in range(len(answers)):
        if is_answer_true(answers[i], correct_comparaisons[i]):
            true += 1
            answer_bool.append("V")
        else:
            false += 1
            answer_bool.append("F")
    return 100*true/(true+false),answer_bool

def log_answers(answers,adresses, ans_corr,log_file):
    with open(log_file, "w", encoding="utf-8-sig") as f:
        for answer, adresse, corr in zip(answers, adresses, ans_corr):
            f.write(f"{adresse}; {answer}; {corr}\n")

def main():

    with open('config.json', 'r', encoding='utf-8') as f, open('schema.json', 'r', encoding='utf-8') as v:
        config = json.load(f)
        schema = json.load(v)
        validate(instance=config, schema=schema)
        params = config.get("parameters", {})
        functions = config.get("functions", {})

    with open(params.get("mots_cles_file", ""), 'r', encoding='utf-8') as f:
        keywords = json.load(f)

    INPUT_FILE = params.get("input_file", "")
    N_LINES = params.get("n_lines", 0)
    MODEL = params.get("model", "")

    PROMPT_FILE = params.get("prompt_file", "")
    API_KEYS = params.get("api_keys", [])
    LOG_FILE = params.get("log_file", "")
    OUTPUT_FILE = params.get("output_file", "")

    if INPUT_FILE.endswith(".xlsx"):
        df = pd.read_excel(INPUT_FILE, engine='calamine')
    elif INPUT_FILE.endswith(".csv"):
        df = pd.read_csv(INPUT_FILE, header=0, dtype=str, encoding='utf-8-sig',delimiter=';')

    if N_LINES >= 0:
        df = df.head(N_LINES)

    if functions.get("log_statistics", False):
        start_time = time.time()

    if functions.get("build_prompts", False):
        prompts = build_all_prompts(PROMPT_FILE, addresses=df['Adresse concat'], pays_liste=df['ADRESSPAY'], keywords=keywords)
    
    if functions.get("use_model", False):
        answers = send_batch_prompts(prompts, API_KEYS, MODEL)

    if functions.get("log_statistics", False):
        end_time = time.time()
        elapsed_time = end_time - start_time

    if functions.get("save_answers", False) or functions.get("log_statistics", False):
        accuracy ,answers_corr= accuracy_calc(df, answers)

    if functions.get("save_answers", False):
        log_answers(answers, df['Adresse concat'], answers_corr,OUTPUT_FILE)

    if functions.get("log_statistics", False):
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"Rows processed: {len(prompts)}, Model: {MODEL}")
            f.write(f", Time: {elapsed_time:.2f} seconds, Prompt: {PROMPT_FILE}\n")
            if accuracy is not None:
                f.write(f"accuracy: {accuracy:.2f}%, ")
            f.write("\n\n")

if __name__ == "__main__":
    main()