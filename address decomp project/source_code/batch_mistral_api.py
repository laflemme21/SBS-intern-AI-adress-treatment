import json, uuid, time, os, random
import httpx
from typing import List, Dict, Any, Optional, Tuple
import json
import os
import random
import string

# Reuse your existing post_process_response

class MistralBatchError(Exception):
    pass

def _build_jsonl_lines(
    prompts: List[str],
    url: str,
    chat_params: Dict[str, Any],
    start_index: int = 0
):
    for i, prompt in enumerate(prompts, start_index):
        yield {
            "custom_id": str(i),
            "method": "POST",
            "url": url,  # e.g. /v1/chat/completions
            "body": {
                **chat_params,
                "messages": [{"role": "user", "content": prompt}],
            },
        }

def write_temp_jsonl(objs,path=None) -> str:
    if path is None:
        path = f"batch_{uuid.uuid4().hex}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for obj in objs:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return path

def _poll_job(client: httpx.Client, job_id: str, api_key: str,
              min_interval=3, max_interval=25, max_wait_sec=3600):
    status_url = f"https://api.mistral.ai/v1/batch/jobs/{job_id}"
    deadline = time.time() + max_wait_sec
    attempt = 0
    while True:
        if time.time() > deadline:
            raise MistralBatchError("Polling timeout exceeded.")
        r = client.get(status_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "SUCCESS":
            return data.get("output_file")
        if status in {"FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"}:
            raise MistralBatchError(f"Job ended with status {status}: {data}")
        # Backoff
        sleep_for = min_interval * (2 ** min(attempt, 5))
        sleep_for = random.uniform(sleep_for * 0.7, sleep_for * 1.3)
        sleep_for = min(sleep_for, max_interval)
        time.sleep(sleep_for)
        attempt += 1

def _download_output_lines(client: httpx.Client, file_id: str, api_key: str):
    url = f"https://api.mistral.ai/v1/files/{file_id}/content"
    with client.stream("GET", url, headers={"Authorization": f"Bearer {api_key}"}, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                yield json.loads(line)

def _extract_content_from_item(item: Dict[str, Any]) -> str:
    """Extract content from batch API response, handling nested 'body' structure."""
    # Check for error
    if item.get("error"):
        print(f"Item error: {item['error']}")
        return "N/A;N/A;N/A;N/A"
    
    # Get response or response body
    resp = item.get("response", {})
    
    # Handle nested structure with 'body' field
    if "body" in resp:
        resp_body = resp["body"]
    else:
        resp_body = resp
    
    # Get choices from the appropriate level
    choices = resp_body.get("choices")
    if not choices:
        print(f"No choices in response body: {resp_body}")
        return "N/A;N/A;N/A;N/A"
    
    try:
        # Extract message and content
        msg = choices[0].get("message", {})
        content = msg.get("content")
        
        # Handle different content formats
        if content is None:
            print(f"Content is None in message: {msg}")
            return "N/A;N/A;N/A;N/A"
        
        if isinstance(content, list):
            collected = []
            for frag in content:
                if isinstance(frag, dict) and "text" in frag:
                    collected.append(frag["text"])
            content = "".join(collected) if collected else str(content)
        
        if not isinstance(content, str):
            content = str(content)
            
        return content
    except Exception as e:
        print(f"Error extracting message: {e}\nResponse: {resp}")
        return "N/A;N/A;N/A;N/A"  # Return default value instead of None
    # Support content list segments
    

def send_batch_prompts(
    prompts: List[str],
    api_key: str,
    model: str = "mistral-small-latest",
    endpoint: str = "/v1/chat/completions",
    batch_size: int = 5000,
    timeout_hours: int = 1,
    poll_max_wait_sec: int = 3600,
    chat_params: Optional[Dict[str, Any]] = None
) -> List[Tuple[str, str, str, str]]:
    """
    Submit prompts via one or multiple Mistral batch jobs and return processed tuples.

    Returns list aligned to input order. Each element is a 4‑tuple from post_process_response.

    If any individual item fails, its slot is filled with ('N/A',...).
    """
    chat_params = chat_params or {}
    # Model centralized at job level if not overridden per line.
    if "model" in chat_params:
        raise ValueError("Put model in the function param, not inside chat_params.")
    url_path = endpoint  # e.g. /v1/chat/completions

    results_map = {}  # custom_id -> processed tuple
    client = httpx.Client(timeout=30)

    try:
        # Split into chunks to respect size limits
        for chunk_index, start in enumerate(range(0, len(prompts), batch_size)):
            sub_prompts = prompts[start:start + batch_size]
            # Build JSONL lines
            lines_iter = list(_build_jsonl_lines(sub_prompts, url_path, chat_params, start_index=start))
            tmp_path = write_temp_jsonl(lines_iter)

            # 1) Upload file
            with open(tmp_path, "rb") as fh:
                files = {"file": (os.path.basename(tmp_path), fh, "application/jsonl")}
                data_form = {"purpose": "batch"}
                up = client.post(
                    "https://api.mistral.ai/v1/files",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files=files,
                    data=data_form
                )
            up.raise_for_status()
            file_id = up.json()["id"]

            # 2) Create job
            job_payload = {
                "input_files": [file_id],
                "model": model,
                "endpoint": endpoint,
                "timeout_hours": timeout_hours,
                # "metadata": {"chunk_index": chunk_index}  # optional
            }
            job = client.post(
                "https://api.mistral.ai/v1/batch/jobs",
                headers={"Authorization": f"Bearer {api_key}"},
                json=job_payload
            )
            job.raise_for_status()
            job_id = job.json()["id"]

            # 3) Poll
            output_file_id = _poll_job(
                client, job_id, api_key,
                max_wait_sec=min(poll_max_wait_sec, timeout_hours * 3600)
            )

            # 4) Download output
            for item in _download_output_lines(client, output_file_id, api_key):
                cid = item.get("custom_id")
                content = _extract_content_from_item(item)
                tupled = str(content)
                results_map[int(cid)] = tupled

            # Cleanup tmp
            try:
                os.remove(tmp_path)
            except OSError:
                pass

        # Reassemble in order
        ordered = [results_map.get(i, ("N/A", "N/A", "N/A", "N/A", "N/A")) for i in range(len(prompts))]
        return ordered
    finally:
        client.close()

