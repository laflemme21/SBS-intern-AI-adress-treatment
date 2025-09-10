from grading import grading_main
from address_verif import address_verif_main
from address_decomp import decomp_address
from jsonschema import validate
import json

def backend_main():
    with open('ressources/config.json', 'r', encoding='utf-8') as f, open('ressources/schema.json', 'r', encoding='utf-8') as v:
        config = json.load(f)
        schema = json.load(v)
        validate(instance=config, schema=schema)
        params = config["address_decomp_parameters"]
        ans_grading_parameters = config["ans_grading_parameters"]
        address_verif_parameters = config["address_verif_parameters"]
        functions = config["functions"]
    if functions["use_mistral"] or functions["parse_and_save_batch_ans_file"] or functions["build_and_save_prompts"]:
        decomp_address(params, functions)
        
    if functions["calculate_conf_score"]:
        grading_main(ans_grading_parameters)

    if functions["check_postal_code"] or functions["check_ville"]:
        address_verif_main(address_verif_parameters, functions)

if __name__ == "__main__":
    backend_main()