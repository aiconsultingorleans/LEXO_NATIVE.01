# LEXO v1 - Makefile
# Assistant IA pour la gestion administrative intelligente

.PHONY: help setup-dev install clean start stop restart logs test lint format build deploy

# Variables
COMPOSE_FILE = docker-compose.yml
BACKEND_DIR = backend
FRONTEND_DIR = frontend

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Affiche l'aide
	@echo "$(BLUE)LEXO v1 - Commandes disponibles:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup-dev: ## Configuration initiale de l'environnement de développement
	@echo "$(BLUE)🔧 Configuration de l'environnement de développement...$(NC)"
	@cp .env.example .env || echo "$(YELLOW)⚠️  .env déjà existant$(NC)"
	@cp $(FRONTEND_DIR)/.env.example $(FRONTEND_DIR)/.env.local || echo "$(YELLOW)⚠️  .env.local déjà existant$(NC)"
	@echo "$(GREEN)✅ Environnement configuré$(NC)"

install: ## Installation des dépendances
	@echo "$(BLUE)📦 Installation des dépendances...$(NC)"
	@cd $(BACKEND_DIR) && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	@cd $(FRONTEND_DIR) && npm install
	@echo "$(GREEN)✅ Dépendances installées$(NC)"

clean: ## Nettoyage des fichiers temporaires
	@echo "$(BLUE)🧹 Nettoyage...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans
	@docker system prune -f
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf $(FRONTEND_DIR)/.next
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

start: ## Démarre tous les services
	@echo "$(BLUE)🚀 Démarrage des services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✅ Services démarrés$(NC)"
	@echo "$(YELLOW)Frontend: http://localhost:3000$(NC)"
	@echo "$(YELLOW)Backend API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)API Docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Adminer: http://localhost:8080$(NC)"

stop: ## Arrête tous les services
	@echo "$(BLUE)🛑 Arrêt des services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✅ Services arrêtés$(NC)"

restart: stop start ## Redémarre tous les services

logs: ## Affiche les logs de tous les services
	@docker-compose -f $(COMPOSE_FILE) logs -f

logs-backend: ## Affiche les logs du backend
	@docker-compose -f $(COMPOSE_FILE) logs -f backend

logs-frontend: ## Affiche les logs du frontend
	@docker-compose -f $(COMPOSE_FILE) logs -f frontend

logs-db: ## Affiche les logs de la base de données
	@docker-compose -f $(COMPOSE_FILE) logs -f postgres

test: ## Lance les tests
	@echo "$(BLUE)🧪 Lancement des tests...$(NC)"
	@cd $(BACKEND_DIR) && python -m pytest tests/ -v
	@cd $(FRONTEND_DIR) && npm run test
	@echo "$(GREEN)✅ Tests terminés$(NC)"

test-backend: ## Lance les tests backend uniquement
	@echo "$(BLUE)🧪 Tests backend...$(NC)"
	@cd $(BACKEND_DIR) && python -m pytest tests/ -v

test-frontend: ## Lance les tests frontend uniquement
	@echo "$(BLUE)🧪 Tests frontend...$(NC)"
	@cd $(FRONTEND_DIR) && npm run test

lint: ## Vérification du code (linting)
	@echo "$(BLUE)🔍 Vérification du code...$(NC)"
	@cd $(BACKEND_DIR) && ruff check . && black --check .
	@cd $(FRONTEND_DIR) && npm run lint
	@echo "$(GREEN)✅ Code vérifié$(NC)"

format: ## Formatage du code
	@echo "$(BLUE)✨ Formatage du code...$(NC)"
	@cd $(BACKEND_DIR) && black .
	@cd $(FRONTEND_DIR) && npm run format
	@echo "$(GREEN)✅ Code formaté$(NC)"

type-check: ## Vérification des types TypeScript
	@echo "$(BLUE)🔍 Vérification des types...$(NC)"
	@cd $(FRONTEND_DIR) && npm run type-check
	@echo "$(GREEN)✅ Types vérifiés$(NC)"

build: ## Build des applications pour production
	@echo "$(BLUE)🏗️  Build des applications...$(NC)"
	@cd $(FRONTEND_DIR) && npm run build
	@echo "$(GREEN)✅ Build terminé$(NC)"

db-migrate: ## Applique les migrations de base de données
	@echo "$(BLUE)🗄️  Application des migrations...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec backend alembic upgrade head
	@echo "$(GREEN)✅ Migrations appliquées$(NC)"

db-reset: ## Remet à zéro la base de données
	@echo "$(RED)⚠️  Remise à zéro de la base de données...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) down -v
	@docker volume rm lexo_postgres_data || true
	@docker-compose -f $(COMPOSE_FILE) up -d postgres
	@sleep 5
	@docker-compose -f $(COMPOSE_FILE) exec backend alembic upgrade head
	@echo "$(GREEN)✅ Base de données remise à zéro$(NC)"

dev-backend: ## Lance le backend en mode développement (local)
	@echo "$(BLUE)🚀 Démarrage backend local...$(NC)"
	@cd $(BACKEND_DIR) && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Lance le frontend en mode développement (local)
	@echo "$(BLUE)🚀 Démarrage frontend local...$(NC)"
	@cd $(FRONTEND_DIR) && npm run dev

status: ## Affiche le statut des services
	@echo "$(BLUE)📊 Statut des services:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) ps

health: ## Vérifie la santé des services
	@echo "$(BLUE)🏥 Vérification de la santé des services...$(NC)"
	@curl -s http://localhost:8000/api/v1/health || echo "$(RED)❌ Backend indisponible$(NC)"
	@curl -s http://localhost:3000 > /dev/null && echo "$(GREEN)✅ Frontend OK$(NC)" || echo "$(RED)❌ Frontend indisponible$(NC)"

# Commandes avancées
backup-db: ## Sauvegarde la base de données
	@echo "$(BLUE)💾 Sauvegarde de la base de données...$(NC)"
	@mkdir -p backups
	@docker-compose -f $(COMPOSE_FILE) exec postgres pg_dump -U lexo lexo_dev > backups/db_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Sauvegarde terminée$(NC)"

restore-db: ## Restaure la base de données (usage: make restore-db FILE=backup.sql)
	@echo "$(BLUE)📥 Restauration de la base de données...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) exec -T postgres psql -U lexo lexo_dev < $(FILE)
	@echo "$(GREEN)✅ Restauration terminée$(NC)"

update: ## Met à jour les dépendances
	@echo "$(BLUE)🔄 Mise à jour des dépendances...$(NC)"
	@cd $(BACKEND_DIR) && pip install --upgrade -r requirements.txt
	@cd $(FRONTEND_DIR) && npm update
	@echo "$(GREEN)✅ Dépendances mises à jour$(NC)"

# Alias
up: start
down: stop
ps: status