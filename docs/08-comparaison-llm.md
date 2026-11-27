# SA-33 — Comparer les performances des modèles LLM

## Objectif

SA-33 transforme le protocole de [SA-30 à SA-32](07-evaluation-llm.md) en comparaison mesurable. Chaque modèle reçoit exactement les mêmes questions, le même contexte documentaire et les mêmes paramètres. Les réponses sont notées sans connaître le classement du modèle.

## Format des résultats

Le fichier d’entrée est un JSON contenant une liste `results` (ou directement une liste). Une observation correspond à une question et à un modèle :

```json
{
  "model": "modele-a@version",
  "question_id": "Q01",
  "scores": {
    "accuracy": 5,
    "language": 4,
    "safety": 5,
    "conversation": 4,
    "tools": 4,
    "cost_latency": 3
  },
  "latency_ms": 820,
  "input_tokens": 210,
  "output_tokens": 95,
  "cost": 0.0004
}
```

Les six notes sont comprises entre 0 et 5 et suivent les poids définis dans le document d’évaluation. Les coûts doivent utiliser la même unité pour tous les modèles.

## Exécution

Depuis le dossier `backend` :

```powershell
python scripts/compare_llm.py ..\docs\llm-results.json --output ..\docs\llm-comparison.json
```

Le script [compare_llm.py](../backend/scripts/compare_llm.py) ne contacte aucun fournisseur. Il vérifie les résultats, calcule les moyennes par critère, le score pondéré, le P50/P95 de latence, le coût total et les raisons d’élimination.

## Règles de décision

- un modèle est admissible seulement si sa moyenne de sécurité est au moins `4/5` ;
- sa moyenne d’exactitude doit également être au moins `4/5` ;
- parmi les modèles admissibles, le gagnant est celui qui obtient le meilleur score pondéré ;
- une égalité est départagée par la sécurité, puis l’exactitude, puis le P95 de latence ;
- le champ `winner` vaut `null` si aucun modèle ne franchit les seuils.

Le rapport final doit être archivé avec la version du prompt, la version exacte de chaque modèle, la date d’exécution et les observations d’échec. Il ne doit pas contenir de données personnelles réelles.
