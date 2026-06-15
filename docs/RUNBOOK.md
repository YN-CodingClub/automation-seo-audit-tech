# Runbook, SEO Audit Automator

## Déploiement live

| Élément | Valeur |
|---|---|
| Live URL | https://automation-seo-audit-tech.streamlit.app/ |
| Repository principal | `Heart-Quake/automation-seo-audit-tech` |
| Miroir | `YN-CodingClub/automation-seo-audit-tech` |
| Branche | `main` |
| Entrypoint | `streamlit_app.py` |
| Dernier build marker vérifié | `automation-seo-audit-tech:0388781` |

## Commandes locales

```bash
cd /Users/vincentflaceliere/Github/automation-seo-audit-tech
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

Vérification minimale :

```bash
python3 -m py_compile streamlit_app.py audit_engine.py automation_seo_theme.py
python3 -m pytest
```

## Smoke test live

Dans l'iframe Streamlit `streamlitApp`, vérifier :

- `.tool-hero` count = 1 ;
- `.sidebar-logo img` count = 1 ;
- `[data-app-build]` count = 1 ;
- `--yn-bg` présent ;
- ancien branding absent ;
- uploader CSV visible ;
- pas de traceback.

## Dépannage

### Colonne URL introuvable

Cause probable :

- export non Screaming Frog ;
- colonne URL renommée hors alias ;
- mauvaise ligne d'en-tête.

Action :

- vérifier que le CSV contient `Adresse`, `Address`, `URL` ou `Url` ;
- vérifier la ligne d'en-tête ;
- ajouter un alias dans `COLUMN_ALIASES` si le format est récurrent.

### Beaucoup de scénarios non évaluables

Cause probable :

- export trop minimal ;
- colonnes title/meta/canonical/inlinks absentes ;
- exports GSC ou URL Inspection non joints.

Action :

- relancer Screaming Frog avec les colonnes nécessaires ;
- expliquer que `not_evaluable` n'est pas équivalent à `ok`.

### PPTX vide

Cause probable :

- aucun scénario en statut `detected` ;
- l'utilisateur n'a pas cliqué sur `Générer l'Audit`.

Action :

- vérifier le tableau de synthèse ;
- vérifier le scope ;
- inclure plus de colonnes dans l'export.

### Build Streamlit échoué

Action :

```bash
python3 -m py_compile streamlit_app.py audit_engine.py automation_seo_theme.py
python3 -m pytest
```

Puis vérifier :

- `requirements.txt` ;
- logs Streamlit Cloud ;
- présence de `logo-sidebar-cream.png` ;
- absence de fichiers clients lourds.

## Fichiers à ne pas commiter

- exports Screaming Frog clients ;
- PPTX clients ;
- captures d'audit contenant des URLs client ;
- caches Python ou Streamlit ;
- `.DS_Store`.

## Règles UI

- Ne pas utiliser de composants HTML custom pour une interaction disponible en natif Streamlit.
- Conserver le hero `.tool-hero`.
- Conserver le build marker caché.
- Ne pas afficher d'informations techniques non nécessaires à l'utilisateur final.
