import pandas as pd
import time 
from jinja2 import Template
import json
from batch_mistral_api import send_batch_prompts,write_temp_jsonl,_build_jsonl_lines,_extract_content_from_item
from jsonschema import validate
from grading import get_delim_csv

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

def accuracy_calc(df,columns,answers):
    correct_comparaisons = (
        df[columns]
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

def log_answers(answers, adresses, log_file, columns: list[str,str,str,str]):
    # answers: List[List[str]], each inner list has 4 elements
    answers = [ans.split(";") for ans in answers]
    # Transpose answers to get columns
    answers_T = list(zip(*answers))
    # Prepare DataFrame for output
    df_out = pd.DataFrame({
        columns[0]: adresses[:len(answers_T[0])],
        columns[1]: answers_T[0],
        columns[2]: answers_T[1],
        columns[3]: answers_T[2],
        columns[4]: answers_T[3]
    })


    # Write to CSV or Excel depending on file extension
    if log_file.endswith(".csv"):
        df_out.to_csv(log_file, sep=";", index=False, encoding="utf-8-sig")
    elif log_file.endswith(".xlsx"):
        df_out.to_excel(log_file, index=False)
    else:
        # Fallback to CSV
        df_out.to_csv(log_file, sep=";", index=False, encoding="utf-8-sig")

def from_batch_ans_file_to_answers(batch_ans_file):
    results_map = {}
    with open(batch_ans_file, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            cid = item.get("custom_id")
            content = _extract_content_from_item(item)
            tupled = str(content)
            results_map[int(cid)] = tupled
    ordered = [results_map.get(i, ("N/A", "N/A", "N/A", "N/A", "N/A")) for i in range(len(results_map))]
    return ordered

def decomp_address(params, functions):

    with open(params["mots_cles_file"], 'r', encoding='utf-8') as f:
        keywords = json.load(f)

    INPUT_FILE = params["input_file"]
    N_LINES = params["n_lines_process"]
    MODEL = params["mistral_model"]

    PROMPT_FILE = params["prompt_file"]
    API_KEYS = params["api_key"]
    LOG_FILE = params["statistics_log_file"]
    OUTPUT_FILE = params["output_file"]

    if INPUT_FILE.endswith(".xlsx"):
        df = pd.read_excel(INPUT_FILE, engine='calamine')
    elif INPUT_FILE.endswith(".csv"):
        df = pd.read_csv(INPUT_FILE, header=0, dtype=str, encoding='utf-8-sig', delimiter=get_delim_csv(INPUT_FILE))

    if functions["log_statistics"]:
        start_time = time.time()
    
    if functions["use_mistral"] or functions["build_and_save_prompts"]:
        if N_LINES >= 0:
            df = df.head(N_LINES)

        prompts = build_all_prompts(PROMPT_FILE, addresses=df[params["concat_column"]], pays_liste=df[params["pays_column"]], keywords=keywords)
    
    if functions["build_and_save_prompts"]:
        lines_iter = list(_build_jsonl_lines(prompts, "/v1/chat/completions", {}))
        write_temp_jsonl(lines_iter, params["save_prompts_file"])

    if functions["use_mistral"]:
        answers = send_batch_prompts(prompts, API_KEYS, MODEL, batch_size=params["mistral_batch_size"])

    if functions["parse_and_save_batch_ans_file"]:
        answers = from_batch_ans_file_to_answers(params["batch_ans_file"])

    if functions["log_statistics"]:
        end_time = time.time()
        elapsed_time = end_time - start_time
    try:
        if functions["log_statistics"] :
            accuracy= accuracy_calc(df, params["output_columns"][1:],answers)
    except Exception as e:
        print(f"Error calculating accuracy: {e}")
        accuracy=None

    if functions["save_answers"] or functions["parse_and_save_batch_ans_file"]:
        log_answers(answers, df[params["concat_column"]],OUTPUT_FILE,params["output_columns"])

    if functions["log_statistics"]:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"Rows processed: {len(prompts)}, Model: {MODEL}")
            f.write(f", Time: {elapsed_time:.2f} seconds, Prompt: {PROMPT_FILE}\n")
            if accuracy is not None:
                f.write(f"accuracy: {accuracy:.2f}%, ")
            f.write("\n\n")

if __name__ == "__main__":
    with open('ressources/config.json', 'r', encoding='utf-8') as f, open('ressources/schema.json', 'r', encoding='utf-8') as v:
        config = json.load(f)
        schema = json.load(v)
        validate(instance=config, schema=schema)
        params = config["address_decomp_parameters"]
        functions = config["functions"]

    decomp_address(params, functions)