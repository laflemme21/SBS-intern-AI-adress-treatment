from mistralai import Mistral
import json

# Load API keys from JSON file
with open('keys.json', 'r', encoding='utf-8') as f:
    api_keys = json.load(f)

# Initialize the Mistral client with the API key
client = Mistral(api_key=api_keys["mistral_api_key"])

# Function to read multi-line input from the user
def read_multiline_input(prompt="Enter your message. End with a single line containing only a dot '.' or send EOF (Ctrl+Z then Enter on Windows, Ctrl+D on Unix):"):
    print(prompt)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            # user sent EOF (Ctrl+Z on Windows + Enter, Ctrl+D on Unix)
            break
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()

# Function to run live chat
def live_chat():
    model = input("Enter the Mistral model (e.g., mistral-large-latest): ").strip()
    messages = []
    print("Starting live chat. Type 'exit' alone on a line to quit.")
    while True:
        user_input = read_multiline_input()
        if not user_input:
            continue
        if user_input.strip().lower() == "exit":
            break

        # Manually construct the message dictionary for user input
        user_message = {"role": "user", "content": user_input}
        messages.append(user_message)

        # Notify the user that their message was sent
        print("Message sent.")

        try:
            # If the client supports streaming, use it; otherwise use non-streaming chat call
            if hasattr(client, "chat_stream"):
                response = client.chat_stream(model=model, messages=messages)
                full_response = ""
                print("Assistant: ", end="", flush=True)
                for chunk in response:
                    # robustly extract delta content from chunk (object or dict)
                    delta = None
                    try:
                        delta = getattr(chunk.choices[0].delta, "content", None)
                    except Exception:
                        try:
                            delta = chunk["choices"][0]["delta"].get("content")
                        except Exception:
                            delta = None
                    if delta:
                        print(delta, end="", flush=True)
                        full_response += delta
                print()  # newline after stream
            else:
                # Non-streaming fallback
                resp = client.chat.complete(model=model, messages=messages)
                # robust extraction of assistant text
                try:
                    full_response = resp.choices[0].message.content
                except Exception:
                    try:
                        full_response = resp["choices"][0]["message"]["content"]
                    except Exception:
                        full_response = str(resp)
                print("Assistant:", full_response)

            # Append assistant response to history
            assistant_message = {"role": "assistant", "content": full_response}
            messages.append(assistant_message)

        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    live_chat()