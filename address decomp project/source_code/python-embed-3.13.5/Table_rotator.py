import os
import sys
import pandas as pd
import json



def load_and_clean_data(file_path, sheet_name, num_columns_to_remove):
    """Load the CSV-converted Excel sheet and perform initial cleaning."""
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=[0, 1], engine="calamine")
    # Remove the first 'num_columns_to_remove' columns
    if not isinstance(num_columns_to_remove, int) or num_columns_to_remove < 0:
        raise ValueError("Number of columns to remove must be a non-negative integer")
    if num_columns_to_remove > len(df.columns):
        raise ValueError("Number of columns to remove exceeds the number of columns in the DataFrame")
    
    # Drop the specified number of columns from the start
    for i in range(num_columns_to_remove):
        df.drop(columns=df.columns[0], inplace=True)
    
    # Rename a specific column by modifying the columns attribute
    df.columns = [(('Date', 'Date') if col == (
        'Unnamed: 1_level_0', 'Unnamed: 1_level_1') else col) for col in df.columns]
    
    if ('Date', 'Date') not in df.columns:
        raise ValueError("Check that the \"number of columns to remove from the start\" is correct and that the 'Date' column in the input file is the first and is unnamed.")

    # Remove all rows that contain NaN values in all columns
    df.dropna(how='all', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    return df

def create_columns_dict(df):
    """Create a dictionary from the column tuples."""
    all_cols = df.columns.tolist()
    # Create a 2D dictionary from the column tuples
    columns_dict = {}
    for col in all_cols:
        if isinstance(col, tuple) and len(col) == 2:  # Ensure it's a tuple with two elements
            outer_key, inner_key = col
            if outer_key not in columns_dict:
                columns_dict[outer_key] = {}
            # Store the original tuple as the value
            columns_dict[outer_key][inner_key] = col
    
    return columns_dict

def filter_by_date_range(df, columns_dict, start_date, end_date):
    """Filter rows by date range."""
    start = 0
    finish = len(df) - 1
    for index in range(len(df)):
        # start date included
        if pd.notna(df.iloc[index, 0]) and df[columns_dict['Date']['Date']][index] >= pd.to_datetime(start_date):
            start=index
            for index in range(start+1,len(df)):
                # end date excluded
                if pd.notna(df.iloc[index, 0]) and (df[columns_dict['Date']['Date']][index] >= pd.to_datetime(end_date)):
                    finish=index-1
                    break
                
            break
    df = df.iloc[start:finish + 1, :]
    df.reset_index(drop=True, inplace=True)
    
    return df

def create_output_headers(df):
    """Create headers for the output file."""
    data_headers = ['USERNAME', 'ACTIVITY', 'REF', 'CLIENT', 'DATE_DEBUT', 'DATE_FIN']
    data_headers_date = []
    for i in range(len(df)):
        date = df.iloc[i, 0]
        if type(date) == pd.Timestamp and not any(d.month == date.month and d.year == date.year for d in data_headers_date):
            data_headers_date.append(date)

    # Convert the dates to the desired format (Jan-2025, Feb-2025, etc.)
    for i in range(len(data_headers_date)):
        data_headers_date[i] = data_headers_date[i].strftime('%b-%Y')

    # Merge the two header lists
    data_headers = data_headers + data_headers_date
    
    return data_headers

def populate_output_dataframe(df, columns_dict, data_headers, refs_delim, refs_and_chara_delim):
    """Populate the output DataFrame."""
    data = pd.DataFrame(columns=data_headers)
    # Iterate through the input df and populate the output df
    for empID in list(columns_dict.keys())[1:]:
        for index in range(len(df)):
            date_index = index
            #if the activity is pilotage, set the reference to "__Pilotage__" for future treatment
            if pd.isna(df.at[df.index[index], columns_dict[empID]['Réf']]) and "pilotage" in str(df.at[df.index[index], columns_dict[empID]['Activité']]).lower():
                df.at[df.index[index], columns_dict[empID]['Réf']] = "__Pilotage__"

            # Check that the reference is not NaN
            if not pd.isna(df.at[df.index[index], columns_dict[empID]['Réf']]):

                # Check if the date is NaT and replace it with the previous date
                if pd.isna(df[columns_dict['Date']['Date']][index]):
                    date_index = index - 1

                data = add_or_update_row(data, df, columns_dict, empID, index, date_index, refs_delim, refs_and_chara_delim)

    return data

def add_or_update_row(data, df, columns_dict, empID, index, date_index, refs_delim, refs_and_chara_delim):
    """
    Add a new row to 'data' if REF does not exist, or update the existing row if it does.
    Handles both single and multiple refs (separated by delimiteur de refs).
    """
    refs_cell = df.at[df.index[index], columns_dict[empID]['Réf']]
    # discard anything after -
    if refs_and_chara_delim in refs_cell:
        refs_cell = refs_cell.split(refs_and_chara_delim)[0]
    if refs_delim in refs_cell:
        refs = refs_cell.split(refs_delim)
    else:
        refs = [refs_cell]

    for ref in refs:
        ref = ref.strip()
        index_to_update = None
        # Treat USERNAME "libre" as nonexistent
        if str(empID).lower() == "libre":
            continue
        # Check if the REF already exists in the output DataFrame and get its index if it does
        for i in range(len(data['REF'].values)):
            if data.at[data.index[i], 'REF'] == ref and data.at[data.index[i], 'USERNAME'] == str(empID):
                index_to_update = data.index[i]
                break

        # Calculate the value to add or set for the month column
        month_col = df.at[df.index[date_index], columns_dict['Date']['Date']].strftime('%b-%Y')
        ref_share = 1 / len(refs) if len(refs) > 0 else 1 # 1 is a half day
        ref_share /= 2  # 1 is a full day

        # If the REF does not exist, create a new row and populate it
        if index_to_update is None:
            # Create a new row with proper data types to avoid FutureWarning
            new_row = {}
            for col in data.columns:
                if col in ['USERNAME', 'ACTIVITY', 'REF', 'CLIENT']:
                    new_row[col] = ""  # Initialize string columns as empty strings
                elif col in ['DATE_DEBUT', 'DATE_FIN']:
                    new_row[col] = pd.NaT  # Initialize date columns as NaT
                else:
                    new_row[col] = 0.0  # Initialize numeric columns as 0

            # Populate with actual values
            new_row['USERNAME'] = str(empID)  # Ensure USERNAME is a string
            new_row['ACTIVITY'] = df.at[df.index[index], columns_dict[empID]['Activité']]
            new_row['REF'] = ref
            new_row['CLIENT'] = df.at[df.index[index], columns_dict[empID]['Client']]
            new_row['DATE_DEBUT'] = df.at[df.index[date_index], columns_dict['Date']['Date']]
            new_row['DATE_FIN'] = df.at[df.index[date_index], columns_dict['Date']['Date']]

            # Add the new row to the DataFrame (use .loc instead of concat)
            data.loc[len(data)] = new_row
            data.loc[len(data) - 1, month_col] = ref_share
        # If the REF exists, update the existing row
        else:
            if data.loc[index_to_update, 'DATE_FIN'] < df.at[df.index[date_index], columns_dict['Date']['Date']]:
                data.loc[index_to_update, 'DATE_FIN'] = df.at[df.index[date_index], columns_dict['Date']['Date']]
            elif data.loc[index_to_update, 'DATE_DEBUT'] > df.at[df.index[date_index], columns_dict['Date']['Date']]:
                data.loc[index_to_update, 'DATE_DEBUT'] = df.at[df.index[date_index], columns_dict['Date']['Date']]
            # Add ref_share to the month column
            data.loc[index_to_update, month_col] = (
                data.at[data.index[index_to_update], month_col] + ref_share
                if pd.notna(data.at[data.index[index_to_update], month_col]) else ref_share
            )
    return data

def format_output_dataframe(data, format_date_v2):
    """Convert columns to the specified format."""
    # Convert date columns to the specified format
    for col in ['DATE_DEBUT', 'DATE_FIN']:
        if col in data.columns:
            data[col] = data[col].dt.strftime(format_date_v2)
    return data

def sort_and_save_output(data, output_file):
    """Sort the DataFrame and save it to a CSV file."""
    # If the output file does not exist, create it (empty file with headers)
    if not os.path.isfile(output_file):
        # Save only headers if file doesn't exist
        data.iloc[0:0].to_csv(output_file, index=False, encoding='utf-8-sig')
    # Save the actual data
    data.to_csv(output_file, index=False, encoding='utf-8-sig')
    return data

def create_rotated_table(json_file_path, schema_file_path, output_file):
    """Main function to execute the workflow."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            params = json.load(f)

        # Check if file paths are strings
        if "chemin planning" in params and not isinstance(params["chemin planning"], str):
            raise TypeError("'input_file' must be a string")

        # Check if input file exists
        if "chemin planning" in params:
            if not os.path.isfile(params["chemin planning"]):
                raise FileNotFoundError(f"Input file '{params['input_file']}' does not exist")

        # Check if worksheet exists in the Excel workbook
        if "chemin planning" in params and "nom feuille planning" in params:
            try:
                sheets = pd.ExcelFile(params["chemin planning"], engine="calamine").sheet_names
                if params["nom feuille planning"] not in sheets:
                    raise ValueError(f"Worksheet '{params['sheet_name']}' does not exist in '{params['input_file']}'")
            except Exception as e:
                raise ValueError(f"Could not read Excel file or sheets: {e}")

        # Type and format checks for present fields
        if "date debut" in params:
            try:
                pd.to_datetime(params["date debut"])
            except Exception:
                raise ValueError("Invalid format for 'date debut'")
        if "date fin" in params:
            try:
                pd.to_datetime(params["date fin"])
            except Exception:
                raise ValueError("Invalid format for 'date fin'")
        if "format des dates V2" in params:
            try:
                pd.Timestamp.now().strftime(params["format des dates V2"])
            except Exception:
                raise ValueError("Invalid format for 'format des dates V2'")
        if "nb colonnes a ignore planning" in params:
            if not isinstance(params["nb colonnes a ignore planning"], int):
                if isinstance(params["nb colonnes a ignore planning"], str) and params["nb colonnes a ignore planning"].isdigit():
                    params["nb colonnes a ignore planning"] = int(params["nb colonnes a ignore planning"])
                else:
                    raise TypeError("'nb colonnes a ignore planning' must be int")

    except Exception as e:
        raise e

    FILE_PATH = params.get("chemin planning")
    SHEET_NAME = params.get("nom feuille planning")
    OUTPUT_FILE = output_file
    START_DATE = params.get("date debut")
    END_DATE = params.get("date fin")
    NUM_COLUMNS_TO_REMOVE = params.get("nb colonnes a ignore planning")
    OUTPUT_DATE_FORMAT = params.get("format date v2")
    REFS_DELIM = params.get("delimiteur de refs")
    REFS_AND_CHARA_DELIM = params.get("delimiteur entre refs et caract")

    # Load and clean data
    df = load_and_clean_data(FILE_PATH, SHEET_NAME, NUM_COLUMNS_TO_REMOVE)

    # Create columns dictionary
    columns_dict = create_columns_dict(df)
    
    # Filter by date range
    df = filter_by_date_range(df, columns_dict, START_DATE, END_DATE)

    # Create output headers
    data_headers = create_output_headers(df)
    
    # Populate output DataFrame
    data = populate_output_dataframe(df, columns_dict, data_headers, REFS_DELIM, REFS_AND_CHARA_DELIM)

    # Convert date columns to the specified format
    data = format_output_dataframe(data, OUTPUT_DATE_FORMAT)

    # Sort and save DataFrame
    data = sort_and_save_output(data, OUTPUT_FILE)
    return data

def main():
    json_file_path = os.path.abspath("utilities\\config.json")
    schema_file_path = os.path.abspath("utilities\\schema.json")
    output_file = os.path.abspath("utilities\\temp.csv")
    create_rotated_table(json_file_path, schema_file_path, output_file)

if __name__ == "__main__":
    main()
