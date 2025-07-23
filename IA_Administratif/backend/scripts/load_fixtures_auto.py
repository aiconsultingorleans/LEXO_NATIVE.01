"""
Script pour charger les fixtures automatiquement (sans interaction)
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le chemin parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from core.database import AsyncSessionLocal
from models.user import User
from models.document import Document
from fixtures.users import get_test_users
from fixtures.documents import get_test_documents

async def load_users(db: AsyncSession) -> List[int]:
    """Charge les utilisateurs de test"""
    print("👥 Chargement des utilisateurs...")
    users = get_test_users()
    user_ids = []
    
    # Vérifier les utilisateurs existants
    existing_users = await db.execute(select(User))
    existing_emails = {user.email for user in existing_users.scalars()}
    
    for user_data in users:
        if user_data["email"] not in existing_emails:
            user = User(**user_data)
            db.add(user)
            await db.flush()
            user_ids.append(user.id)
            print(f"  ✓ {user.email} ({user.role})")
        else:
            print(f"  ⏭️  {user_data['email']} existe déjà")
            # Récupérer l'ID de l'utilisateur existant
            result = await db.execute(select(User).where(User.email == user_data["email"]))
            user = result.scalar_one()
            user_ids.append(user.id)
    
    await db.commit()
    print(f"✅ {len(user_ids)} utilisateurs disponibles")
    return user_ids

async def load_documents(db: AsyncSession, user_ids: List[int]):
    """Charge les documents de test"""
    print("📄 Chargement des documents...")
    
    # Vérifier le nombre de documents existants
    result = await db.execute(select(Document))
    existing_count = len(result.scalars().all())
    
    if existing_count > 0:
        print(f"  ℹ️  {existing_count} documents existent déjà")
        return
    
    documents = get_test_documents(user_ids)
    
    for doc_data in documents:
        document = Document(**doc_data)
        db.add(document)
    
    await db.commit()
    print(f"✅ {len(documents)} documents créés")

async def main():
    """Fonction principale"""
    print("🚀 Chargement automatique des fixtures LEXO v1")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Charger les données
        user_ids = await load_users(db)
        if user_ids:
            await load_documents(db, user_ids)
    
    print("\n✨ Fixtures chargées avec succès !")
    print("\n🔑 Comptes de test disponibles :")
    print("  - admin@lexo.fr / admin123 (Admin)")
    print("  - jean.dupont@example.com / password123 (User)")
    print("  - readonly@lexo.fr / readonly123 (ReadOnly)")

if __name__ == "__main__":
    asyncio.run(main())