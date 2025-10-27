Of course, here is the translation of the README file into English, with the original formatting preserved.

# SBS-intern-AI-address-treatment

# Table of Contents

1.  File Organization Overview
2.  Introduction to How the Tool Works
3.  Overview of Each Tool Function and Key Parameters
4.  Introduction to Key Documents

***

## 1. File Organization Overview

The project is structured as follows:
-   **source_code/**: Contains all Python scripts and the embedded Python interpreter.
-   **resources/**: Contains configuration files and storage files such as keywords, valid cities, etc.
-   **documentation/**: Project documentation and examples of documents used by the tool.
-   **in_out_files/**: Contains all files taken as input and rendered as output by the tool.
-   **execute.bat**: Launch script for Windows.

***

## 2. Introduction to How the Tool Works

This tool automates the decomposition of addresses using the Mistral AI API.
It takes an Excel/CSV file containing full addresses as input and produces a file
with these addresses broken down into several components (street, building, floor, etc.).
It can also provide a confidence score for each decomposed address and verify the validity of other fields such as the city and postal code.

### How to run the tool
1.  Double-click on `execute.bat` to launch the graphical interface or run it from the command line.
2.  In the first window, select the features to use.
3.  In the second window, configure the necessary parameters.
4.  Click "Run" to execute the processing.

The application automatically saves your parameters in the `config.json` file.

***

## 3. Overview of Functions and Key Parameters

### Functions Page (Features)
This page allows you to choose the functions to execute.

-   **use_mistral**: From a file containing addresses, sends them to Mistral in batches and extracts the responses from the output file. To save the result, `save_answers` must be checked.
-   **log_statistics**: If `use_mistral` is checked, this function will save the execution time and data about the execution in a log file.
-   **parse_and_save_batch_ans_file**: Extracts Mistral's responses from a file obtained after running a batch on "La Plateforme".
-   **save_answers**: If `use_mistral` is checked, this function saves the obtained result.
-   **build_and_save_prompts**: Generates a file containing prompts in a format that the Mistral batch API accepts. This file can be submitted to the batch API.
-   **calculate_conf_score**: Calculates a confidence score for each row and saves them in a file.
-   **check_postal_code**: Verifies that the postal code of each row exists in the file of all postal codes corresponding to the address's country.
-   **check_ville**: Verifies that the city of each row exists in the file of all cities corresponding to the address's country.

### Main Parameters

#### address_decomp_parameters
-   **api_key**: API key for Mistral.
-   **mistral_model**: Mistral model to use.
-   **input_file**: File containing the addresses to process. Must contain a column with the concatenated addresses.
-   **output_file**: File where the results will be saved.
-   **concat_column**: Name of the column containing the full address in the input file.
-   **pays_column**: Name of the column containing the country.
-   **output_columns**: List of column names to be generated in the output file. The column names can be changed, but they will always contain, in this order: concat, street, building, floor, mention.
-   **prompt_file**: Jinja2 file containing the prompt template. For each row, the country, the keywords contained in the address and their affiliated field, and the address to be processed are injected into it.

#### ans_grading_parameters
-   Parameters for evaluating the quality of the address decompositions.
-   Weights for different evaluation criteria.

#### address_verif_parameters
-   Parameters for verifying address components against reference files.

***

## 4. File Descriptions

### Configuration Files
-   `config.json`: Contains all configurable parameters of the application.
-   `schema.json`: Defines the structure and constraints of the parameters.
-   `keys.json`: Stores the API keys to access OpenAI and Mistral services.
-   `common_words.json`: Contains categorized lists of common words found in addresses:
    -   "Street number and name" (street, avenue, boulevard...)
    -   "Building/residence" (building, block, tower...)
    -   "Apartment/floor/staircase" (floor, apartment...)
    -   "Special mention/locality" (c/o, hamlet, locality...)

### User Interface
-   `gui.py`: Graphical user interface for configuring and launching the application.
    -   Feature selection window.
    -   Parameter configuration window with contextual descriptions (tooltips).
    -   Buttons to navigate, save the configuration, and execute the process.

### Main Scripts

#### `backend_main.py`
The main script that orchestrates the execution of the different features:
-   Loads the configuration from `config.json`.
-   Executes the selected functions in the appropriate order.

#### `address_decomp.py`
Script for address decomposition:
-   Opens and processes Excel/CSV address files.
-   Builds prompts using Jinja2 templates.
-   Sends batch requests to the Mistral API.
-   Calculates the accuracy of the results using the corrected data and generates logs.
-   **Dependencies**: `batch_mistral_api.py`, `common_words.json`, `keys.json`.

#### `batch_mistral_api.py`
Manages batch processing with the Mistral API:
-   Creates and manages batch jobs to process large quantities of prompts.
-   Handles file upload/download, job creation, and retrieval of results.
-   Extracts the content of API responses.
-   **Main function**: `send_batch_prompts()`

#### `grading.py`
Module for evaluating address decompositions:
-   Calculates confidence scores for each component.
-   Verifies the presence of keywords in the correct columns.
-   Analyzes the length and structure of the components.

#### `address_verif.py`
Module for verifying address components:
-   Checks postal codes and city names against reference files.
-   Generates a verification report.

### Data Files

#### `Adresses_test_correction.xlsx`
-   Excel file containing 1360 addresses with their corrected versions.

### Other Files

#### `prompt_7.j2`
The prompt used, offering an excellent quality-to-price ratio:
-   This prompt needs to be injected with the country, the address, and the context (keywords from the address).

#### `batch_log.txt`
Log file used to save details of each job performed by `address_decomp.py`.

The project forms a complete system for decomposing addresses into standardized components (street, building, apartment, special mention) using AI models, with tools for batch processing, fine-tuning, and result verification.
