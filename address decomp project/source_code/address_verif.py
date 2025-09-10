import pandas as pd
import json
from jsonschema import validate
from grading import get_delim_csv

def load_word_list(file_paths):
    """Load words from a file into a set for fast membership testing."""
    word_set = []
    for i in range(len(file_paths)):
        word_set.append(set())
        with open(file_paths[i], 'r', encoding='utf-8') as file:
            for line in file:
                word = line.strip()
                if word:
                    word_set[i].add(word.lower())
    return word_set

def check_membership(word_set, word):
    """Check which search words are present in the word set."""
    return word.lower() in word_set

def address_verif_main(verification_parameters: dict, function: dict):

    ADDRESS_FILE = verification_parameters["input_file"]
    CORRECT_VILLE_FILE = verification_parameters["ville_files"]
    CORRECT_CODE_POSTALE_FILE = verification_parameters["postal_code_files"]
    PAYS= verification_parameters["corresponding_pays"]
    COLUMN_PAYS = verification_parameters["pays_column"]
    COLUMN_VILLE = verification_parameters["ville_column"]
    COLUMN_CODE_POSTALE = verification_parameters["code_postal_column"]
    OUTPUT_FILE = verification_parameters["output_file"]
    EXE_VILLE = function["check_ville"]
    EXE_CODE_POSTALE = function["check_postal_code"]

    if ADDRESS_FILE.endswith(".xlsx"):
        df = pd.read_excel(ADDRESS_FILE, engine='calamine')
    elif ADDRESS_FILE.endswith(".csv"):
        df = pd.read_csv(ADDRESS_FILE, header=0, dtype=str, encoding='utf-8-sig', delimiter=get_delim_csv(ADDRESS_FILE))

    ville_set = load_word_list(CORRECT_VILLE_FILE)
    code_postale_set = load_word_list(CORRECT_CODE_POSTALE_FILE)

    if EXE_VILLE or EXE_CODE_POSTALE:
        for index, row in df.iterrows():
            for i in range(len(PAYS)):
                pays = str(row[COLUMN_PAYS]).strip()
                if pays.lower() == PAYS[i].lower():
                    ville = str(row[COLUMN_VILLE]).strip()
                    code_postale = str(row[COLUMN_CODE_POSTALE]).strip()
                    if EXE_VILLE:
                        df.at[index, 'VILLE_CORRECT'] = check_membership(ville_set[i], ville)
                    if EXE_CODE_POSTALE:
                        df.at[index, 'CODE_POSTALE_CORRECT'] = check_membership(code_postale_set[i], code_postale)
                    break

    if OUTPUT_FILE.endswith(".csv"):
        df.to_csv(OUTPUT_FILE, sep=";", index=False, encoding="utf-8-sig")
    elif OUTPUT_FILE.endswith(".xlsx"):
        df.to_excel(OUTPUT_FILE, index=False)
    else:
        raise ValueError("Unsupported output file format. Use .csv or .xlsx")



if __name__=="__main__":
    with open('ressources/config.json', 'r', encoding='utf-8') as f, open('ressources/schema.json', 'r', encoding='utf-8') as v:
        config = json.load(f)
        schema = json.load(v)
        validate(instance=config, schema=schema)
        verification_parameters = config["address_verif_parameters"]
        functions = config["functions"]
    address_verif_main(verification_parameters, functions)