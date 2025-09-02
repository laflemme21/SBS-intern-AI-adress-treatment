from batch_mistral_api import _extract_content_from_item
from address_decomp import accuracy_calc
import json
import pandas as pd









def main():
    input_file = "mistral-8b_out.jsonl"
    MODEL = "ft:ministral-8b-latest:5d5f2efb:20250902:79156560"
    
    LOG_FILE = "asynchronus_requests_log.txt"
    CORRECT_FILE = "Adresses_test_correct.xlsx"
    df = pd.read_excel(CORRECT_FILE, engine='calamine')
    with open(input_file, "r", encoding="utf-8") as f:
        results_map = {}  # custom_id -> processed tuple
        for line in f:
            item = json.loads(line)
            cid = item.get("custom_id")
            content = _extract_content_from_item(item)
            tupled = str(content)
            results_map[int(cid)] = tupled
        ordered = [results_map.get(i, ("N/A", "N/A", "N/A", "N/A", "N/A")) for i in range(len(results_map))]


        accuracy=accuracy_calc(df,ordered)

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"Rows processed: {len(ordered)}, file_name {input_file}, Model: {MODEL}\n")
            if accuracy is not None:
                f.write(f"accuracy: {accuracy:.2f}%")
            f.write("\n\n")

if __name__ == "__main__":
    main()