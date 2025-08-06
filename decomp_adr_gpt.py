import requests
import pandas as pd
import os
import time  # Ajout pour mesurer le temps

# Remplacez 'votre_clé_api' par votre clé API OpenAI
api_key = '################################ '
api_url = 'https://api.openai.com/v1/chat/completions'  # Endpoint OpenAI

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

# Lire le fichier Excel sans ligne d'en-tête
file_path = 'Adresses_test.xlsx'
temp_file_path = 'temp_test_adresses.xlsx'
df = pd.read_excel(file_path, engine='openpyxl', header=None)

# Fonction pour envoyer une requête à l'API OpenAI
def decompose_address(address,model):
    data = {
        'model': model,  # Utiliser le modèle spécifié
        'messages': [
            {
                'role': 'user',
                'content': (
                    "Décompose l'adresse suivante en 3 champs : "
                    "1/ numéro et nom de la voie (ce champ ne doit pas être vide), "
                    "2/ immeuble, bâtiment, résidence, "
                    "3/ mention spéciale ou lieu-dit. "
                    "Ajoute aussi un quatrième champ : "
                    "4/ un indice de confiance entre 0 et 1 basé sur la clarté et la certitude de ta décomposition. "
                    "La réponse doit être strictement dans la même ligne, séparée par des points-virgules (même si le champ est vide), sans titre ni commentaire.. il faudrait respecter l ordre des champs avec separateur point virgule meme si le champ est vide on respecte l emplacement"
                    "l'indice de confiance est a mettre uniquement dans le 4eme emplacement, il faudrait respecter l'emplacement de chaque champ"
                    "Tous les mots de la l'adresse doivent être utilisés et placés dans les emplacements 1(numéro et nom de la voie), 2(immeuble, batiment résidence) et 3(mention spéciale, lieu-dit)"
                    "Exemple : Pour l'adresse 'Immeuble Les Tulipes 10 Rue de la Paix Le Pré -st germain', la réponse doit être : "
                    "'10 Rue de la Paix; Immeuble Les Tulipes; Le Pré -st germain; 0.95'. "
                    "Autre exemple (avec champs vides et respect des emplacements) : 10 Avenue puvis de chavannes. la réponse doit être : 10 Avenue puvis de chavannes;;;0.93"
                    f"L'adresse à décomposer est : '{address}'"
                )
            }
        ],
        'max_tokens': 250,
        'temperature': 0.3
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()  # Gère les erreurs HTTP

        response_data = response.json()

        if 'choices' in response_data and len(response_data['choices']) > 0:
            content = response_data['choices'][0]['message']['content'].strip()
        else:
            content = "N/A"

        return post_process_response(content)

    except requests.exceptions.RequestException as e:
        print(f"Erreur réseau/API : {e}")
        return "N/A", "N/A", "N/A", 0.0
    except KeyError:
        print("Réponse inattendue de l'API, champs manquants.")
        return "N/A", "N/A", "N/A", 0.0

# Fonction de post-traitement de la réponse
def post_process_response(content):
    fields = content.split(';')

    # Normaliser la sortie en 4 champs
    while len(fields) < 4:
        fields.append("N/A")
    if len(fields) > 4:
        fields = [fields[0], fields[1], fields[2], fields[3]]

    try:
        confidence_score = float(fields[3].strip())  # Convertir l'indice de confiance en float
    except ValueError:
        confidence_score = 0.0  # Valeur par défaut si la conversion échoue

    return fields[0].strip(), fields[1].strip(), fields[2].strip(), confidence_score

start_time = time.time()  # Démarrer le chronomètre

model_used = 'gpt-3.5-turbo'  # Modèle par défaut

# Traiter seulement les n premières lignes de l'Excel
n_rows=10
error_occurred = False

for index, row in df.head(n_rows).iterrows():
    if pd.notna(row.iloc[11]):  # Vérifier si la colonne L (index 11) est renseignée
        address = row.iloc[11]
        try:
            numero_voie, immeuble_residence, mention_speciale, confidence_score = decompose_address(address, model_used)
        except Exception as e:
            error_occurred = True
            print(f"Erreur lors du traitement de la ligne {index}: {e}")
            numero_voie, immeuble_residence, mention_speciale, confidence_score = "N/A", "N/A", "N/A", 0.0

        # Mettre à jour les colonnes M, N, O et P (nouvelle colonne pour l'indice)
        df.at[index, 12] = numero_voie
        df.at[index, 13] = immeuble_residence
        df.at[index, 14] = mention_speciale
        df.at[index, 15] = confidence_score  # Ajout de l'indice de confiance

# Sauvegarder les modifications dans un fichier temporaire sans ligne d'en-tête
df.to_excel(temp_file_path, index=False, header=False, engine='openpyxl')

# Remplacer le fichier original par le fichier temporaire
os.replace(temp_file_path, file_path)

end_time = time.time()  # Arrêter le chronomètre
elapsed_time = end_time - start_time

print(f"Traitement terminé et fichier Excel mis à jour pour les {n_rows} premières lignes.")
print(f"Temps d'exécution : {elapsed_time:.2f} secondes.")

# Écrire dans le log uniquement si aucune erreur n'est survenue
if not error_occurred:
    log_file = "prompt_1_execution_log.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"Rows processed: {n_rows}, Model: {model_used}, Time: {elapsed_time:.2f} seconds\n")
