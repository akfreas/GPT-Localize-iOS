#!/usr/bin/env python3

import argparse
import os
import openai
from pprint import pprint
import os
from openai import OpenAI
from tqdm import tqdm  
from termcolor import colored
import json
import tiktoken

COST_PER_THOUSAND_TOKENS = 0.01  # $0.01 per 1k tokens
model = "gpt-4-1106-preview"
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)
def estimate_tokens(text, source_lang, target_lang, app_context):
    full_prompt = json.dumps(create_prompt(text, source_lang, target_lang, app_context))
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(full_prompt)
    return len(tokens)

def calculate_cost(token_count):
    # Calculate the cost based on the token count and cost per token
    return (token_count / 1000) * COST_PER_THOUSAND_TOKENS

def create_prompt(text, source_lang, target_lang_code, app_context):
    languages = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "pt": "Portuguese",
        "ru": "Russian",
    }
    target_lang = languages[target_lang_code]
    prompt = f"Translate the following iOS app strings from {source_lang} to {target_lang}, keeping the format intact.\n{text}"
    system = f"""
    You are translating strings from an app from English to {target_lang}. 
    Do not translate the keys (left side of the = sign), only the values.
    If the string is already in {target_lang}, and the meaning is not significantly different than the existing string, you can leave it as is.
    {app_context}
    """
    messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    return messages

def translate_text(text, source_lang, target_lang_code, app_context, filename_comment):
    messages = create_prompt(text, source_lang, target_lang_code, app_context)
    tqdm.write(f"Translating chunk: {filename_comment}")
    response = client.chat.completions.create(model="gpt-4-1106-preview", messages=messages)
    tqdm.write(f"Finished translating chunk: {filename_comment}. Used {response.usage.total_tokens} tokens.")
    return response.choices[0].message.content

def parse_localization_file(file_path):
    if not os.path.exists(file_path):
        print(colored(f"Localization file not found: {file_path}", "red"))
        return
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    localization_dict = {}
    current_file = None

    for line in lines:
        line = line.strip()
        if line.startswith('/*') and line.endswith('*/'):
            current_file = line[2:-2].strip()
        elif '=' in line:
            key_value = line.split('=')
            key = key_value[0].strip().strip('"')
            value = key_value[1].strip().strip('";')
            if current_file not in localization_dict:
                localization_dict[current_file] = []
            localization_dict[current_file].append({'key': key, 'value': value})
    return localization_dict


def write_translations(localization_dict, target_lang_code, app_context_path, target_directory):

    if "lproj" in target_directory:
        print(colored("Target directory should be the directory that contains the lproj directories, not the lproj directory itself", "red"))
        return

    if not os.path.exists(target_directory):
        print(colored("Target directory not found", "red"))
        return

    directory = os.path.join(target_directory, f"{target_lang_code}.lproj")
    if os.path.exists(directory):
        print(colored(f"Target directory {directory} already exists. Overwrite? [y/n]", "yellow"))
        response = input()
        if response.lower() != 'y':
            return
    if not os.path.exists(app_context_path):
        # create a context file from input
        print(colored(f"App context file {app_context_path} not found. Create? [y/n]", "yellow"))
        response = input()
        if response.lower() != 'y':
            print(colored("App context file not found. Add the app context file and try again.", "red"))
            return
        else:
            print(colored("Describe the app you would like to localize. This helps the model understand the context of the strings:", "light_blue"))
            app_context = input()
            with open(app_context_path, 'w', encoding='utf-8') as file:
                file.write(app_context)
                print(colored(f"Created app context file at {app_context_path}", "green"))
    with open(app_context_path, 'r', encoding='utf-8') as file:
        app_context = file.read()
    os.makedirs(directory, exist_ok=True)
    total_tokens = 0
    for filename_comment, texts in localization_dict.items():
        text = list(map(lambda text: f"\"{text['key']}\" = \"{text['value']}\";", texts))
        joined = "\n".join(text)
        total_tokens += estimate_tokens(joined, "English", target_lang_code, app_context)

    total_cost = calculate_cost(total_tokens)
    print(colored(f"Estimated total tokens: {total_tokens}", 'green'))
    print(colored(f"Estimated total cost: ${total_cost:.2f}", 'green'))
    
    user_confirmation = input(colored("Do you want to proceed with the translation? (y/n): ", "yellow"))
    if user_confirmation.lower() != 'y':
        print(colored("Translation cancelled by the user.", 'red'))
        return

    with open(os.path.join(directory, "Localizable.strings"), 'w', encoding='utf-8') as file:
        progress_bar = tqdm(localization_dict.items(), desc="Processing", unit="chunk")

        # Wrap localization_dict.items() with tqdm for progress tracking
        for filename_comment, texts in progress_bar:
            text = list(map(lambda text: f"\"{text['key']}\" = \"{text['value']}\";", texts))

            joined = "\n".join(text)
            
            translated_text = translate_text(joined, "English", target_lang_code, app_context, filename_comment)
            file.write(f"/* {filename_comment} */\n{translated_text} \n\n")
            tqdm.write(f"Wrote translated chunk to file: {filename_comment}")
            progress_bar.set_description(f"Processing {filename_comment}")

def main():
    parser = argparse.ArgumentParser(description="Localize iOS app strings")
    parser.add_argument("--source_file", type=str, help="Path to the source localization file", required=True)
    parser.add_argument("--target_dir", type=str, help="Path to the target strings resource directory", required=True)
    parser.add_argument("--target_lang_code", type=str, help="Target language for translation", required=True)
    parser.add_argument("--app_context", type=str, help="Path to the app context file that describes the app that the strings are from", required=False, default="app_context.txt")
    parser.add_argument("--only_new", type=bool, help="Only translate strings that are not already in the target language", required=False, default=False)
    args = parser.parse_args()

    localization_data = parse_localization_file(args.source_file)
    write_translations(localization_data, args.target_lang_code, args.app_context, args.target_dir)

if __name__ == "__main__":
    main()
