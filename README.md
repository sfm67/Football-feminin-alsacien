# Foot féminin en Alsace
1. Crée un dépôt GitHub public, dépose ces fichiers.
2. Settings > Pages > Source : "Deploy from a branch", branche main, dossier /(root).
3. Onglet Actions > "Mise à jour des données" > Run workflow (puis tous les jours automatiquement).
4. Si une compétition sort vide : lance en local `DEBUG=1 python scrape.py`, regarde debug/*.html et envoie-les moi pour ajuster.
5. Le régional (R1/R2 Féminine, U18 Régional…) est détecté automatiquement via la page Grand EST ; seules les poules comptant un club alsacien sont gardées.
