import pandas as pd
import re
from pathlib import Path

LOG_FILE = "asynchronus_requests_log.txt"
EXCEL_FILE = "Comparaison de tests.xlsx"

COLUMNS = [
    "model", "num of rows", "time", "prompt",
    "accuracy", "true neg acc", "conf acc", "conf coverage"
]

def parse_log_entry(entry: str):
    print("\n--- Parsing entry ---")
    print(entry)
    # Patterns for all possible fields
    summary_re = re.compile(
        r"Rows processed: (\d+), Model: ([^,]+), Time: ([\d.]+) seconds(?:, Prompt: ([^\n]+))?"
    )
    prompt_file_re = re.compile(r"Prompt file used: ([^\n]+)")
    accuracy_re = re.compile(r"accuracy: ([\d.]+)%")
    percent_exact_re = re.compile(r"Percentage of exact matches: ([\d.]+)%")
    true_neg_re = re.compile(r"True neg rate: ([\d.]+)%")
    conf_acc_re = re.compile(r"Conf accuracy: ([\d.]+)%")
    conf_cov_re = re.compile(r"Conf coverage: ([\d.]+)%")

    result = dict.fromkeys(COLUMNS, None)
    summary_match = summary_re.search(entry)
    if summary_match:
        num_rows, model, time, prompt = summary_match.groups()
        result["model"] = model.strip()
        result["num of rows"] = int(num_rows)
        result["time"] = float(time)
        if prompt:
            result["prompt"] = prompt.strip()
        print(f"Summary found: model={result['model']}, num_rows={result['num of rows']}, time={result['time']}, prompt={result['prompt']}")
    else:
        print("No summary found.")

    # Try to find prompt file if not in summary
    if not result["prompt"]:
        prompt_file_match = prompt_file_re.search(entry)
        if prompt_file_match:
            result["prompt"] = prompt_file_match.group(1).strip()
            print(f"Prompt file found: {result['prompt']}")

    # Scan all lines for metrics
    lines = entry.splitlines()
    for line in lines:
        if result["accuracy"] is None:
            m = accuracy_re.search(line)
            if m:
                result["accuracy"] = float(m.group(1))
                print(f"Accuracy found: {result['accuracy']}")
        if result["accuracy"] is None:
            m = percent_exact_re.search(line)
            if m:
                result["accuracy"] = float(m.group(1))
                print(f"Percentage of exact matches found: {result['accuracy']}")
        if result["true neg acc"] is None:
            m = true_neg_re.search(line)
            if m:
                result["true neg acc"] = float(m.group(1))
                print(f"True neg acc found: {result['true neg acc']}")
        if result["conf acc"] is None:
            m = conf_acc_re.search(line)
            if m:
                result["conf acc"] = float(m.group(1))
                print(f"Conf acc found: {result['conf acc']}")
        if result["conf coverage"] is None:
            m = conf_cov_re.search(line)
            if m:
                result["conf coverage"] = float(m.group(1))
                print(f"Conf coverage found: {result['conf coverage']}")

    # Only return if at least one field is filled
    if any(v is not None for v in result.values()):
        print(f"Result parsed: {result}")
        return result
    print("No valid fields found in entry.")
    return None

def extract_entries(log_text):
    # Split log into blocks for each test (summary line + metrics line)
    lines = log_text.splitlines()
    entries = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("Rows processed:"):
            block = lines[i]
            # Collect following lines until next "Rows processed:" or end
            j = i + 1
            while j < len(lines) and not lines[j].startswith("Rows processed:"):
                block += "\n" + lines[j]
                j += 1
            entries.append(block)
            i = j
        else:
            i += 1
    print(f"\nTotal entries extracted: {len(entries)}")
    return entries

def log_to_excel(all_entries=True, sheet_name="tests"):
    log_path = Path(LOG_FILE)
    if not log_path.exists():
        print(f"Log file {LOG_FILE} not found.")
        return

    with open(log_path, "r", encoding="utf-8") as f:
        log_text = f.read()

    entries = extract_entries(log_text)
    if not entries:
        print("No valid entries found in log.")
        return

    # Choose which entries to add
    if all_entries:
        parsed = [parse_log_entry(e) for e in entries]
    else:
        parsed = [parse_log_entry(entries[-1])]

    # Filter out completely empty parses
    parsed = [p for p in parsed if p is not None]
    print(f"\nParsed entries to write: {len(parsed)}")
    for p in parsed:
        print(p)
    if not parsed:
        print("No valid parsed entries to write.")
        return

    excel_path = Path(EXCEL_FILE)
    # Read all sheets if file exists
    if excel_path.exists():
        with pd.ExcelFile(excel_path) as xls:
            sheets = {name: xls.parse(name, dtype=object) for name in xls.sheet_names}
    else:
        sheets = {}

    # Update or create the target sheet
    if sheet_name in sheets:
        df = sheets[sheet_name]
    else:
        df = pd.DataFrame(columns=COLUMNS)

    # Ensure columns match and order is correct, and dtype is object
    new_df = pd.DataFrame(parsed)
    new_df = new_df.reindex(columns=COLUMNS)
    for col in COLUMNS:
        new_df[col] = new_df[col].astype(object)
        df[col] = df[col].astype(object)

    df = pd.concat([df, new_df], ignore_index=True)

    sheets[sheet_name] = df

    # Write all sheets back
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="w") as writer:
        for name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=name, index=False)
    print(f"\nSaved {len(parsed)} entries to sheet '{sheet_name}' in {EXCEL_FILE}.")

if __name__ == "__main__":
    # Set all_entries=False to add only the last test
    log_to_excel(all_entries=True, sheet_name="tests")