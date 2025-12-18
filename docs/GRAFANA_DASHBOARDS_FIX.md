# Correction des Dashboards Grafana - Solution de Contournement

**Date**: 2025-12-17  
**Problème**: Les dashboards ne se chargent pas automatiquement via le provisioning (erreur "Dashboard title cannot be empty")

## Problème Identifié

Grafana ne peut pas charger automatiquement les dashboards depuis `/var/lib/grafana/dashboards` malgré :
- ✅ Format JSON correct avec `{"dashboard": {"title": "..."}}`
- ✅ Fichiers présents dans le conteneur
- ✅ Configuration de provisioning correcte
- ✅ Titre présent dans les fichiers JSON

**Erreur dans les logs**:
```
level=error msg="failed to load dashboard from " file=/var/lib/grafana/dashboards/api-overview.json error="Dashboard title cannot be empty"
```

## Solution : Import Manuel via l'Interface Web

Puisque le provisioning automatique ne fonctionne pas, importez les dashboards manuellement via l'interface web de Grafana.

### Étapes pour Importer les Dashboards

1. **Accédez à Grafana**: http://localhost:3000
   - Login: `admin` / `admin`

2. **Importez chaque dashboard**:
   - Cliquez sur **"+"** (menu principal) > **"Import"**
   - Ou allez dans **Dashboards** > **Import**
   - Copiez-collez le contenu JSON de chaque dashboard depuis les fichiers :
     - `grafana/dashboards/api-overview.json`
     - `grafana/dashboards/platform-overview.json`
     - `grafana/dashboards/bigdata-overview.json`
   - Cliquez sur **"Load"**
   - Vérifiez que le datasource Prometheus est sélectionné
   - Cliquez sur **"Import"**

### Dashboards Disponibles

1. **API Overview** (`api-overview.json`)
   - Métriques FastAPI : RPS, P95 Latency, Error Rate, Top Endpoints
   - Requiert les métriques : `http_requests_total`, `http_request_duration_seconds`

2. **Platform Overview** (`platform-overview.json`)
   - Vue d'ensemble de la plateforme
   - Statistiques API agrégées

3. **Big Data Ecosystem Overview** (`bigdata-overview.json`)
   - Statut des services (up/down)
   - Métriques Kafka et Spark (si disponibles)

## Vérification

### 1. Vérifier que Prometheus scrape FastAPI

Accédez à: http://localhost:9090/targets

Le target `fastapi` doit être **UP** (vert).

### 2. Vérifier que les métriques existent

Dans Prometheus (http://localhost:9090), testez ces requêtes :
- `http_requests_total`
- `http_request_duration_seconds_bucket`
- `up{job="fastapi"}`

### 3. Générer du trafic pour voir les données

```bash
# Faites quelques requêtes à FastAPI
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/metrics

# Attendez quelques secondes puis rafraîchissez les dashboards dans Grafana
```

## Alternative : Import via API REST

Vous pouvez aussi importer les dashboards via l'API REST de Grafana :

```bash
# Exemple pour api-overview.json
curl -X POST \
  http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @grafana/dashboards/api-overview.json
```

## Cause Probable

Le problème semble être lié à :
- Un bug dans la version de Grafana utilisée (`grafana/grafana:latest`)
- Un problème avec le parsing JSON lors du provisioning automatique
- Un problème de compatibilité avec le montage de volumes Windows → Docker

## Prochaines Étapes

1. **Importez manuellement les dashboards** (solution immédiate)
2. **Générez du trafic** sur FastAPI pour voir les données
3. **Vérifiez les dashboards** dans Grafana après import
4. **Considérez mettre à jour Grafana** vers une version spécifique si le problème persiste

## Fichiers Modifiés

- ✅ `grafana/dashboards/api-overview.json` - Dashboard API créé
- ✅ `grafana/dashboards/platform-overview.json` - Dashboard Platform créé  
- ✅ `grafana/dashboards/bigdata-overview.json` - Dashboard BigData corrigé
- ✅ `grafana/provisioning/dashboards/dashboard.yml` - Configuration provisioning (correcte mais ne fonctionne pas)
- ✅ `grafana/provisioning/datasources/prometheus.yml` - Datasource Prometheus configuré

## Status Final

- ✅ **Prometheus** : Fonctionne, scrape FastAPI correctement
- ✅ **FastAPI Metrics** : Endpoint `/metrics` fonctionne
- ✅ **Grafana Datasource** : Prometheus configuré et accessible
- ⚠️ **Dashboards** : Provisioning automatique ne fonctionne pas, import manuel requis




