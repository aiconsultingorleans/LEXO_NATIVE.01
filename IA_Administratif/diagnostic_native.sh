#!/bin/bash

# 🔍 LEXO v1 - Diagnostic Complet Native macOS
echo "=== DIAGNOSTIC LEXO NATIF ==="
echo "Date: $(date)"
echo ""

echo "🔍 Services Système:"
brew services list | grep -E "(postgresql|redis)"
echo ""

echo "🌐 Ports Actifs:"
lsof -i :3000 -i :8000 -i :8004 -i :5432 -i :6379 2>/dev/null || echo "Aucun port actif"
echo ""

echo "💾 Utilisation Mémoire:"
ps aux | grep -E "(python|node|uvicorn|postgres|redis)" | grep -v grep
echo ""

echo "📊 Tests Connectivité:"
curl -s http://localhost:8000/api/v1/health >/dev/null && echo "✅ Backend OK" || echo "❌ Backend KO"
curl -s http://localhost:3000 >/dev/null && echo "✅ Frontend OK" || echo "❌ Frontend KO"  
curl -s http://localhost:8004/health >/dev/null && echo "✅ Mistral OK" || echo "❌ Mistral KO"
redis-cli ping 2>/dev/null | grep -q PONG && echo "✅ Redis OK" || echo "❌ Redis KO"
psql -U lexo -d lexo_dev -c "SELECT 1;" >/dev/null 2>&1 && echo "✅ PostgreSQL OK" || echo "❌ PostgreSQL KO"
echo ""

echo "📂 Environnements Virtuels:"
[ -d "backend/venv" ] && echo "✅ Backend venv OK" || echo "❌ Backend venv manquant"
[ -d "ai_services/venv" ] && echo "✅ MLX venv OK" || echo "❌ MLX venv manquant"
echo ""

echo "📝 Fichiers PID:"
[ -f "logs/backend_native.pid" ] && echo "✅ Backend PID: $(cat logs/backend_native.pid)" || echo "❌ Backend PID manquant"
[ -f "logs/frontend_native.pid" ] && echo "✅ Frontend PID: $(cat logs/frontend_native.pid)" || echo "❌ Frontend PID manquant"
[ -f "logs/mistral_native.pid" ] && echo "✅ Mistral PID: $(cat logs/mistral_native.pid)" || echo "❌ Mistral PID manquant"
echo ""

echo "🍎 Architecture Apple Silicon:"
python3 -c "import platform; print(f'Python: {platform.machine()}')" 2>/dev/null || echo "❌ Python non accessible"
echo ""

echo "🧪 Tests Imports Critiques:"
cd backend && source venv/bin/activate 2>/dev/null && python -c "import fastapi, sqlalchemy, redis, chromadb; print('✅ Backend imports OK')" 2>/dev/null || echo "❌ Backend imports KO"
cd ../ai_services && source venv/bin/activate 2>/dev/null && python -c "import mlx, mlx_lm; print('✅ MLX imports OK')" 2>/dev/null || echo "❌ MLX imports KO"
cd ..
echo ""

echo "📈 Performance et Logs:"
echo "Dernières lignes logs backend:"
tail -3 logs/backend_native.log 2>/dev/null || echo "Pas de logs backend"
echo ""
echo "Dernières lignes logs frontend:"
tail -3 logs/frontend_native.log 2>/dev/null || echo "Pas de logs frontend"
echo ""

echo "=== FIN DIAGNOSTIC ==="