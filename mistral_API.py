import requests
import aiohttp
import asyncio
import random 
import json, time, uuid, os
import requests
from contextlib import ExitStack


def post_process_response(content):
    fields = content.split(';')
    while len(fields) < 5:
        fields.append("N/A")
    return tuple(field.strip() for field in fields[:5])


async def call_mistral_async(session, prompt: str, api_key: str, model: str, max_retries=1000):
    """
    Sends a single prompt to the Mistral API and preprocesses the response.
    Retries if rate limit is exceeded.

    Args:
        session (aiohttp.ClientSession): The HTTP session for making requests.
        prompt (str): The prompt to send to Mistral.
        api_key (str): Your Mistral API key.
        model (str): The Mistral model to use.
        max_retries (int): Number of retries on failure.

    Returns:
        tuple: The preprocessed response (fields from post_process_response).
    """
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    retries = 0
    while retries <= max_retries:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                response_json = await response.json()
            if "object" in response_json and response_json["object"] == "error":
                error = response_json['message']
                print(f"Mistral request failed with error {error}, {retries} retries")
                # Check for rate limit and retry
                if error == "Rate limit exceeded":
                    await asyncio.sleep(random.expovariate(1/(0.5+5)))  # Random sleep to avoid hitting the rate limit again
            else:
                try:
                    # Defensive extraction of content
                    choices = response_json.get('choices')
                    if not choices or not isinstance(choices, list) or not choices[0].get('message'):
                        print(f"Unexpected response structure: {response_json}")
                    else:
                        content_field = choices[0]['message'].get('content')
                        raw_content = ""
                        if isinstance(content_field, str):
                            raw_content = content_field
                        elif isinstance(content_field, list):
                            for item in content_field:
                                if isinstance(item, dict) and "text" in item:
                                    raw_content = item["text"]
                                    break
                            if not raw_content:
                                raw_content = str(content_field)
                        else:
                            raw_content = str(content_field)
                        result = post_process_response(raw_content)
                except Exception as e:
                    print(f"Error extracting content: {e}, response: {response_json}")
                    return "N/A", "N/A", "N/A", "N/A", "N/A"
                if len(result) < 5:
                    result = tuple(list(result) + ["N/A"] * (5 - len(result)))
                return result
        except Exception as e:
            print(f"Mistral request failed: {e}, {retries} retries")
            await asyncio.sleep(0.2)
        finally:
            retries += 1
    print("Max retries exceeded, returning default values.")
    return "N/A", "N/A", "N/A", "N/A", "N/A"


def send_batch_prompts(
    prompts,
    api_key,
    model="mistral-small-latest",
    endpoint="/v1/chat/completions",
    timeout_hours=1,
    poll_interval=5  # <-- default identity
):
    """
    Submit a JSONL batch to Mistral, wait for completion, and return
    chat contents ordered to match the input prompts list.
    """
    if not endpoint.startswith("/v1/"):
        raise ValueError("endpoint must start with /v1/, e.g. /v1/chat/completions")

    # 1) Build JSONL lines in the required format
    # NOTE: no "model" in body; the batch job's 'model' applies to all items.
    lines = []
    for i, prompt in enumerate(prompts):
        lines.append({
            "custom_id": str(i),
            "body": {
                "messages": [{"role": "user", "content": prompt}],
                # add request-level params here if needed (max_tokens, temperature, etc.)
            },
        })

    # 2) Write temporary JSONL
    tmp = f"batch_{uuid.uuid4().hex}.jsonl"
    with open(tmp, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    headers_auth = {"Authorization": f"Bearer {api_key}"}
    upload_url = "https://api.mistral.ai/v1/files"  # Files API (NOT /v1/batch/files)

    try:
        # 3) Upload file with purpose=batch
        with open(tmp, "rb") as fh:
            files = {"file": (os.path.basename(tmp), fh, "application/jsonl")}
            data = {"purpose": "batch"}
            up = requests.post(upload_url, headers=headers_auth, files=files, data=data, timeout=120)
        up.raise_for_status()
        file_id = up.json()["id"]

        # 4) Create the batch job
        job_url = "https://api.mistral.ai/v1/batch/jobs"
        job_payload = {
            "input_files": [file_id],
            "model": model,         # the single model used for the whole batch
            "endpoint": endpoint,   # e.g., /v1/chat/completions
            "timeout_hours": timeout_hours,
        }
        job = requests.post(job_url, headers=headers_auth, json=job_payload, timeout=60)
        job.raise_for_status()
        job_id = job.json()["id"]

        # 5) Poll until completion (SUCCESS or a terminal failure)
        status_url = f"https://api.mistral.ai/v1/batch/jobs/{job_id}"
        terminal_failures = {"FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"}  # you may also handle CANCELLATION_REQUESTED separately
        output_file_id = None

        while True:
            st = requests.get(status_url, headers=headers_auth, timeout=30)
            st.raise_for_status()
            j = st.json()
            status = j.get("status")
            if status == "SUCCESS":
                output_file_id = j.get("output_file")
                break
            if status in terminal_failures:
                raise RuntimeError(f"Batch job ended with status: {status}")
            time.sleep(poll_interval)

        if not output_file_id:
            raise RuntimeError("Batch job succeeded but no output_file was returned.")

        # 6) Download the results JSONL file content
        dl_url = f"https://api.mistral.ai/v1/files/{output_file_id}/content"
        parsed_lines = []
        with requests.get(dl_url, headers=headers_auth, stream=True, timeout=120) as r:
            r.raise_for_status()
            for raw_line in r.iter_lines(decode_unicode=True):
                if raw_line:
                    parsed_lines.append(json.loads(raw_line))

        # 7) Sort back to input order and extract assistant content
        def _extract_chat_content(item):
            # Each JSONL line may contain either "response" or "error"
            if item.get("error"):
                # choose: 'raise' (current), 'skip', or placeholder
                raise RuntimeError(f'Item {item.get("custom_id")} failed: {item["error"]}')
            resp = item.get("response", {})
            return resp["choices"][0]["message"]["content"]

        sorted_results = sorted(parsed_lines, key=lambda x: int(x.get("custom_id", 0)))
        raw_responses = [_extract_chat_content(item) for item in sorted_results]
        outputs = [post_process_response(text) for text in raw_responses]

        return outputs

    finally:
        # Always clean up the temp file
        try:
            os.remove(tmp)
        except OSError:
            pass
