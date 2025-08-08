import requests
import aiohttp
import asyncio


def post_process_response(content):
    fields = content.split(';')
    while len(fields) < 5:
        fields.append("N/A")
    return tuple(field.strip() for field in fields[:5])


async def call_mistral_async(session, prompt: str, api_key: str, model: str, max_retries=3):
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
            if "error" in response_json:
                error = response_json["error"]
                print(f"Mistral request failed with error {error}")
                # Check for rate limit and retry
                if isinstance(error, dict) and error.get("code") == "rate_limit_exceeded":
                    await asyncio.sleep(2)
                    retries += 1
                    continue
                return "N/A", "N/A", "N/A", "N/A", "N/A"
            # Extract the content and preprocess it immediately
            raw_content = response_json['choices'][0]['message']['content']
            # You can use your own post_process_response function here
            result = post_process_response(raw_content)
            if len(result) < 5:
                result = tuple(list(result) + ["N/A"] * (5 - len(result)))
            return result
        except Exception as e:
            print(f"Mistral request failed: {e}")
            await asyncio.sleep(0.2)
            retries += 1
    return "N/A", "N/A", "N/A", "N/A", "N/A"