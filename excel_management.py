import pandas as pd

# Function to extract addresses from an Excel file
def extract_addresses_from_excel(file_path, n_rows=None):
    """
    Extracts addresses from a specified column in an Excel file.

    Args:
        file_path (str): Path to the Excel file.
        n_rows (int, optional): Number of rows to process. If None, processes all rows.

    Returns:
        pd.DataFrame: A DataFrame containing the extracted rows.
    """
    df = pd.read_excel(file_path, engine='openpyxl')
    if n_rows:
        df = df.head(n_rows)['Adresse concat']

    return list(df)

# Function to update the Excel file with treated data
def update_excel_with_treated_data(file_path, updated_data, start_col=12):
    """
    Updates the Excel file with treated data.

    Args:
        file_path (str): Path to the Excel file.
        updated_data (list of tuples): List of tuples containing treated data.
        start_col (int): Starting column index to update in the Excel file.
    """
    df = pd.read_excel(file_path, engine='openpyxl', header=None)
    for index, row in enumerate(updated_data):
        for col_offset, value in enumerate(row):
            df.iloc[index, start_col + col_offset] = value
    df.to_excel(file_path, index=False, header=False, engine='openpyxl')

if __name__ == "__main__":
    # Example usage
    file_path = 'Adresses_test.xlsx'
    n_rows = 10  # Number of rows to process
    addresses = extract_addresses_from_excel(file_path, n_rows) 
    print(list(addresses))

