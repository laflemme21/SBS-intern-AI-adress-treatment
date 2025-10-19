{
    "address_decomp_parameters": {
        "api_key": "################################",
        "mistral_model": "ft:ministral-8b-latest:5d5f2efb:20250902:79156560",
        "mistral_batch_size": 1000,
        "mots_cles_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/ressources/common_words.json",
        "input_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/in_out_files/Adresses_test_correct.xlsx",
        "pays_column": "ADRESSPAY",
        "output_columns": [
            "Adresse concat",
            "Numero de voie et voie",
            "immeuble residence",
            "Appartement / etage",
            "mention speciale / lieu dit"
        ],
        "concat_column": "Adresse concat",
        "output_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/in_out_files/ministral-400-answers.csv",
        "prompt_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/ressources/prompt_7.j2",
        "n_lines_process": 35,
        "statistics_log_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/in_out_files/batch_log.txt",
        "save_prompts_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/documentation/saved_prompts.jsonl",
        "batch_ans_file": "C:/Users/kkassis/Downloads/2306b982-8a8b-451c-bb4e-8055f7063659.jsonl"
    },
    "ans_grading_parameters": {
        "input_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/in_out_files/ministral-400-answers.csv",
        "mots_cles_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/ressources/common_words.json",
        "input_columns": [
            "Adresse concat",
            "Numero de voie et voie",
            "immeuble residence",
            "Appartement / etage",
            "mention speciale / lieu dit"
        ],
        "number_of_rows": -1,
        "output_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/in_out_files/output.xlsx",
        "grading_weights": {
            "lengths": [
                0.2,
                0.1,
                0.1,
                0.2
            ],
            "keywords": 0.5,
            "wrong_keywords": 1.0,
            "rue_starts_number": 0.6,
            "exact_word_match": 2.0
        },
        "min_length": 3,
        "max_length": 50
    },
    "address_verif_parameters": {
        "input_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/in_out_files/Adresses_test_correct.xlsx",
        "postal_code_files": [
            "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/ressources/france_cop.txt"
        ],
        "ville_files": [
            "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/ressources/france_villes.txt"
        ],
        "corresponding_pays": [
            "FRANCE"
        ],
        "pays_column": "ADRESSPAY",
        "ville_column": "ADRESSVIL",
        "code_postal_column": "ADRESSCOP",
        "output_file": "C:/Users/kkassis/Documents/GitHub/SBS-intern-AI-adress-treatment/address decomp project/in_out_files/Adresses_test_correct.xlsx"
    },
    "functions": {
        "use_mistral": false,
        "log_statistics": false,
        "parse_and_save_batch_ans_file": true,
        "save_answers": false,
        "build_and_save_prompts": false,
        "calculate_conf_score": true,
        "check_postal_code": false,
        "check_ville": false
    }
}
