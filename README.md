# Traducteur Python — hors ligne et Google

Application de bureau en français, inspirée de la disposition de Google Traduction : deux panneaux, choix des langues, inversion et copie. Projet indépendant, non affilié à Google.

## Premier lancement

Python 3.11 ou 3.12 recommandé. Ouvrez un terminal dans ce dossier :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python traducteur.py
```

Sous Windows : utilisez `py -m venv .venv`, puis `.venv\Scripts\python.exe` à la place de `.venv/bin/python`.

Sous Debian/Ubuntu, si Tkinter ou venv manque : `sudo apt install python3-tk python3-venv`.

## Télécharger les langues

1. Ouvrez **Langues hors ligne**.
2. Cliquez sur **Actualiser** (connexion Internet requise).
3. Cliquez sur **Tout installer**, ou sélectionnez les paires utiles.

Les modèles ne sont pas inclus dans cette archive. Le téléchargement complet peut occuper plusieurs Go et durer longtemps ; la taille et la durée dépendent du catalogue et de la connexion. Les fichiers installés restent dans `modeles/`, à côté du script. Une interruption conserve les modèles déjà installés ; relancer ignore les mêmes versions. L'arrêt attend la fin du modèle courant.

Pour télécharger sans interface :

```sh
.venv/bin/python traducteur.py --installer-tout
```

Copiez ensuite le dossier avec ses modèles pour le conserver. Sur une autre machine, installez aussi Python et les dépendances compatibles avant de couper Internet ; copier un environnement `.venv` n'est pas une méthode portable.

**Toutes les langues du monde ne sont pas disponibles hors ligne.** Le bouton installe tous les modèles de traduction du catalogue Argos actuel. Une langue affichée dans le menu ne garantit pas un modèle installé. Les parcours indirects (par exemple via l'anglais) sont gérés par Argos quand les modèles nécessaires existent. La qualité dépend de la paire et du parcours. Le choix de langue source est manuel.

## Google en ligne

Activez Cloud Translation API dans votre projet Google Cloud et créez une clé API autorisée pour cette API. Une facturation peut être nécessaire.

Dans l'application, saisissez la clé dans **Clé Google**, choisissez **Google en ligne**, puis **Langues Google** pour charger les langues prises en charge. Le texte est envoyé à Google uniquement quand vous lancez une traduction dans ce mode. Les requêtes de catalogue contactent aussi Google quand vous cliquez sur Langues Google. Le mode hors ligne ne bascule jamais automatiquement vers Internet.

La clé n'est pas enregistrée par l'application. Vous pouvez aussi fournir la variable d'environnement `GOOGLE_TRANSLATE_API_KEY`. Aucun serveur intermédiaire n'est utilisé. Ne distribuez pas votre clé avec le programme.

## Limites et vérification

Texte uniquement, 5 000 caractères par traduction. Pas de détection automatique, OCR ou audio. Les écritures de droite à gauche dépendent du rendu Tkinter du système.

Vérification effectuée : compilation Python et tests isolés du service Google et de la reprise des installations. Les traductions réelles, le téléchargement des modèles et l'affichage graphique doivent être vérifiés sur votre machine avec les dépendances et, pour Google, votre propre clé.

Sources :
- Argos Translate : https://github.com/argosopentech/argos-translate
- API Google : https://docs.cloud.google.com/translate/docs/basic/translating-text
