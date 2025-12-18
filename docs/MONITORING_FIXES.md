# Corrections Monitoring Prometheus + Grafana

**Date**: 2025-12-17  
**Problème**: Dashboards Grafana vides, endpoint `/metrics` FastAPI retournait 404

## Problèmes Identifiés

1. **FastAPI `/metrics` retournait 404**
   - Cause: Le module `prometheus_client` n'était pas installé dans le conteneur
   - Solution: Reconstruction de l'image FastAPI avec `prometheus-client==0.19.0` dans `requirements.txt`

2. **Dashboards Grafana vides**
   - Cause: Format JSON des dashboards incorrect (propriétés manquantes ou mal structurées)
   - Solution: Correction du format JSON pour correspondre au schéma Grafana v16

3. **Prometheus ne pouvait pas scraper FastAPI**
   - Cause: Endpoint `/metrics` non disponible (404)
   - Solution: Résolu après reconstruction de FastAPI

## Corrections Appliquées

### 1. FastAPI - Installation de prometheus_client

**Fichier modifié**: `api/requirements.txt`
- Ajout de `prometheus_client==0.19.0`

**Fichier modifié**: `api/main.py`
- Ajout du middleware Prometheus pour tracker les requêtes HTTP
- Ajout de l'endpoint `/metrics` pour exposer les métriques

**Action requise**:
```bash
docker-compose build fastapi
docker-compose up -d fastapi
```

### 2. Dashboards Grafana - Format JSON corrigé

**Fichiers modifiés**:
- `grafana/dashboards/api-overview.json`
- `grafana/dashboards/platform-overview.json`

**Corrections**:
- Ajout de la structure `{"dashboard": {...}}` requise par Grafana
- Ajout des propriétés `uid`, `id`, `schemaVersion`
- Correction des `datasource` dans les `targets` pour référencer Prometheus
- Ajout des propriétés `fieldConfig` et `options` complètes pour chaque panel

**Action requise**:
```bash
docker-compose restart grafana
```

### 3. Vérification Prometheus

**Configuration**: `prometheus/prometheus.yml`
- Scrape job `fastapi` configuré pour `fastapi:8000/metrics` ✅
- Métriques disponibles: `http_requests_total`, `http_request_duration_seconds`

## Vérification

### 1. Vérifier que FastAPI expose les métriques

```bash
# Depuis votre machine (Windows)
curl http://localhost:8000/metrics

# Depuis un conteneur
docker-compose exec prometheus wget -qO- http://fastapi:8000/metrics
```

Vous devriez voir des métriques comme:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/metrics",method="GET",status="200"} 1.0
```

### 2. Vérifier que Prometheus scrape FastAPI

Accédez à: http://localhost:9090/targets

Le target `fastapi` doit être en état **UP** (vert).

### 3. Vérifier que Grafana peut accéder à Prometheus

1. Accédez à Grafana: http://localhost:3000
2. Login: `admin` / `admin`
3. Allez dans **Configuration** > **Data Sources**
4. Sélectionnez **Prometheus**
5. Cliquez sur **Test** - doit afficher "Data source is working"

### 4. Vérifier les dashboards

1. Dans Grafana, allez dans **Dashboards**
2. Vous devriez voir:
   - **API Overview** - Métriques FastAPI (RPS, latence, erreurs)
   - **Platform Overview** - Vue d'ensemble de la plateforme
   - **Big Data Ecosystem Overview** - Dashboard existant

3. Ouvrez un dashboard et vérifiez que les panels affichent des données

### 5. Générer des métriques pour tester

Faites quelques requêtes à FastAPI pour générer des métriques:

```bash
# Depuis votre machine
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# Attendez quelques secondes puis rafraîchissez les dashboards Grafana
```

## URLs Importantes

- **Prometheus UI**: http://localhost:9090
- **Grafana UI**: http://localhost:3000 (admin/admin)
- **FastAPI**: http://localhost:8000
- **FastAPI Metrics**: http://localhost:8000/metrics

## Métriques Disponibles

### FastAPI Metrics

- `http_requests_total{method, endpoint, status}` - Nombre total de requêtes HTTP
- `http_request_duration_seconds_bucket{method, endpoint, le}` - Distribution de latence (histogramme)
- Métriques Python standard (GC, mémoire, CPU)

### Prometheus Targets

- `prometheus` (localhost:9090) - UP ✅
- `fastapi` (fastapi:8000) - UP ✅
- Autres targets (kafka, spark, etc.) - DOWN (normal, nécessitent des exporters)

## Prochaines Étapes

1. **Générer du trafic** sur FastAPI pour voir les métriques dans les dashboards
2. **Configurer des alertes** dans Prometheus si nécessaire
3. **Ajouter des exporters** pour Kafka, Spark, etc. si vous voulez monitorer ces services

## Dépannage

### Les dashboards sont toujours vides

1. Vérifiez que Prometheus scrape bien FastAPI: http://localhost:9090/targets
2. Vérifiez que les métriques existent: http://localhost:9090/graph?query=http_requests_total
3. Vérifiez les logs Grafana: `docker-compose logs grafana`
4. Vérifiez que le datasource Prometheus est configuré dans Grafana

### L'endpoint /metrics retourne 404

1. Vérifiez que FastAPI est reconstruit: `docker-compose build fastapi`
2. Vérifiez que le conteneur utilise la nouvelle image: `docker-compose up -d fastapi`
3. Vérifiez les logs: `docker-compose logs fastapi`

### Prometheus ne peut pas scraper FastAPI

1. Vérifiez que les deux services sont sur le même réseau Docker
2. Vérifiez que FastAPI est accessible depuis Prometheus: `docker-compose exec prometheus wget -qO- http://fastapi:8000/metrics`
3. Vérifiez la configuration Prometheus: `prometheus/prometheus.yml`




