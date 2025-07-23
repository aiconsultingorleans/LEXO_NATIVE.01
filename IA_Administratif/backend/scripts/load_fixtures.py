"""
Script pour charger les fixtures dans la base de données
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le chemin parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from core.database import get_db, engine
from models.user import User
from models.document import Document
from fixtures.users import get_test_users
from fixtures.documents import get_test_documents

async def clear_database(db: AsyncSession):
    """Efface les données existantes"""
    print("🗑️  Suppression des données existantes...")
    
    # Supprimer les documents d'abord (foreign key)
    await db.execute(delete(Document))
    await db.execute(delete(User))
    await db.commit()
    print("✅ Base de données nettoyée")

async def load_users(db: AsyncSession) -> List[int]:
    """Charge les utilisateurs de test"""
    print("👥 Chargement des utilisateurs...")
    users = get_test_users()
    user_ids = []
    
    for user_data in users:
        user = User(**user_data)
        db.add(user)
        await db.flush()
        user_ids.append(user.id)
        print(f"  ✓ {user.email} ({user.role})")
    
    await db.commit()
    print(f"✅ {len(users)} utilisateurs créés")
    return user_ids

async def load_documents(db: AsyncSession, user_ids: List[int]):
    """Charge les documents de test"""
    print("📄 Chargement des documents...")
    documents = get_test_documents(user_ids)
    
    for doc_data in documents:
        document = Document(**doc_data)
        db.add(document)
    
    await db.commit()
    print(f"✅ {len(documents)} documents créés")

async def main():
    """Fonction principale"""
    print("🚀 Chargement des fixtures LEXO v1")
    print("=" * 50)
    
    # Créer directement une session
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        # Optionnel : nettoyer la base
        response = input("⚠️  Voulez-vous effacer les données existantes ? (y/N): ")
        if response.lower() == 'y':
            await clear_database(db)
        
        # Charger les données
        user_ids = await load_users(db)
        await load_documents(db, user_ids)
    
    print("\n✨ Fixtures chargées avec succès !")
    print("\n📊 Résumé :")
    print(f"  - Utilisateurs : {len(get_test_users())}")
    print(f"  - Documents : {len(get_test_documents([1, 2, 3]))}")
    print("\n🔑 Comptes de test :")
    print("  - admin@lexo.fr / admin123 (Admin)")
    print("  - jean.dupont@example.com / password123 (User)")
    print("  - readonly@lexo.fr / readonly123 (ReadOnly)")

if __name__ == "__main__":
    asyncio.run(main())