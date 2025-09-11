# SBS-intern-AI-adress-treatment

# Sommaire

1. Présentation de l'organisation des fichiers
2. Introduction au fonctionnement de l'outil
3. Présentation de chaque fonction de l'outil ainsi que des paramètres clés
4. Introduction des documents clés

## 1. Présentation de l'organisation des fichiers

Le projet est structuré comme suit :
- **source_code/** : Contient tous les scripts Python et l'interpréteur Python embarqué
- **ressources/** : Contient les fichiers de configuration et les fichiers de stockages comme mots cles, villes valides etc.
- **documentation/** : Documentation du projet et exemples de documents utilisé par l'outil
- **in_out_files/** : Contient tout les fichiers pris comme input et rendus comme output par l'outil. 
- **execute.bat** : Script de lancement pour Windows

## 2. Introduction au fonctionnement de l'outil

Cet outil permet la décomposition automatisée d'adresses en utilisant l'API Mistral AI. 
Il prend en entrée un fichier Excel/CSV contenant des adresses complètes et produit un fichier 
avec ces adresses décomposées en plusieurs composants (rue, immeuble, étage, etc.).
Il peut aussi donner un indice de confiance sur chaque adresse decomposee et verifier la validite d'autre champs comme la ville et le code postale.

### Comment exécuter l'outil
1. Double-cliquez sur `execute.bat` pour lancer l'interface graphique ou le lancer sur cmd
2. Dans la première fenêtre, sélectionnez les fonctionnalités à utiliser
3. Dans la seconde fenêtre, configurez les paramètres nécessaires
4. Cliquez sur "Run" pour exécuter le traitement

L'application sauvegarde automatiquement vos paramètres dans le fichier config.json.

## 3. Présentation des fonctions et paramètres clés

### Page des fonctions (Fonctionnalités)
Cette page permet de choisir les fonctions a executer.

- **use_mistral** : a partir d un fichier contenant des adresses, les envois a mistral en batches et extrait les reponses du fichier rendus. Pour sauvegarder le resultat, save_answers doit etre coche.
- **log_statistics** : Si use mistral est coche, cette fonction va sauvegarder le temps d execution et des donnes sur l execution dans un log file.
- **parse_and_save_batch_ans_file** : Extrait les reponses de Mistral d'un fichiers obtenue apres l execution d un batch su La Plateforme
- **save_answers** : Si use mistral est coche, cette fonction sauvegarde le resultat obtenue
- **build_and_save_prompts** : genere un fichiers contenant des prompts, dans un format que le batch api de Mistral accepte. Ce fichier peut etre soumis au batch api
- **calculate_conf_score** : Calcul un score de confiance pour chaque range et les sauvegarde dans un fichiers
- **check_postal_code** : verifie que le code postal de chaque range existe dans le fichier de toute les adresse postale correspondant au pays de l'adresse
- **check_ville** : verifie que la ville de chaque range existe dans le fichier de toute les villes correspondant au pays de l'adresse

### Paramètres principaux

#### address_decomp_parameters
- **api_key** : Clé API pour Mistral
- **mistral_model** : Modèle Mistral à utiliser
- **input_file** : Fichier contenant les adresses à traiter. doit contenir un colonne qui contient les adresses concat
- **output_file** : Fichier où sauvegarder les résultats
- **concat_column** : Nom de la colonne contenant l'adresse complète dans le input file
- **pays_column** : Nom de la colonne contenant le pays
- **output_columns** : Liste des noms de colonnes à générer dans le fichier de sortie. le noms des colonnes peut etre changer mais celle-ci contiendront toujours and cette ordre concat,rue,immeuble,etaghe,mention
- **prompt_file** : Fichier JinJa2 contanant la template du prompt. Pour chaque range on lui injecte le pays, les mots cles contenue dans l adresse et le champs auquel ils sont affilies et l'adresse a traite

#### ans_grading_parameters
- Paramètres pour évaluer la qualité des décompositions d'adresses
- Poids pour différents critères d'évaluation

#### address_verif_parameters
- Paramètres pour vérifier les composants d'adresse contre des références

## 4. Description des fichiers

### Fichiers de configuration
- `config.json` : Contient tous les paramètres configurables de l'application
- `schema.json` : Définit la structure et les contraintes des paramètres
- `keys.json` : Stocke les clés API pour accéder aux services OpenAI et Mistral.
- `common_words.json` : Contient des listes catégorisées de mots courants dans les adresses :
  - "Numéro et nom de la voie" (rue, avenue, boulevard...)
  - "Immeuble/bâtiment/résidence" (immeuble, batiment, tour...)
  - "Appartement/étage/escalier" (étage, appartement...)
  - "Mention spéciale/lieu-dit" (c/o, hameau, lieu-dit...)

### Interface utilisateur
- `gui.py` : Interface graphique permettant de configurer et lancer l'application
  - Fenêtre de sélection des fonctionnalités
  - Fenêtre de configuration des paramètres avec descriptions contextuelles (infobulles)
  - Boutons pour naviguer, sauvegarder la configuration et exécuter le traitement

### Scripts principaux

#### `backend_main.py`
Script principal qui orchestre l'exécution des différentes fonctionnalités:
- Charge la configuration depuis config.json
- Exécute les fonctions sélectionnées dans l'ordre approprié

#### `address_decomp.py`
Script pour la décomposition d'adresses :
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

#### `grading.py`
Module d'évaluation des décompositions d'adresses :
- Calcule des scores de confiance pour chaque composant
- Vérifie la présence de mots-clés dans les bonnes colonnes
- Analyse la longueur et la structure des composants

#### `address_verif.py`
Module de vérification des composants d'adresse :
- Vérifie les codes postaux et noms de ville contre des fichiers de référence
- Génère un rapport de vérification

### Fichiers de données

#### `Adresses_test_correction.xlsx`
- Fichier Excel contenant 1360 adresses avec leur correction

### Autres Fichiers

#### `prompt_7.j2`
Le prompt utilisé avec un excellent rendement qualité prix:
- Ce prompt a besoin d'être injecté avec le pays, l'adresse et le contexte (les mots clés de l'adresse)

#### `batch_log.txt`
Fichier de log utilisé pour sauvegarder les détails de chaque job effectué par address_decomp.py

Le projet forme un système complet pour décomposer des adresses en composants standardisés (rue, bâtiment, appartement, mention spéciale) en utilisant des modèles d'IA, avec des outils pour le traitement par lots, le fine-tuning et la vérification des résultats.