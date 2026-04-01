# APEX Screener — Cockpit d'Analyse Financière

Outil automatisé d'aide à la décision d'investissement (Actions & Crypto — Spot uniquement).  
Agrégateur de données fondamentales + moteur d'alertes asynchrone en filtrage top-down (entonnoir).

## Architecture

```
┌────────────┐     ┌──────────┐     ┌──────────────────┐
│  React     │────▶│  Nginx   │────▶│  FastAPI          │
│  Dashboard │     │  :80     │     │  Backend :8000    │
└────────────┘     └──────────┘     └──────┬───────────┘
                                           │
                    ┌──────────────────────┼──────────────────┐
                    │                      │                  │
              ┌─────▼─────┐         ┌──────▼──────┐   ┌──────▼──────┐
              │ PostgreSQL │         │ Celery      │   │ Celery      │
              │ TimescaleDB│         │ Worker      │   │ Beat        │
              │ :5432      │         │ (2 workers) │   │ (scheduler) │
              └────────────┘         └──────┬──────┘   └─────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │    Redis     │
                                    │    :6379     │
                                    └──────────────┘
```

## Modules de données

| Module | Source | Fréquence | Données |
|--------|--------|-----------|---------|
| **1. Macroéconomie** | FRED API | Quotidien 18h UTC | DFF, WM2NS, T10Y2Y |
| **2. Radar Sectoriel** | FMP | Quotidien 22h UTC | 11 ETF GICS + MM200 + Force Relative |
| **3a. Screener Actions** | FMP | On-demand | FCF, ROIC, Balance Sheet |
| **3b. Screener Crypto** | DeFiLlama | Toutes les 6h | TVL, FDV, MCap, Fees (top 100) |
| **4. Traqueur Initiés** | SEC EDGAR | Toutes les 30min (heures marché) | Form 4, Code P uniquement |

## Workflow d'alertes

### Actions (Équités)
```
Form 4 (Code P) > 250K$  →  FCF positif 4Q ?  →  ROIC > 10% ?  →  Secteur > MM200 ?  →  🔔 Telegram
                               ✗ Rejet silencieux  ✗ Rejet         ✗ Rejet
```

### Crypto (On-Chain)
```
TVL spike > 20%  →  MCap/FDV > 0.4 ?  →  🔔 Telegram
                     ✗ Rejet silencieux
```

## Déploiement sur VPS

### Prérequis
- VPS avec Docker et Docker Compose installés
- 4 Go RAM minimum (8 Go recommandé)
- Clés API : FRED, FMP, Telegram Bot

### 1. Cloner et configurer

```bash
git clone <repo-url> apex-screener
cd apex-screener

# Copier et remplir le fichier de configuration
cp .env.example .env
nano .env  # Remplir toutes les clés API
```

### 2. Obtenir les clés API

| Service | URL | Tier gratuit |
|---------|-----|--------------|
| **FRED** | https://fred.stlouisfed.org/docs/api/api_key.html | Illimité |
| **FMP** | https://financialmodelingprep.com/developer/docs/ | 250 req/jour |
| **Telegram Bot** | https://t.me/BotFather | Gratuit |
| **DeFiLlama** | Pas de clé requise | Gratuit |
| **SEC EDGAR** | Pas de clé requise (User-Agent requis) | 10 req/sec |

### 3. Lancer les services

```bash
# Build et démarrage
docker compose up -d --build

# Initialiser la base de données
bash scripts/init-db.sh

# Vérifier que tout tourne
docker compose ps
docker compose logs -f backend
```

### 4. Premier chargement de données

```bash
# Déclencher toutes les synchros manuellement
bash scripts/trigger-all.sh

# Suivre l'exécution dans les logs Celery
docker compose logs -f celery-worker
```

### 5. Accéder au dashboard

- **Dashboard React** : `http://<VPS_IP>:80`
- **API FastAPI** : `http://<VPS_IP>:8000/api/health`
- **Swagger docs** : `http://<VPS_IP>:8000/docs`

## API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/health` | GET | Santé du service |
| `/api/status` | GET | État global du système |
| `/api/macro` | GET | Données macroéconomiques |
| `/api/sectors` | GET | Radar sectoriel |
| `/api/stocks/{symbol}` | GET | Fondamentaux d'un ticker |
| `/api/crypto` | GET | Screener crypto DeFi |
| `/api/insiders` | GET | Transactions d'initiés |
| `/api/alerts` | GET | Historique des alertes |
| `/api/trigger/sync-macro` | POST | Synchro macro manuelle |
| `/api/trigger/sync-sectors` | POST | Synchro secteurs manuelle |
| `/api/trigger/sync-crypto` | POST | Synchro crypto manuelle |
| `/api/trigger/scan-insiders` | POST | Scan initiés manuel |
| `/api/trigger/process-equity-alerts` | POST | Traitement alertes actions |
| `/api/trigger/process-crypto-alerts` | POST | Traitement alertes crypto |

## Celery Beat Schedule (automatique)

| Tâche | Cron | Description |
|-------|------|-------------|
| sync-macro | `0 18 * * *` | Synchro FRED quotidienne |
| sync-sectors | `0 22 * * *` | Synchro ETF sectoriels |
| sync-crypto | `15 */6 * * *` | Synchro DeFiLlama 4x/jour |
| scan-insiders | `*/30 13-22 * * *` | Scan Form 4 (heures marché) |
| equity-alerts | `15,45 13-22 * * *` | Workflow alertes actions |
| crypto-alerts | `30 */6 * * *` | Workflow alertes crypto |

## Structure du projet

```
apex-screener/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI entry point
│       ├── core/
│       │   ├── config.py              # Pydantic Settings
│       │   ├── database.py            # SQLAlchemy async engine
│       │   ├── http_client.py         # Rate-limited HTTP client
│       │   └── logging.py             # Structured logging
│       ├── models/
│       │   ├── macro.py               # MacroSeries
│       │   ├── sector.py              # SectorETF
│       │   ├── screener.py            # StockFundamentals + CryptoFundamentals
│       │   ├── insider.py             # InsiderTransaction
│       │   └── alerts.py              # AlertLog
│       ├── modules/
│       │   ├── macro/fetcher.py       # Module 1: FRED ETL
│       │   ├── sector/fetcher.py      # Module 2: ETF + MM200 + RS
│       │   ├── screener/stocks.py     # Module 3a: FCF + ROIC
│       │   ├── screener/crypto.py     # Module 3b: DeFiLlama
│       │   └── insider/fetcher.py     # Module 4: SEC EDGAR Form 4
│       ├── services/
│       │   ├── telegram.py            # Telegram Bot notifications
│       │   └── alert_engine.py        # Moteur de filtrage top-down
│       ├── tasks/
│       │   ├── celery_app.py          # Celery config + Beat schedule
│       │   └── scheduled.py           # Tâches planifiées
│       └── api/
│           └── routes.py              # FastAPI endpoints
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.tsx                    # Router principal
│       ├── pages/
│       │   ├── Dashboard.tsx          # Vue globale
│       │   ├── MacroPage.tsx          # Graphiques FRED
│       │   ├── SectorsPage.tsx        # Radar sectoriel
│       │   ├── CryptoPage.tsx         # Screener DeFi
│       │   ├── InsidersPage.tsx       # Tableau initiés
│       │   └── AlertsPage.tsx         # Historique alertes
│       ├── components/
│       │   ├── Sidebar.tsx
│       │   ├── StatusBadge.tsx
│       │   └── LoadingState.tsx
│       ├── hooks/useData.ts           # TanStack Query hooks
│       └── lib/api.ts                 # API client
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
└── scripts/
    ├── init-db.sh
    └── trigger-all.sh
```

## Maintenance

```bash
# Voir les logs en temps réel
docker compose logs -f celery-worker

# Restart un service
docker compose restart celery-worker

# Mettre à jour le code
git pull
docker compose up -d --build

# Backup PostgreSQL
docker compose exec db pg_dump -U apex apex_screener > backup.sql
```

## Sécurité

- Toutes les clés API dans `.env` (jamais en dur dans le code)
- Rate limiting intégré par source API (configurable dans `.env`)
- Logs structurés JSON consultables via `docker compose logs`
- User non-root dans les containers Docker
- CORS configurable (restreindre en production)
