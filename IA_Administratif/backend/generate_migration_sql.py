#!/usr/bin/env python3
"""
Script pour générer le SQL des migrations Alembic sans connexion DB
"""

import os
import sys
from alembic.config import Config
from alembic import command
from io import StringIO

def generate_sql():
    """Générer le SQL pour toutes les migrations"""
    
    # Configuration d'Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Capturer la sortie SQL
    sql_output = StringIO()
    
    # Configurer Alembic pour générer du SQL
    def dump(sql, *multiparams, **params):
        sql_output.write(str(sql.compile(dialect=engine.dialect)))
        sql_output.write(";\n")
    
    # Générer le SQL pour la migration
    try:
        # Mode offline - génère juste le SQL
        command.upgrade(alembic_cfg, "head", sql=True)
        
        print("✅ SQL généré avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération SQL: {e}")
        return False
    
    return True

if __name__ == "__main__":
    generate_sql()