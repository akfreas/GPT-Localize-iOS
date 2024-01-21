#!/usr/bin/env python3

import argparse
import json
from openai import OpenAI
from collections import deque
import os
from pprint import pprint
import tiktoken
from tqdm import tqdm
from termcolor import colored

language_names = {
        "en": "English",
        "de": "German",
        "es": "Spanish",
        "fr": "French",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "pt": "Portuguese",
        "zh": "Chinese",
        "ar": "Arabic",
        "cs": "Czech",
        "da": "Danish",
        "fi": "Finnish",
        "el": "Greek",
        "hi": "Hindi",
        "hu": "Hungarian",
        # add more languages here
}


class LocalizationString:
    def __init__(self, string, comment):
        self.string = string
        self.comment = comment

    def __repr__(self):
        return f"LocalizationString(value={self.string}, comment={self.comment})"

    def __eq__(self, other):
        return self.comment == other.comment and self.string == other.string
    
    def serialize(self):
        return {
            "string": self.string,
            "comment": self.comment,
        }
    
COST_PER_THOUSAND_TOKENS = 0.01  # $0.01 per 1k tokens
model = "gpt-4-1106-preview"

def chunk_requests(requests, chunk_size):
    for i in range(0, len(requests), chunk_size):
        yield requests[i:i + chunk_size]

def estimate_tokens(data, source_lang, target_lang):
    tokens = []
    for chunk in chunk_requests(data, 10):
        full_prompt = json.dumps(create_prompt(source_lang, target_lang, chunk))
        encoding = tiktoken.encoding_for_model(model)
        tokens.extend(encoding.encode(full_prompt))
    return len(tokens) * 2 # Account for response tokens

def calculate_cost(token_count):
    # Calculate the cost based on the token count and cost per token
    return (token_count / 1000) * COST_PER_THOUSAND_TOKENS

def create_prompt(source_lang, target_lang, strings):
    serialized = [string.serialize() for string in strings]

    """
    Creates a prompt for translation based on the source and target languages and the serialized strings.
    """
    app_context = ""
    system = f"""
    You are translating strings from an app from {source_lang} to {target_lang}. 
    {app_context}
    """
    prompt = f"Translate the \"string\" property in the following JSON  array from {source_lang} to {target_lang}."
    prompt += " Use the \"comment\" property to understand the context of the string, if there is one.\n\n"
    prompt += json.dumps(serialized) + "\n\nReturn a JSON object in the following format: {\"translations\": [{\"string\": \"<translated>\"}]}.\n\n"
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]
    
    return messages

def translate_strings(openai_client, strings, source_lang, target_lang):
    translations = []
    total_tokens = 0

    # Preparing the list of chunks
    chunks = list(chunk_requests(strings, 10))

    # Initialize tqdm with a description
    with tqdm(chunks, desc="Translating chunks") as pbar:
        for chunk in pbar:
            messages = create_prompt(source_lang, target_lang, chunk)
            
            response = openai_client.chat.completions.create(
                model=model, 
                messages=messages,
                response_format={"type": "json_object"},
            )
            total_tokens += response.usage.total_tokens
            parsed_response = json.loads(response.choices[0].message.content)
            translations.extend(parsed_response.get("translations", []))

            # Update the postfix with a custom message including "Total tokens used"
            pbar.set_postfix_str(colored(f"Total tokens used: {total_tokens}.", "light_blue") + colored(f"Cost: ${calculate_cost(total_tokens):.2f}", "yellow"))

    return translations, total_tokens

# Main function to handle the translation process
def translate_xccstrings_file(input_file, target_lang, source_lang, overwrite_file, no_cost_prompt):

    # Check if OPENAI_API_KEY is set
    if "OPENAI_API_KEY" not in os.environ:
        # If not, prompt the user to enter it
        print(colored("OPENAI_API_KEY environment variable not set.", "yellow"))
        print(colored("Please enter your OpenAI API key:", "yellow"))
        api_key = input()
    else:
        api_key = os.environ["OPENAI_API_KEY"]

    openai_client = OpenAI(
        api_key=api_key,
    )

    with open(input_file, 'r') as file:
        data = json.load(file)

    strings_to_translate = []
    paths = []

    # Collect strings that need translation
    for key, value in data["strings"].items():
        localizations = value["localizations"]
        comment = value.get("comment", "")  

        source_localization = localizations.get(source_lang)
        if target_lang not in localizations.keys():
            if source_localization.get("variations") is None and source_localization.get("stringUnit") is not None:
                string_value = source_localization.get("stringUnit").get("value")
                strings_to_translate.append(LocalizationString(string_value, comment))
                paths.append((key, target_lang, None))
            elif source_localization.get("variations") is not None:
                device_variations = source_localization["variations"]
                for variation_key, variation_value in device_variations.items():
                    for device, device_content in variation_value.items():
                        string_value = device_content["stringUnit"]["value"]
                        strings_to_translate.append(LocalizationString(string_value, comment))
                        paths.append((key, target_lang, (variation_key, device)))
    
    if len(strings_to_translate) == 0:
        print(colored("No strings to translate!", "green"))
        return
    
    estimated_tokens = estimate_tokens(strings_to_translate, source_lang, target_lang)
    target_file = input_file
    if not overwrite_file and os.path.exists(input_file):
        # prompt to overwrite the file
        print(colored(f"Do you want to overwrite the existing .xcstrings file at {input_file}? (y/n)", "yellow"))
        if input().lower() != "y":
            # ask for a new file name
            print(colored("Please enter a new file path to save the output:", "yellow"))
            new_file_name = input()
            target_file = new_file_name    

    if not no_cost_prompt:
        print(colored(f"Estimated cost for {estimated_tokens} tokens using {model}: ${calculate_cost(estimated_tokens):.2f}", "yellow"))
        print(colored("Do you want to continue? (y/n)", "yellow"))
        if input().lower() != "y":
            print("Aborting...")
            return
    

    translated_strings, total_tokens = translate_strings(openai_client, strings_to_translate, language_names[source_lang], language_names[target_lang])

    print(colored(f"Total tokens used: {total_tokens}. Cost: ${calculate_cost(total_tokens):.2f}"))

    for path, translation in zip(paths, translated_strings):

        key, lang, variation_path = path
        if "strings" not in data:
            data["strings"] = {}
        if key not in data["strings"]:
            data["strings"][key] = {"localizations": {}}
        if lang not in data["strings"][key]["localizations"]:
            data["strings"][key]["localizations"][lang] = {}

        if variation_path is None:
            data["strings"][key]["localizations"][lang] = {
                "stringUnit": {
                    "value": translation.get("string"),
                    "state": "translated",
                }
            }
        else:
            variation_key, device = variation_path

            if "variations" not in data["strings"][key]["localizations"][lang]:
                data["strings"][key]["localizations"][lang]["variations"] = {}

            if variation_key not in data["strings"][key]["localizations"][lang]["variations"]:
                data["strings"][key]["localizations"][lang]["variations"][variation_key] = {}


            data["strings"][key]["localizations"][lang]["variations"][variation_key][device] = {
                "stringUnit": {
                    "value": translation.get("string"),
                    "state": "translated",
                }
            }

    with open(target_file, 'w') as file:
        json.dump(data, file, indent=4)

    print(f"Translation completed. Output saved to {target_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate .xcstrings files using OpenAI.")
    parser.add_argument("--input-file", type=str, help="Input .xcstrings file to be translated.", required=True)
    parser.add_argument("--target-language-code", type=str, help="Target language code (eg. 'en' or 'de').", required=True)
    parser.add_argument("--source-language-code", type=str, help="Source language code. (eg. 'en' or 'de')", required=True)
    parser.add_argument("--overwrite-file", help="Prompt to overwrite the xccstrings file.", required=False, default=False, action="store_true")
    parser.add_argument("--no-cost-prompt", help="Prompt to confirm the cost.", required=False, default=True, action="store_true")
    args = parser.parse_args()

    translate_xccstrings_file(args.input_file, args.target_language_code, args.source_language_code, args.overwrite_file, args.no_cost_prompt)
