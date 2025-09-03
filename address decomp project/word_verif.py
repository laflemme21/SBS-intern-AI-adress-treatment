import pandas as pd
import re
import json

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

def all_columns_keyword_check(df, list_of_keywords, list_of_columns,n):
    """
    Check if any of the keywords are present in all specified columns of the DataFrame.
    if a key word is specified in a columns from the same index as the list it belongs to, 
    we increment a value, if it is found in a different column, we increment another value

    Args:
        list_of_keywords (list): List of keywords to check for.
        list_of_columns (list): List of column names to check in.

    Returns:
        pd.Series: A boolean Series indicating the presence of keywords in all columns.
    """
    right_keywords = 0
    right_indices = []
    for keywords, column in zip(list_of_keywords, list_of_columns):
        if column in df.columns:
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                mask = df[column].astype(str).str.lower().str.contains(pattern, regex=True, na=False)
                right_keywords += mask.sum()
                if mask.any():
                    right_indices.extend(df[mask].index.tolist())
        else:
            print(f"Column '{column}' not found in DataFrame")
            return None

    wrong_keywords = 0
    wrong_indices = []
    for k in range(len(list_of_keywords)):
        for c in [i for i in range(len(list_of_columns)) if i != k]:
            column = list_of_columns[c]
            if column in df.columns:
                for keyword in list_of_keywords[k]:
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    mask = df[column].astype(str).str.lower().str.contains(pattern, regex=True, na=False)
                    wrong_keywords += mask.sum()
                    if mask.any():
                        wrong_indices.extend((df[mask].index.tolist(),keyword))

    # Print the index of the first 10 right and wrong addresses
    # print("First 10 indices of right addresses:", right_indices[:10])
    print(f"First {n} keywords wrongly placed, with indices:", wrong_indices[:n*2])

    return right_keywords, wrong_keywords


# Example usage (uncomment to test)
if __name__ == "__main__":
    # Load keywords from JSON file
    with open('common_words.json', 'r', encoding='utf-8') as f:
        common_words = json.load(f)

    columns=['Adresse concat','Numero de voie et voie','immeuble residence','Appartement / etage','mention speciale / lieu dit']
    number_of_rows = 60

    # Extract data from Excel
    df = extract_columns_from_excel('ministral-400-answers.csv', columns)

    # keep the number of rows specified
    df = df.head(number_of_rows)

    # Strip all cells before checking for non-empty cells
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    # Replace cells that are empty strings (after stripping) with NaN
    df = df.replace('', pd.NA)

    # keep only rows that have one or more non empty cells
    df = df[df.notna().sum(axis=1) >= 1]

    number_of_non_empty_cells = df.notna().sum().sum()
    # Check for specific keywords in columns, and get the number of matches in the right and wrong columns
    keyword_columns=columns[1:]
    right_columns,wrong_columns = all_columns_keyword_check(df, list(common_words.values()), keyword_columns,5)
    print(f"Found {right_columns} rows with keywords in the right columns, percentage of right: {right_columns/(right_columns+wrong_columns)*100:.2f}%")
    print(f"Found {wrong_columns} rows with keywords in the wrong columns, percentage of wrong: {wrong_columns/(wrong_columns+right_columns)*100:.2f}%")
    print(f"Percentage of non empty cells with keywords: {(right_columns+wrong_columns)/(number_of_non_empty_cells)*100:.2f}%")

    num_of_complete_matches, unmatching_indices = compare_word_sets(df,'Adresse concat' , ['Numero de voie et voie','immeuble residence', 'Appartement / etage', 'mention speciale / lieu dit'])

    print(f"Indices of unmatching rows: {unmatching_indices} len: {len(unmatching_indices)}")
    print(f"Number of rows where all words match exactly: {num_of_complete_matches} out of {len(df)} ({num_of_complete_matches/len(df)*100:.2f}%)")


