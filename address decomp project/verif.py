import pandas as pd
import re
import json
from jsonschema import validate

def extract_columns_from_excel(file_path, columns):
    """
    Extract specific columns from an Excel file into a pandas DataFrame.
    
    Args:
        file_path (str): Path to the Excel file
        columns (list): List of column names to extract
        
    Returns:
        pd.DataFrame: DataFrame containing only the specified columns
    """
    try:
        
        if file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path, engine='calamine')
        elif file_path.endswith(".csv"):
            df = pd.read_csv(file_path, header=0, dtype=str, encoding='utf-8-sig',delimiter=';')
        # Check if all specified columns exist
        for col in columns:
            if col not in df.columns:
                print(f"Warning: Column '{col}' not found in the file.")
        
        # Return only columns that exist in the DataFrame
        existing_columns = [col for col in columns if col in df.columns]
        return df[existing_columns]
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return pd.DataFrame()

def check_keywords_in_column(df, column, keywords):
    """
    Check if any keyword appears as a full word in cells of the specified column.
    
    Args:
        df (pd.DataFrame): The DataFrame to check
        column (str): The name of the column to check
        keywords (list): List of keywords to look for
        
    Returns:
        pd.Series: Boolean Series indicating for each row whether a keyword was found
    """
    if column not in df.columns:
        print(f"Column '{column}' not found in DataFrame")
        return pd.Series([False] * len(df))
    
    # Create a pattern that matches any keyword as a whole word
    pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
    
    # Apply the pattern to each cell in the column
    return df[column].astype(str).str.lower().str.contains(pattern, regex=True, na=False)

def compare_word_sets(df, unique_col, list_cols):
    """
    Compare words between a single column and a list of columns.
    
    For each row, checks if:
    1. All words from the single column are in the aggregated list columns
    2. No additional words in the list columns that aren't in the single column
    3. The frequency of each word matches in both places
    
    Args:
        df (pd.DataFrame): The DataFrame to check
        unique_col (str): Name of the single column to compare against
        list_cols (list): List of column names to aggregate and compare with
        
    Returns:
        int: number of rows that satisfy all comparison criteria
    """
    # Validate columns exist
    if unique_col not in df.columns:
        print(f"Column '{unique_col}' not found in DataFrame")
        return 0
    
    valid_list_cols = [col for col in list_cols if col in df.columns]
    if len(valid_list_cols) < len(list_cols):
        print(f"Some columns in list_cols were not found in the DataFrame")
    
    # Function to extract words from a cell
    def extract_words(text):
        if pd.isna(text):
            return []
        return re.findall(r'\b\w+\b', str(text))
    
    # Process each row
    matching_indices = []
    unmatching_indices = []
    for idx, row in pd.DataFrame(df).iterrows():
        # Get words from the unique column
        unique_words = extract_words(row[unique_col])
        unique_word_counts = {word: unique_words.count(word) for word in set(unique_words)}

        # Get words from all list columns combined
        combined_words = []
        for col in valid_list_cols:
            combined_words.extend(extract_words(row[col]))

        combined_word_counts = {word: combined_words.count(word) for word in set(combined_words)}

        # Check all criteria
        match = True
        
        # Check if unique words exist in combined with same frequency
        for word, count in unique_word_counts.items():
            if word not in combined_word_counts or combined_word_counts[word] != count:
                match = False
                unmatching_indices.append(idx)
                break
        if not match:
            continue
        # Check if combined has any extra words
        for word in combined_word_counts:
            if word not in unique_word_counts:
                match = False
                unmatching_indices.append(idx)
                break
        
        if match:
            matching_indices.append(idx)

    if len(unmatching_indices) + len(matching_indices) != len(df):
        print("ATTENTION: Some rows weren't checked or repeated")

    return len(matching_indices),unmatching_indices

def field_length_check(row, columns, min_lengths,max_lengths,weights):
    """
    Check if the length of the content in specified columns is at least min_length for a row.
    
    Args:
        row (pd.Series): The row to check
        columns (list): List of column names to check
        min_length (int): Minimum length required for each cell's content
        max_length (int): Maximum length allowed for each cell's content
        weights (list): List of weights to assign if length condition is met for each column

    Returns:
        list: A list of ints indicating for each row containing the updated grades
    """
    total_weight = 0
    for col,weight in zip(columns,weights):
            if isinstance(row[col], str) and min_lengths <= len(row[col]) <= max_lengths:
                total_weight += weight

    return total_weight

def grade_calculation(df, columns, common_words, weights,min_lengths=3,max_lengths=50):
    """
    Calculate a confidence score for each row based on multiple characteristics.
    
    Args:
        df (pd.DataFrame): The DataFrame to evaluate
        columns (list): List of column names to check
        common_words (list): List of common keywords to look for
        weights (list): List of weights to assign for each characteristic

    Returns:
        list: A list of ints indicating for each row the calculated confidence score
    """
    grades = [0 for _ in range(len(df))]
    
    for i in range(len(df)):
        # Check for keywords in the specified columns
        grades[i] += row_keyword_check(df.iloc[i], weights['keywords'], columns[1:], common_words)
        # Field length check
        grades[i] += field_length_check(df.iloc[i], columns[1:], min_lengths,max_lengths,weights['lengths'])
        # Check if the rue column starts with a number
        grades[i] += first_column_starts_number_check(df.iloc[i], columns[1], weights['rue_starts_number'])
        # Check if the column etage contains a number
        grades[i] += column_contains_number_check(df.iloc[i], columns[3], weights['etage_contains_number'])
        # Check if the column lieu dit contains a number
        grades[i] += column_contains_number_check(df.iloc[i], columns[4], weights['lieu_dit_contains_number'])
        # Compare words between the first column and the rest
        grades[i] += compare_word_sets_row(df.iloc[i], columns[0], columns[1:], weights['exact_word_match'])

    df['confidence score'] = grades
    return grades


def first_column_starts_number_check(row, column, weight):
    """
    Check if the content of the specified column starts with a number.
    If it does, add the specified weight to the grade.

    Args:
        row (pd.Series): The row to check.
        column (str): The name of the column to check.
        weight (int): The weight to add if the condition is met.

    Returns:
        int: The grade for the row.
    """
    grade = 0
    if isinstance(row[column], str) and re.match(r'^\d', row[column].strip()):
        grade += weight
    return grade

def column_contains_number_check(row, column, weight):
    """
    Check if the content of the specified column contains any number.
    If it does, add the specified weight to the grade.

    Args:
        row (pd.Series): The row to check.
        column (str): The name of the column to check.
        weight (int): The weight to add if the condition is met.

    Returns:
        int: The grade for the row.
    """
    grade = 0
    if isinstance(row[column], str) and re.search(r'\d', row[column]):
        grade += weight
    return grade


def row_keyword_check(row, weight, list_of_columns, keywords_dict):
    """
    For a single row, check for keywords in each specified column.
    For each keyword found in its corresponding column, add the corresponding weight.
    Returns the total grade for the row.

    Args:
        row (pd.Series): The row to check.
        weight (int): The weight for the column.
        list_of_columns (list): List of column names to check in.
        keywords_dict (dict): Dictionary with column names as keys and lists of keywords as values.

    Returns:
        int: The grade for the row.
    """
    grade = 0
    for column in list_of_columns:
        keywords = keywords_dict[column]
        cell = str(row[column]).lower() if column in row and pd.notna(row[column]) else ""
        for keyword in keywords:
            keyword=keyword.lower()
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, cell):
                grade += weight
    return grade

def compare_word_sets_row(row, unique_col, list_cols, weight):
    """
    Compare words between a single column and a list of columns for one row.

    Checks if:
    1. All words from the unique column are in the aggregated list columns
    2. No additional words in the list columns that aren't in the unique column
    3. The frequency of each word matches in both places

    Args:
        row (pd.Series): The row to check
        unique_col (str): Name of the single column to compare against
        list_cols (list): List of column names to aggregate and compare with
        weight (float or int): The weight to return if the condition is met

    Returns:
        float or int: The weight if the condition is met, else 0
    """
    def extract_words(text):
        if pd.isna(text):
            return []
        return re.findall(r'\b\w+\b', str(text))

    unique_words = extract_words(row[unique_col])
    unique_word_counts = {word: unique_words.count(word) for word in set(unique_words)}

    combined_words = []
    for col in list_cols:
        combined_words.extend(extract_words(row[col]))

    combined_word_counts = {word: combined_words.count(word) for word in set(combined_words)}

    # Check all criteria
    match = True
    for word, count in unique_word_counts.items():
        if word not in combined_word_counts or combined_word_counts[word] != count:
            match = False
            break
    if match:
        for word in combined_word_counts:
            if word not in unique_word_counts:
                match = False
                break

    return weight if match else 0

def verification_main(verification_parameters):
    with open(verification_parameters["mots_cles_file"], 'r', encoding='utf-8') as f:
        common_words = json.load(f)

    columns=verification_parameters["columns"]
    number_of_rows = verification_parameters["number_of_rows"]
    OUTPUT_FILE = verification_parameters["output_file"]

    # Extract data from Excel
    df = extract_columns_from_excel(verification_parameters["input_file"], columns)

    # keep the number of rows specified
    if number_of_rows >= 0:
        df = df.head(number_of_rows)

    # Strip all cells before checking for non-empty cells
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    # Replace cells that are empty strings (after stripping) with NaN
    df = df.replace('', pd.NA)

    # keep only rows that have one or more non empty cells
    df = df[df.notna().sum(axis=1) >= 1]

    number_of_non_empty_cells = df.notna().sum().sum()

    grades= grade_calculation(df, columns, common_words, verification_parameters["grading_weights"],verification_parameters["min_length"],verification_parameters["max_length"])
    df['confidence score'] = [f"{grade:.2f}" for grade in grades]
    if OUTPUT_FILE.endswith(".xlsx"):
        df.to_excel(OUTPUT_FILE, index=False)
    elif OUTPUT_FILE.endswith(".csv"):
        df.to_csv(OUTPUT_FILE, index=False, sep=';')

if __name__ == "__main__":
    with open('config.json', 'r', encoding='utf-8') as f, open('schema.json', 'r', encoding='utf-8') as v:
        config = json.load(f)
        schema = json.load(v)
        validate(instance=config, schema=schema)
        verification_parameters = config.get("verification_parameters", {})
    verification_main(verification_parameters)