# API de Recommandations

## Endpoint de Recommandations

### GET `/api/v1/recommendations/{user_id}`

Retourne les films recommandés pour un utilisateur donné.

#### Paramètres

- `user_id` (path, requis): ID de l'utilisateur (entier)
- `limit` (query, optionnel): Nombre maximum de recommandations à retourner (défaut: 10, max: 100)

#### Exemple de requête

```bash
# Obtenir 10 recommandations pour l'utilisateur 1
curl http://localhost:8000/api/v1/recommendations/1

# Obtenir 20 recommandations pour l'utilisateur 1
curl http://localhost:8000/api/v1/recommendations/1?limit=20
```

#### Exemple de réponse

```json
{
  "user_id": 1,
  "count": 10,
  "recommendations": [
    {
      "movie_id": 116155,
      "score": 5.188101768493652,
      "rank": 1,
      "title": "Toy Story (1995)",
      "release_year": 1995,
      "genres": ["Adventure", "Animation", "Children", "Comedy", "Fantasy"]
    },
    {
      "movie_id": 81117,
      "score": 5.071373462677002,
      "rank": 2,
      "title": "Jumanji (1995)",
      "release_year": 1995,
      "genres": ["Adventure", "Children", "Fantasy"]
    }
  ]
}
```

#### Codes de réponse

- `200 OK`: Recommandations trouvées et retournées avec succès
- `404 Not Found`: Aucune recommandation trouvée pour cet utilisateur
- `500 Internal Server Error`: Erreur lors du chargement des données
- `503 Service Unavailable`: Le service de recommandations n'est pas disponible (données non chargées)

## Fonctionnalités

### Cache Redis

Les recommandations sont mises en cache dans Redis avec un TTL de 1 heure pour améliorer les performances. Si Redis n'est pas disponible, le cache est ignoré et les données sont chargées directement depuis le lakehouse.

### Enrichissement des données

Chaque recommandation inclut automatiquement:
- `movie_id`: ID du film
- `score`: Score de recommandation (prédiction ALS)
- `rank`: Rang de la recommandation (1 = meilleure recommandation)
- `title`: Titre du film
- `release_year`: Année de sortie (si disponible)
- `genres`: Liste des genres du film

## Configuration

L'API utilise les variables d'environnement suivantes:

- `LAKEHOUSE_PATH`: Chemin vers le répertoire lakehouse (défaut: `/lakehouse`)
- `REDIS_HOST`: Hôte Redis (défaut: `redis`)
- `REDIS_PORT`: Port Redis (défaut: `6379`)

## Structure des données

### Recommandations (Gold Layer)

Les recommandations sont stockées dans `/lakehouse/gold/recommendations_als/` au format Parquet avec la structure suivante:

- `user_id`: ID de l'utilisateur
- `recommendations`: Tableau de recommandations (chaque élément contient `movie_id`, `score`, `rank`)
- `model_version`: Version du modèle utilisé
- `generated_ts`: Timestamp de génération

### Films (Silver Layer)

Les informations sur les films sont stockées dans `/lakehouse/silver/movies/` au format Parquet avec:

- `movie_id`: ID du film
- `title`: Titre du film
- `release_year`: Année de sortie
- `genres`: Tableau des genres

## Notes techniques

- Le service charge les données depuis les fichiers Parquet/Delta du lakehouse
- Les données sont mises en cache en mémoire pour améliorer les performances
- Le cache peut être vidé en redémarrant le service
- Les recommandations sont triées par score décroissant (meilleures recommandations en premier)


