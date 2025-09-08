from verif import verification_main
from address_decomp import decomp_address
from jsonschema import validate
import json

def main():
    with open('config.json', 'r', encoding='utf-8') as f, open('schema.json', 'r', encoding='utf-8') as v:
        config = json.load(f)
        schema = json.load(v)
        validate(instance=config, schema=schema)
        params = config["ai_parameters"]
        verification_parameters = config["verification_parameters"]
        functions = config["functions"]
    decomp_address(params, functions)
    if functions["calculate_conf_score"]:
        verification_main(verification_parameters)

if __name__ == "__main__":
    main()