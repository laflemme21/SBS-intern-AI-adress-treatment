import asyncio
import random 


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
            
            # Check for error at the top level
            if "object" in response_json and response_json.get("object") == "error":
                error = response_json.get('message', 'Unknown error')
                print(f"Mistral request failed with error {error}, {retries} retries")
                # Check for rate limit and retry
                if error == "Rate limit exceeded":
                    await asyncio.sleep(random.expovariate(1/(0.5+5)))  # Random sleep to avoid hitting the rate limit again
            else:
                try:
                    # Handle the nested structure - check if we have a 'body' field (batch API)
                    content_container = response_json
                    if "body" in response_json:
                        content_container = response_json["body"]
                    
                    # Access choices safely
                    choices = content_container.get('choices', [])
                    if not choices or not isinstance(choices, list) or len(choices) == 0:
                        print(f"No valid choices found in response. Full response: {response_json}")
                        return "N/A", "N/A", "N/A", "N/A", "N/A"
                    
                    # Access message safely
                    message = choices[0].get('message', {})
                    if not message:
                        print(f"No message found in first choice. Full response: {response_json}")
                        return "N/A", "N/A", "N/A", "N/A", "N/A"
                    
                    # Extract content safely
                    content_field = message.get('content')
                    raw_content = ""
                    
                    if isinstance(content_field, str):
                        raw_content = content_field
                    elif isinstance(content_field, list):
                        for item in content_field:
                            if isinstance(item, dict) and "text" in item:
                                raw_content += item["text"]
                        if not raw_content:
                            raw_content = str(content_field)
                    else:
                        raw_content = str(content_field)
                    
                    result = post_process_response(raw_content)
                    return result
                    
                except Exception as e:
                    print(f"Error extracting content: {e}")
                    print(f"Full response: {response_json}")
                    return "N/A", "N/A", "N/A", "N/A", "N/A"
        except Exception as e:
            print(f"Mistral request failed: {e}, {retries} retries")
            await asyncio.sleep(0.2)
        finally:
            retries += 1
    
    print("Max retries exceeded, returning default values.")
    return "N/A", "N/A", "N/A", "N/A", "N/A"

