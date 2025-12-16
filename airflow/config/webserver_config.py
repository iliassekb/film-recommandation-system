# Configuration pour le webserver Airflow
# Ce fichier peut être utilisé pour personnaliser le comportement du webserver

import os
from airflow.configuration import conf

# Configuration de base
SECRET_KEY = os.environ.get('AIRFLOW__WEBSERVER__SECRET_KEY', 'your-secret-key-here')

# Configuration CORS si nécessaire
ENABLE_CORS = True
CORS_ORIGINS = ["*"]

# Configuration de l'authentification
AUTH_ROLE_PUBLIC = 'Viewer'  # ou 'Admin', 'User', 'Op', 'Public', 'Viewer'

# Configuration des sessions
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Configuration du cache
CACHE_TYPE = 'SimpleCache'
CACHE_DEFAULT_TIMEOUT = 300

