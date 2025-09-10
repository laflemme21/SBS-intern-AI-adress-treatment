import os
import pandas as pd
from io import StringIO
import json


def load_data(file_path: str, header: int, sheet: str|int = 0) -> pd.DataFrame:
    """Load data from a file into a DataFrame. 

    Args:
        file_path (str): Path to the data file.
        header (int): Row number(s) to use as the column names, and the start of the data.
        sheet (str or int, optional): The sheet name or index to read from (default is 0)."""

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} cannot be found.")
    # extract the file extension
    file_extension = os.path.splitext(file_path)[1]
    if file_extension == '.xlsx':
        data = pd.read_excel(file_path,sheet_name=sheet, header=header, engine='calamine')
    elif file_extension == '.csv':
        data = pd.read_csv(file_path, header=header)

    # if the headers are multi-index, delete the parent headers
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.map(lambda x: x[-1], na_action='ignore')
    return data

def save_data(data: pd.DataFrame, file_path: str, delimiter: str = ',') -> bool:
    """Save a DataFrame to a file.

    Args:
        data (pd.DataFrame): The DataFrame to save.
        file_path (str): Path to the file where the DataFrame will be saved.
        delimiter (str): Delimiter to use in the output file.
    """

    try:
        data.to_csv(file_path, index=False, sep=delimiter, encoding='utf-8-sig')  # UTF-8 with BOM
        return True
    except Exception as e:
        print(f"Error saving data to {file_path}: {e}")
        return False

def populate_engagement(df):
    for activite in range(len(df['ACTIVITY'])):
        if df['ACTIVITY'][activite] == 'ESC' or df['ACTIVITY'][activite] == 'MCO' or df['ACTIVITY'][activite] == 'REPORT ESC' or df['ACTIVITY'][activite] == 'ABSEN' or ('pilotage' in str(df['ACTIVITY'][activite]).lower()):
            df.loc[activite, 'ENGAGEMENT'] = 'CONFIRME'
        else:
            df.loc[activite, 'ENGAGEMENT'] = 'PREVISIONEL'
    return df

def populate_output_df(
    output_df: pd.DataFrame,
    colonne_sortie_recherche: str,      # e.g. 'REF'
    column_destinations: list,
    data: pd.DataFrame,
    colonne_source_recherche: str,        # e.g. 'Change ES -  EV'
    data_column_sources: list
) -> pd.DataFrame:
    """
    Populate the output DataFrame with data from the data DataFrame,
    matching rows where colonne_sortie_recherche matches colonne_source_recherche.
    If multiple rows in output_df match, populate all of them.
    """
    for _, data_row in data.iterrows():
        search_value = data_row[colonne_source_recherche]
        # Find all matching rows in output_df
        mask = output_df[colonne_sortie_recherche] == search_value
        if mask.any():
            for column_destination, data_column_source in zip(column_destinations, data_column_sources):
                output_df.loc[mask, column_destination] = data_row[data_column_source]

    return output_df

def initialize_output_df(data: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Initialize the output DataFrame with the desired structure."""
    df = pd.DataFrame(columns=columns)
    df['USERNAME'] = data.iloc[:, 0]  # Assuming the first column is the reference column
    df['ACTIVITY'] = data.iloc[:, 1]  # Assuming the second column is the activity column
    df['REF'] = data.iloc[:, 2]  # Assuming the third column is the reference column
    df['CLIENT'] = data.iloc[:, 3]  # Assuming the fourth column is the client column
    for col in data.columns[4:]:
        df[col] = data.iloc[:, data.columns.get_loc(col)]
    return df

def clean_csv_df(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    for col in df2.select_dtypes(include="object").columns:
        df2[col] = df2[col].map(lambda v: v.replace('\n', ' ').replace('\r', ' ') if isinstance(v, str) else v)
    return df2

def format_date_columns(df: pd.DataFrame, date_format: str) -> pd.DataFrame:
    """
    Finds columns containing dates (by checking the first row) and sets all dates in those columns to the given format.
    Only cells that are actual dates are formatted; ints and floats are ignored.
    Non-date cells remain unchanged.
    """
    df_copy = df.copy()
    # Apply date formatting to the entire columns that contain the word date
    date_col_indices = [i for i in df_copy.columns if 'date' in i.lower()]

    # Apply formatting only to valid date cells in those columns
    def format_cell(val):
        try:
            date = pd.to_datetime(val, dayfirst=True, errors='raise').strftime(date_format)
            return date
        except Exception:
            return val  # Leave as is if not a date

    for col in date_col_indices:
        df_copy[col] = df_copy[col].apply(format_cell)

    return df_copy

def activite_pilotage_traitement(df, tous_clients, index_premiere_col_mois):
    """
    Pour chaque ligne où 'ACTIVITY' contient 'pilotage' (insensible à la casse)
    et 'REF' contient '__pilotage__', répartit les sommes mensuelles sur tous les clients donnés.
    Les sommes sont divisées équitablement (division entière, le reste va au premier client).
    Les lignes originales sont remplacées par une ligne pour chaque client.
    index_premiere_col_mois : index (int) de la première colonne de mois dans df
    """
    rows_to_add = []
    rows_to_drop = []

    # Colonnes de mois à partir de l'index donné
    mois_cols = list(df.columns[index_premiere_col_mois:])

    for idx, row in df.iterrows():
        activity = str(row.get('ACTIVITY', '')).lower()
        ref = str(row.get('REF', '')).lower()
        if 'pilotage' in activity and '__pilotage__' in ref:
            # Répartir les valeurs mensuelles
            mois_vals = [row[col] if pd.notnull(row[col]) else 0 for col in mois_cols]
            for i, client in enumerate(tous_clients):
                new_row = row.copy()
                new_row['Projet GPS'] = client
                new_row['CLIENT'] = "Tous clients"
                # Répartition équitable
                repartition = []
                for val in mois_vals:
                    val = float(val)
                    base = val // len(tous_clients)
                    reste = val % len(tous_clients)
                    if i == 0:
                        repartition.append(base + reste)
                    else:
                        repartition.append(base)
                for col, val in zip(mois_cols, repartition):
                    new_row[col] = val
                rows_to_add.append(new_row)
            rows_to_drop.append(idx)

    # Supprimer les lignes originales
    df = df.drop(rows_to_drop, inplace=False)
    # Ajouter les nouvelles lignes
    if rows_to_add:
        df = pd.concat([df, pd.DataFrame(rows_to_add)], ignore_index=True)

    return df

# Example usage before loading the
def create_V2(json_file_path, schema_file_path, rotator_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        params = json.load(f)
    REFERENCE_DF_PATH = params["chemin fichier suivi"]
    REFERENCE_SHEET = params["nom feuille suivi"]
    CC_ROTATED_PLAN_DF_PATH = rotator_file_path
    OUTPUT_DF_PATH = params["chemin fichier sortie"]
    OUTPUT_COLUMNS = params["noms colonnes sortie"]
    NUMBER_HEADERS_INPUT = params["nb rangees a ignore fichier suivi"]
    DATA_COL_TO_SEARCH = params["colonne source recherche"]
    OUTPUT_COL_TO_SEARCH = params["colonne sortie recherche"]
    EXPORT_FROM_DATA = params["colonnes a exporter"]
    IMPORT_TO_OUTPUT = params["colonnes a importer"]
    OUTPUT_DATE_FORMAT = params["format date v2"]
    SORT_BY = params["trier sortie par"]
    OUTPUT_FILE_DELIMITER = params["delimiteur fichier sortie"]
    PILOTAGE_TOUS_CLIENTS = params["liste projet GPS pilotage"]

    # Check that path variables are valid
    for path_var, path_value in [
        ("chemin fichier suivi", REFERENCE_DF_PATH),
        ("rotated_plan_file_path", CC_ROTATED_PLAN_DF_PATH),
        ("chemin fichier sortie", OUTPUT_DF_PATH)
    ]:
        if not isinstance(path_value, str) or not path_value:
            raise ValueError(f"Parameter '{path_var}' must be a non-empty string.")
        # Only check existence for input files
        if path_var != "chemin fichier sortie" and not os.path.exists(path_value):
            raise FileNotFoundError(f"File '{path_value}' specified in '{path_var}' does not exist.")

    # Check that all elements of sort_by, import_to_output, and colonne sortie recherche exist in output_columns
    missing = []
    for col in SORT_BY:
        if col not in OUTPUT_COLUMNS:
            missing.append(col)
    for col in IMPORT_TO_OUTPUT:
        if col not in OUTPUT_COLUMNS:
            missing.append(col)
    # colonne sortie recherche can be str or list
    if isinstance(OUTPUT_COL_TO_SEARCH, list):
        for col in OUTPUT_COL_TO_SEARCH:
            if col not in OUTPUT_COLUMNS:
                missing.append(col)
    else:
        if OUTPUT_COL_TO_SEARCH not in OUTPUT_COLUMNS:
            missing.append(OUTPUT_COL_TO_SEARCH)
    if missing:
        raise ValueError(f"The following columns are missing from output_columns: {missing}")

    cc_rotated_plan_df = load_data(CC_ROTATED_PLAN_DF_PATH, 0)
    output_df = initialize_output_df(cc_rotated_plan_df, OUTPUT_COLUMNS)
    reference_df = load_data(REFERENCE_DF_PATH, NUMBER_HEADERS_INPUT, REFERENCE_SHEET)
    output_df = populate_engagement(output_df)
    output_df = populate_output_df(output_df=output_df, colonne_sortie_recherche=OUTPUT_COL_TO_SEARCH, column_destinations=IMPORT_TO_OUTPUT, data=reference_df, colonne_source_recherche=DATA_COL_TO_SEARCH, data_column_sources=EXPORT_FROM_DATA)
    output_df=activite_pilotage_traitement(output_df, PILOTAGE_TOUS_CLIENTS, index_premiere_col_mois=len(OUTPUT_COLUMNS)+2)
    output_df = clean_csv_df(output_df)
    output_df = format_date_columns(output_df, OUTPUT_DATE_FORMAT)
    output_df = output_df.sort_values(by=SORT_BY, ascending=True)

    save_data(output_df, OUTPUT_DF_PATH, OUTPUT_FILE_DELIMITER)

def main():
    json_file_path = os.path.abspath("utilities\\config.json")
    schema_file_path = os.path.abspath("utilities\\schema.json")
    rotator_file_path = os.path.abspath("utilities\\temp.csv")
    create_V2(json_file_path, schema_file_path, rotator_file_path)

if __name__ == "__main__":
    main()
