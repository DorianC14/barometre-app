# Baromètre 2026 · Santé financière mondiale

Projet KEDGE BS, Gestion d'actifs 2025-2026. L'application calcule un **score de tension financière**
de 0 (euphorie) à 100 (stress), pour le **Monde** et pour l'**Europe / France**. Le score agrège
22 indicateurs répartis en 5 piliers et s'actualise automatiquement.

## Ce que contient le dépôt

```
pipeline/                 Collecte et calcul (Python)
  sources.py              Connecteurs : FRED, BCE, Eurostat, INSEE, OCDE, STOXX, Twelve Data, Yahoo, multpl, GPR, EPU
  config.py               Méthodologie chiffrée : séries, 22 indicateurs, piliers, poids, zones, allocation
  transforms.py           Variation sur 1 an, écart à la moyenne 200 jours, credit impulse…
  scoring.py              Normalisation (z-score 10 ans → 0-100), pondération, contributions,
                          variantes (poids égaux, ACP), régime All Weather, conseils, test historique
  news.py, lexicon.py     Revue de presse (RSS) et sentiment par dictionnaire
  run.py                  Point d'entrée : --mode markets | full | news
  tests/                  Tests de la logique de calcul
web/                      Application Next.js (7 pages), export statique pour Vercel
docs/                     Note d'explication (2 pages, HTML et PDF)
.github/workflows/        Actualisation automatique (GitHub Actions)
```

## Comment l'actualisation fonctionne

1. **GitHub Actions** lance `pipeline/run.py` automatiquement :
   - toutes les 15 minutes : cours de marché (indices, VIX, Brent, EUR/USD, or, taux 10 ans US) ;
   - chaque jour vers 5 h-6 h (Paris) : toutes les séries (macro, taux, crédit, géopolitique) ;
   - vers 7 h et 18 h : revue de presse et sentiment.
2. Les résultats (JSON) sont publiés sur la branche **`data`** du dépôt. Cette branche ne garde
   qu'un seul commit, pour rester légère.
3. Le site sur **Vercel** lit ces fichiers et se recharge seul toutes les 2 minutes. Il n'a pas
   besoin d'être redéployé à chaque mise à jour des données.

Si une source ne répond pas, la dernière valeur connue est gardée et signalée « en retard ».

## Mise en ligne (à faire une fois)

1. Créer un dépôt GitHub **public** et y pousser ce dossier. Un dépôt public donne des minutes
   GitHub Actions illimitées. Avec un dépôt privé, passer le cron des marchés à `*/30`.
2. Créer une clé gratuite sur **twelvedata.com**, puis dans le dépôt : *Settings → Secrets and variables →
   Actions → New repository secret*, nom `TWELVEDATA_API_KEY`. Sans clé, les cours passent par Yahoo
   (souvent bloqué pour les robots) puis par FRED et STOXX, avec un jour de décalage.
3. Onglet **Actions** → « Actualisation des données » → **Run workflow** (mode `full`).
   Au bout de 5 à 10 minutes, la branche `data` apparaît.
4. Sur **Vercel** : *Add New Project* → importer le dépôt → **Root Directory : `web`**.
   Ajouter la variable d'environnement :
   `NEXT_PUBLIC_DATA_URL = https://raw.githubusercontent.com/<compte>/<dépôt>/data`
5. Déployer. Le site est en ligne et suit les données automatiquement.

GitHub peut suspendre les tâches programmées d'un dépôt public après 60 jours sans activité.
Dans ce cas, il suffit de les réactiver dans l'onglet Actions.

## Lancer en local

```bash
pip install -r pipeline/requirements.txt
export TWELVEDATA_API_KEY=...   # facultatif
cd pipeline && python run.py --mode full && python run.py --mode news   # écrit ../data/*.json
cd ../web && npm install && mkdir -p public/data && cp ../data/*.json public/data/ && npm run dev
```

Tests : `python -m pytest pipeline/tests`.

## Méthode en bref

- **Normalisation** : z-score glissant sur 10 ans (3 ans minimum), borné à ±3, converti en
  percentile de la loi normale (0-100). Inversion pour les indicateurs de risque. L'inflation est
  notée selon son écart à la cible de 2 % : 100 − 25 × |π − 2|.
- **Pondération** : banques centrales 25 %, risque 20 %, marchés 20 %, macro 20 %, flux et
  sentiment 15 %. Le taux anticipé compte double dans son pilier.
- **Score** = 100 − note favorable pondérée. Zones : 0-20 euphorie, 20-40 favorable,
  40-60 neutre, 60-80 prudence, 80-100 stress.
- **Contribution d'un indicateur** = poids du pilier × poids dans le pilier × (note − 50).
  Score = 50 + somme des contributions.

*Les conseils affichés sont des suppositions issues d'un modèle pédagogique. Ils ne constituent
pas un conseil en investissement personnalisé (directive MIF).*
