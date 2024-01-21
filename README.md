# GPT-Localize-iOS

🇺🇸🇩🇪🇪🇸🇫🇷🇮🇹🇯🇵🇰🇷🇵🇹🇷🇺🇨🇳🇦🇷🇩🇰🇫🇮🇬🇷🇮🇳🇭🇺

## Reach more users for your app with localization!

GPT-Localize-iOS is a tool designed to automatically translate your `.xcstrings` files into any language, using the power and cost-effectiveness of OpenAI's GPT-4 API. This script can even handle translations tailored to various devices, ensuring your iOS app localization is seamless and accurate.

## Features

- **Multiple Language Support:** Translate your strings into tons of languages in record time
- **Contextual Translation:** The translation takes into account the comments for your strings and an overall app context string
- **Multi-Device Translation:** Supports translation of string catalog's device-specific strings
- **OpenAI GPT-4 Integration:** Utilizes the latest GPT-4 model for accurate and contextual translations.
- **Cost Estimation:** Provides an estimate of the translation cost before proceeding.


## Prerequisites

To use GPT-Localize-iOS, you must set up an OpenAI API key. Here's how to do it:

1. Visit [OpenAI's API](https://openai.com/api/) page and sign up for an API key.
2. Once you have your API key, you can set it as an environment variable `OPENAI_API_KEY` on your system. Alternatively, the script will prompt you to enter it when needed.

Ideally, you should have comments added for each localization key. This will greatly help GPT to understand what you are trying to achieve with each string, and will improve the outcome of the translation.

## Getting started

### Recommended: Use venv or virtualenv

Set up a virtual environment with venv or virtualenv first to isolate your dependencies.

### Install dependencies

Run `pip install -r requirements.txt` to install the necessary requirements.


## Usage

Ensure you have Python 3.x installed on your system to run the script. Here is an example command line invocation:

```sh
python3 translate_strings.py --input-file=path/to/your/file.xcstrings --target-language-code=es --source-language-code=en
```

### Command Line Flags

- `--input-file`: The path to your `.xcstrings` file to be translated.
- `--target-language-code`: The target language code (e.g., 'es' for Spanish).
- `--source-language-code`: The source language code of your strings (e.g., 'en' for English).
- `--overwrite-file`: (Optional) If set, the script will overwrite the original file with the translations.
- `--no-cost-prompt`: (Optional) If set to false, the script will prompt you for confirmation before proceeding with the translation, based on the estimated cost.
- `--app-context-path`: (Optional) Information about the app being translated in order to provide the best translation quality.

## Additional Resources

For more information on working with `.xcstrings` files, check out Apple's WWDC 2023 video, ["Discovering String Catalogs"](https://developer.apple.com/videos/play/wwdc2023/10155/).

## Disclaimer

This tool uses OpenAI's API for translations and may incur costs based on usage. Please check the [OpenAI pricing](https://openai.com/pricing/) for more details.
