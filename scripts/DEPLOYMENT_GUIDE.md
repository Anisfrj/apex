# APEX Equity Screener - Deployment Guide

## 📋 Prérequis

Ton VPS doit avoir :
- Docker & Docker Compose installés
- Git configuré
- Port 8000 (backend) et 80 (frontend) ouverts
- Accès SSH à root@51.255.200.29

## 🚀 Déploiement Automatique (Recommandé)

### Option 1: Script tout-en-un

```bash
# Connexion SSH au VPS
ssh root@51.255.200.29

# Navigation vers le répertoire apex
cd ~/apex  # ou cd /root/apex

# Rendre le script exécutable et lancer
chmod +x scripts/deploy_equity_screener.sh
bash scripts/deploy_equity_screener.sh
```

Ce script va :
1. ✅ Pull le code depuis GitHub
2. ✅ Créer la table `equities_fundamentals`
3. ✅ Rebuild le backend avec yfinance
4. ✅ Redémarrer tous les services
5. ✅ Vérifier le status des containers

## 🔧 Déploiement Manuel

Si le script automatique ne fonctionne pas, voici les étapes détaillées :

### 1. Pull le code
```bash
cd ~/apex
git pull origin main
```

### 2. Créer la table PostgreSQL
```bash
docker exec -i apex-db psql -U apex -d apex_screener < scripts/create_equities_fundamentals_table.sql
```

Vérifier la création :
```bash
docker exec -it apex-db psql -U apex -d apex_screener -c "\dt equities_fundamentals"
```

### 3. Rebuild le backend
```bash
docker compose build backend
```

### 4. Restart tous les services
```bash
docker compose down
docker compose up -d
```

### 5. Vérifier le status
```bash
docker compose ps
```

Tous les containers doivent être "Up" et "healthy".

## 🧪 Tests Post-Déploiement

### Test 1: Trigger le scraping
```bash
curl -X POST http://localhost:8000/api/trigger/sync-equities
```

Résultat attendu : `{"status":"success","message":"Equity screener sync triggered","task_id":"..."}`

### Test 2: Vérifier les logs Celery
```bash
docker compose logs -f celery-worker
```

Tu dois voir :
- `📊 600+ tickers à scraper`
- `Progress: 50/600`, `100/600`, etc.
- `✅ Equity Screener sync terminé: 600/600 réussis`

### Test 3: Vérifier la base de données
```bash
docker exec -it apex-db psql -U apex -d apex_screener -c \
  "SELECT COUNT(*), sector FROM equities_fundamentals GROUP BY sector;"
```

Tu dois voir des lignes avec différents secteurs (Technology, Healthcare, Finance, etc.)

### Test 4: Tester l'API de recherche
```bash
curl "http://localhost:8000/api/equities?sector=Technology&min_market_cap=10000000000&limit=10"
```

Doit retourner 10 tech stocks avec market cap > 10B.

### Test 5: Accès frontend
Ouvre ton navigateur : `http://51.255.200.29`

Va sur **Screener Actions** dans le sidebar → tu dois voir la page avec les filtres.

## 🐛 Troubleshooting

### Problème: Redis connection refused
```bash
# Vérifier que Redis tourne
docker compose ps redis

# Restart Redis si nécessaire
docker compose restart redis
```

### Problème: Celery task not found
```bash
# Vérifier que equity_tasks est dans celery_app.py
cat backend/app/tasks/celery_app.py | grep equity_tasks

# Doit afficher : include=["app.tasks.scheduled", "app.tasks.equity_tasks"],
```

### Problème: Table equities_fundamentals n'existe pas
```bash
# Recréer la table manuellement
docker exec -i apex-db psql -U apex -d apex_screener < scripts/create_equities_fundamentals_table.sql
```

### Problème: Module yfinance not found
```bash
# Rebuild le backend pour installer yfinance
docker compose build backend --no-cache
docker compose up -d
```

## 📊 Monitoring Production

### Voir tous les logs
```bash
docker compose logs -f
```

### Logs backend seulement
```bash
docker compose logs -f backend
```

### Logs Celery worker
```bash
docker compose logs -f celery-worker
```

### Vérifier la santé des services
```bash
watch -n 2 'docker compose ps'
```

## 🔄 Workflow de Scraping

1. **Trigger manuel** : `POST /api/trigger/sync-equities`
2. **Celery** reçoit la task `celery_sync_equities`
3. **Scraping** : 600+ tickers via yfinance (Wikipedia → yfinance API)
4. **Stockage** : Upsert dans `equities_fundamentals`
5. **Frontend** : Affichage avec filtres avancés

## ⚙️ Configuration

Les variables d'environnement sont dans `.env` (déjà configuré) :
- `DATABASE_URL` : PostgreSQL connection
- `REDIS_URL` : Redis pour Celery
- `FMP_API_KEY` : Pas utilisé pour equity screener (yfinance est gratuit)

## 📈 Prochaines Étapes

Une fois déployé et testé :
1. Ajouter un cron pour scraping quotidien (Celery Beat)
2. Optimiser les filtres frontend
3. Ajouter des graphiques de performance
4. Intégrer avec les autres modules (Insider, Macro, Sector)

---

**Auteur** : Anis  
**Date** : Avril 2026  
**Version** : 1.0
