import asyncio
import aiohttp
import ssl
import certifi
import time 
import pandas as pd
import os
from jinja2 import Template


# Settings
MODEL = "gpt-4o-mini-search-preview-2025-03-11"
OPENAI_SECRET_KEY = '################################ '


# Function to extract addresses from an Excel file
def extract_from_excel_and_build_prompt(file_path, prompt_file, n_rows=None):
    """
    Extracts addresses from a specified column in an Excel file and builds prompts using a template from a file.

    Args:
        file_path (str): Path to the Excel file.
        n_rows (int, optional): Number of rows to process. If None, processes all rows.
        prompt_file (str): Path to the prompt template file.

    Returns:
        list: List of prompts.
        pd.DataFrame: The DataFrame containing the extracted rows.
    """
    # Read the prompt template from the file
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = Template(f.read().strip())

    df = pd.read_excel(file_path, engine='openpyxl', header=0)
    if n_rows:
        df = df.head(n_rows)

    addresses = df['Adresse concat'].tolist()
    contexts = df.iloc[:, 9].tolist()  # Column J (index 9)

    prompts = []
    for address, context in zip(addresses, contexts):
        # Set context to "FRANCE" if it is empty or NaN
        if not isinstance(context, str) or context.strip() == "":
            context = "FRANCE"
        # Pass the address and context to the jinja2 prompt template
        prompt = prompt_template.render(address=address, context=context)
        prompts.append(prompt)

    return prompts, df

# Call ChatGPT with the given prompt, asynchronously.
async def call_chatgpt_async(session, prompt: str, max_retries=3):
    """
    Sends a single prompt to ChatGPT and preprocesses the response.
    Retries if rate limit is exceeded.

    Args:
        session (aiohttp.ClientSession): The HTTP session for making requests.
        prompt (str): The prompt to send to ChatGPT.

    Returns:
        tuple: The preprocessed response (fields from post_process_response).
    """
    payload = {
        'model': MODEL,
        'messages': [
            {"role": "user", "content": prompt}
        ]
    }
    retries = 0
    while retries <= max_retries:
        try:
            async with session.post(
                url='https://api.openai.com/v1/chat/completions',
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_SECRET_KEY}"},
                json=payload,
                ssl=ssl.create_default_context(cafile=certifi.where())
            ) as response:
                response_json = await response.json()
            if "error" in response_json:
                error = response_json["error"]
                print(f"OpenAI request failed with error {error}")
                # Check for rate limit and retry
                if isinstance(error, dict) and error.get("code") == "rate_limit_exceeded":
                    await asyncio.sleep(2)  # 2s
                    retries += 1
                    continue
                return "N/A", "N/A", "N/A", "N/A", "N/A"  # Default values in case of an error
            # Extract the content and preprocess it immediately
            raw_content = response_json['choices'][0]['message']['content']
            result = post_process_response(raw_content)
            # Ensure always 5 values
            if len(result) < 5:
                result = tuple(list(result) + ["N/A"] * (5 - len(result)))
            return result
        except Exception as e:
            print(f"Request failed: {e}")
            await asyncio.sleep(0.2)
            retries += 1
    return "N/A", "N/A", "N/A", "N/A", "N/A"  # Default values if all retries fail


# Call chatGPT for all the given prompts in parallel.
async def call_chatgpt_bulk(prompts):
    """
    Sends multiple prompts to ChatGPT in parallel and preprocesses each response.

    Args:
        prompts (list): List of prompts to send to ChatGPT.

    Returns:
        list: List of preprocessed responses.
    """
    async with aiohttp.ClientSession() as session, asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(call_chatgpt_async(session, prompt)) for prompt in prompts]
        responses = await asyncio.gather(*tasks)
    return responses

def post_process_response(content):
    fields = content.split(';')
    while len(fields) < 5:
        fields.append("N/A")
    return tuple(field.strip() for field in fields[:5])

def add_answers_to_excel(df, n_rows, responses, start_col=12):
    """
    Updates the DataFrame with the processed responses and saves it back to the Excel file.

    Args:
        df (pd.DataFrame): The DataFrame to update.
        n_rows (int): Number of rows to update.
        responses (list): List of processed responses.
        start_col (int): Starting column index to update in the DataFrame.
    """
    # Ensure the columns that will receive string data are of object dtype
    for i in range(5):
        col_idx = start_col + i
        if col_idx not in df.columns or df.dtypes[col_idx] != 'object':
            df[col_idx] = df[col_idx].astype('object')

    for idx, (row_index, _) in enumerate(df.head(n_rows).iterrows()):
        numero_voie, immeuble_residence, etage_appartement, mention_speciale, confidence_score = responses[idx]
        df.at[row_index, start_col] = numero_voie
        df.at[row_index, start_col + 1] = immeuble_residence
        df.at[row_index, start_col + 2] = etage_appartement
        df.at[row_index, start_col + 3] = mention_speciale
        df.at[row_index, start_col + 4] = confidence_score  # Add confidence score

    # Save the updated DataFrame to a temporary file, keeping headers
    temp_file_path = 'temp_test_adresses.xlsx'
    df.to_excel(temp_file_path, index=False, header=True, engine='openpyxl')

    # Replace the original file with the temporary file
    os.replace(temp_file_path, 'Adresses_test.xlsx')

def compare_with_correct(file_predicted, file_correct, n_rows, start_col=12, mark_col=17):
    """
    Compare the predicted answers in file_predicted with the correct answers in file_correct.
    Returns the percentage of exact matches for the 4 columns (M, N, O, P by default).
    Also writes 'V' or 'F' in mark_col for each row in file_predicted.
    """
    df_pred = pd.read_excel(file_predicted, engine='openpyxl', header=0)
    df_corr = pd.read_excel(file_correct, engine='openpyxl', header=0)
    correct = 0

    # Ensure the mark_col exists
    if mark_col >= len(df_pred.columns):
        for _ in range(mark_col - len(df_pred.columns) + 1):
            df_pred[df_pred.shape[1]] = ""
    # Ensure the mark_col is of object dtype for string assignment
    if df_pred.dtypes[mark_col] != 'object':
        df_pred[mark_col] = df_pred[mark_col].astype('object')

    for idx in range(n_rows):
        is_all_true = True
        for col in range(start_col, start_col + 4):  # Check columns M, N, O, P
            val_pred = str(df_pred.iloc[idx, col]).strip()
            val_corr = str(df_corr.iloc[idx, col]).strip()
            if val_pred != val_corr:
                is_all_true = False 
        if is_all_true:
            correct += 1  # 1 row correct
            df_pred.iloc[idx, mark_col] = 'V'
        else:
            df_pred.iloc[idx, mark_col] = 'F'

    percent = 100 * correct / n_rows if n_rows > 0 else 0

    # Save the updated predicted file with V/F marking
    df_pred.to_excel(file_predicted, index=False, header=True, engine='openpyxl')
    return percent

if __name__ == "__main__":
    # ----------- CONFIGURATION -----------
    N_ROWS = 20  # Number of rows to process
    INPUT_FILE = 'Adresses_test.xlsx'
    PROMPT_FILE = 'prompt_3.j2'
    OUTPUT_FILE = 'Adresses_test.xlsx'
    CORRECT_FILE = 'Adresses_test_correct.xlsx'
    LOG_FILE = "asynchronus_requests_log.txt"
    START_COL = 12  # First column to edit (12=M)
    UPDATE_LOG = True  # Set to False to disable logging

    # ----------- WORKFLOW SELECTION -----------
    RUN_EXTRACTION = True
    RUN_CHATGPT = True
    RUN_WRITE_OUTPUT = True
    RUN_COMPARE = True

    # ----------- PIPELINE -----------
    start_time = time.time()

    if RUN_EXTRACTION:
        prompts, df = extract_from_excel_and_build_prompt(INPUT_FILE, n_rows=N_ROWS, prompt_file=PROMPT_FILE)
    else:
        prompts, df = [], None

    if RUN_CHATGPT and prompts:
        processed_results = asyncio.run(call_chatgpt_bulk(prompts))
    else:
        processed_results = []

    if RUN_WRITE_OUTPUT and df is not None and processed_results:
        add_answers_to_excel(df, len(prompts), processed_results, start_col=START_COL)

    end_time = time.time()
    elapsed_time = end_time - start_time

    if RUN_COMPARE:
        percent_true = compare_with_correct(OUTPUT_FILE, CORRECT_FILE, len(prompts), start_col=START_COL)
    else:
        percent_true = None

    # ----------- LOGGING -----------
    if UPDATE_LOG:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"Rows processed: {len(prompts)}, Model: {MODEL}, Time: {elapsed_time:.2f} seconds\n")
            f.write(f"Prompt file used: {PROMPT_FILE}\n")
            if percent_true is not None:
                f.write(f"Percentage of exact matches: {percent_true:.2f}%\n")
            f.write("\n")

# WARNING: Never write to 'Adresses_test_correct.xlsx'. It is used as a read-only reference.