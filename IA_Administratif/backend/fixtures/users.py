"""
Fixtures pour les utilisateurs de test
"""

from typing import List, Dict
from datetime import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_test_users() -> List[Dict]:
    """Retourne une liste d'utilisateurs de test"""
    return [
        {
            "email": "admin@lexo.fr",
            "first_name": "Admin",
            "last_name": "LEXO",
            "hashed_password": pwd_context.hash("admin123"),
            "role": "admin",
            "is_active": True
        },
        {
            "email": "jean.dupont@example.com",
            "first_name": "Jean",
            "last_name": "Dupont",
            "hashed_password": pwd_context.hash("password123"),
            "role": "user",
            "is_active": True
        },
        {
            "email": "marie.martin@example.com",
            "first_name": "Marie",
            "last_name": "Martin",
            "hashed_password": pwd_context.hash("password123"),
            "role": "user",
            "is_active": True
        },
        {
            "email": "readonly@lexo.fr",
            "first_name": "ReadOnly",
            "last_name": "User",
            "hashed_password": pwd_context.hash("readonly123"),
            "role": "readonly",
            "is_active": True
        },
        {
            "email": "inactive@lexo.fr",
            "first_name": "Inactive",
            "last_name": "User",
            "hashed_password": pwd_context.hash("inactive123"),
            "role": "user",
            "is_active": False
        }
    ]