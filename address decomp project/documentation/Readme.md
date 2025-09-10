# SBS-intern-AI-adress-treatment

## Description des fichiers

### Fichiers de configuration
- `keys.json` : Stocke les clés API pour accéder aux services OpenAI et Mistral.
- `common_words.json` : Contient des listes catégorisées de mots courants dans les adresses :
  - "Numéro et nom de la voie" (rue, avenue, boulevard...)
  - "Immeuble/bâtiment/résidence" (immeuble, batiment, tour...)
  - "Appartement/étage/escalier" (étage, appartement...)
  - "Mention spéciale/lieu-dit" (c/o, hameau, lieu-dit...)

### Scripts principaux

#### `address_decomp.py`
Script principal pour la décomposition d'adresses :
- Ouvre et traite des fichiers d'adresses Excel/CSV
- Construit des prompts via des templates Jinja2
- Envoie les requêtes par lots à l'API Mistral
- Calcule la précision des résultats en utilisant la correction et génère des logs
- **Dépendances** : batch_mistral_api.py, common_words.json, keys.json

#### `batch_mistral_api.py`
Gère le traitement par lots avec l'API Mistral :
- Crée et gère des jobs batch pour traiter de grandes quantités de prompts
- Gère le téléchargement/upload de fichiers, la création de jobs et la récupération des résultats
- Extrait le contenu des réponses API
- Fonction principale : `send_batch_prompts()`

#### `fine_tuner_output.py`
Prépare les données pour le fine-tuning du modèle :
- Traite les données d'adresses depuis des fichiers Excel
- Crée des exemples d'entraînement avec prompts et réponses attendues
- Génère un fichier JSONL pour le fine-tuning
- **Dépendances** : address_decomp.py (utilise `build_all_prompts()`)

#### `word_verif.py`
Analyse et vérifie les mots dans les données d'adresses :
- Extrait des colonnes depuis des fichiers Excel/CSV
- Vérifie la présence de mots-clés dans des colonnes spécifiques
- Compare des ensembles de mots entre colonnes
- Calcule des statistiques sur la présence et le placement des mots-clés
- Utilisé pour verifier un fichier de réponses sans la corréction

### Autre fichiers

#### `Adresses_test_correction.xlsx`
- Fichier Excel contenant 1360 adresses avec leur correction
- C'est le fichier utiliser dans address_decomp.py pour extraire, corriger et ajouter le contexte dans les prompts

#### `ministral-400-answers.csv`
- Fichier csv contenant 100 adresses traitées par "ft:ministral-8b-latest:5d5f2efb:20250902:79156560"

#### `prompt_7.j2`
Le prompt utilisé avec un excellent rendement qualité prix:
- Ce prompt a besoin d'être injecter avec le pays, l'adresse et le context (les mots clés de l'adresse)

#### `reformat_data.py`
Corrige le format des fichiers utiliser pour fine-tune un modèle
- Tout fichier qui est utiliser pour l'entrainement fine-tune d'un modèle doit passer par cette étape
- usage: >python reformat_data.py dataset.jsonl 
- Ne pas formatter les prompt normaux lors de l'utilisation d'un modèle, uniquement les fichiers destiner au fine-tuning

#### `training-300.jsonl`
Dans le fichier training-400, utilisé pour entrainer le modèle ministral au dessus.

#### `validation-100.jsonl`
Dans le fichier training-400, utilisé comme fichier de validation pour entrainer le modèle ministral au dessus
- Les fichiers training-300.jsonl et validation-100.jsonl ne continennent pas d'adresses en communs.

#### `batch_log.txt`
Fichier de log utiliser pour sauvegarder les details de chaque job effectuer par address_decomp.py

Le projet forme un système complet pour décomposer des adresses en composants standardisés (rue, bâtiment, appartement, mention spéciale) en utilisant des modèles d'IA, avec des outils pour le traitement par lots, le fine-tuning et la vérification des résultats.