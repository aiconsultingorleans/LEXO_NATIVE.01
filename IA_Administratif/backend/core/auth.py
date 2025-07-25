"""
Module d'authentification centralisé
Réexporte les fonctions d'auth depuis api.auth pour une utilisation transversale
"""

from api.auth import get_current_user

# Réexporter pour usage dans d'autres modules
__all__ = ["get_current_user"]