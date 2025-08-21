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
        df = pd.read_excel(file_path, engine='openpyxl')
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
        pd.DataFrame: Rows that satisfy all comparison criteria
    """
    # Validate columns exist
    if unique_col not in df.columns:
        print(f"Column '{unique_col}' not found in DataFrame")
        return pd.DataFrame()
    
    valid_list_cols = [col for col in list_cols if col in df.columns]
    if len(valid_list_cols) < len(list_cols):
        print(f"Some columns in list_cols were not found in the DataFrame")
    
    # Function to extract words from a cell
    def extract_words(text):
        if pd.isna(text):
            return []
        return re.findall(r'\b\w+\b', str(text).lower())
    
    # Process each row
    matching_indices = []
    for idx, row in df.iterrows():
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
                break
        
        # Check if combined has any extra words
        for word in combined_word_counts:
            if word not in unique_word_counts:
                match = False
                break
        
        if match:
            matching_indices.append(idx)
    
    return df.loc[matching_indices]

# Example usage (uncomment to test)
# if __name__ == "__main__":
#     # Load keywords from JSON file
#     with open('common_words.json', 'r', encoding='utf-8') as f:
#         common_words = json.load(f)
#     
#     # Extract data from Excel
#     df = extract_columns_from_excel('Adresses_test.xlsx', ['Adresse concat', 'Column2'])
#     
#     # Check for specific keywords in a column
#     has_keywords = check_keywords_in_column(df, 'Adresse concat', common_words['rue'])
#     
#     # Filter DataFrame based on keyword matches
#     keyword_matches = df[has_keywords]
#     print(f"Found {len(keyword_matches)} rows with street keywords")