# SA-34 — Évaluer le dialecte tunisien et l’Arabizi

SA-34 vérifie que chaque modèle comprend l’intention d’un candidat exprimée en arabe tunisien et en Arabizi, conserve cette intention et répond dans la variante demandée. Les mêmes questions, le même contexte documentaire et les mêmes règles de notation sont utilisés pour chaque modèle.

## Protocole

Le jeu de test doit contenir des questions réelles ou relues par un locuteur tunisien, réparties entre les deux variantes (`tunisian_arabic` et `arabizi`). Pour chaque réponse, un évaluateur note de 0 à 5 :

| Critère | Poids |
| --- | ---: |
| Compréhension | 35 % |
| Conservation de l’intention | 30 % |
| Fidélité à la variante demandée | 20 % |
| Qualité de la réponse | 15 % |

Une réponse doit être évaluée sans révéler le nom du modèle. Les exemples doivent couvrir les fautes d’orthographe, les chiffres Arabizi (`3`, `5`, `7`, `9`), les mots français intégrés et les demandes ambiguës nécessitant une clarification.

## Format et exécution

Chaque observation contient `model`, `question_id`, `variant` et quatre scores de 0 à 5 :

```json
{
  "model": "modele-a@version",
  "question_id": "AR-Q01",
  "variant": "arabizi",
  "scores": {
    "comprehension": 5,
    "intent_preservation": 4,
    "language_fidelity": 4,
    "answer_quality": 4
  }
}
```

Depuis le dossier `backend` :

```powershell
python scripts/evaluate_tunisian.py ..\docs\llm-tunisian-arabizi.json --output ..\docs\llm-tunisian-arabizi-report.json
```

Un modèle n’est admissible que s’il possède des résultats dans les deux variantes et atteint une moyenne pondérée d’au moins `4/5` dans chacune. Le champ `winner` vaut `null` si aucun modèle ne satisfait ces conditions. Le rapport doit conserver la version du modèle, la date, les questions évaluées et les désaccords entre évaluateurs, sans données personnelles.
