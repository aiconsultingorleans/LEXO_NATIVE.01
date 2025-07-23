"""
Fixtures pour les documents de test
"""

from typing import List, Dict
from datetime import datetime, timedelta
import random

def get_test_documents(user_ids: List[int]) -> List[Dict]:
    """Retourne une liste de documents de test"""
    categories = ["factures", "impots", "rib", "contrats", "courriers", "non_classes"]
    entities = [
        ["EDF", "Électricité", "Énergie"],
        ["Orange", "Télécom", "Internet"],
        ["DGFIP", "Impôts", "Administration"],
        ["Crédit Agricole", "Banque", "Finance"],
        ["CPAM", "Sécurité Sociale", "Santé"],
        ["La Poste", "Courrier", "Service"],
    ]
    
    documents = []
    base_date = datetime.now() - timedelta(days=180)
    
    for i in range(50):
        user_id = random.choice(user_ids)
        category = random.choice(categories)
        entity_set = random.choice(entities)
        doc_date = base_date + timedelta(days=random.randint(0, 180))
        
        document = {
            "user_id": user_id,
            "filename": f"document_{i+1:03d}.pdf",
            "original_filename": f"scan_{i+1:03d}_{entity_set[0]}.pdf",
            "file_path": f"/data/documents/{user_id}/{category}/document_{i+1:03d}.pdf",
            "file_size": random.randint(100000, 5000000),  # Entre 100KB et 5MB
            "mime_type": "application/pdf",
            "category": category,
            "confidence_score": round(random.uniform(0.85, 0.99), 2),
            "entities": entity_set,
            "amount": round(random.uniform(50, 500), 2) if category == "factures" else None,
            "document_date": doc_date,
            "ocr_text": f"Ceci est un document de test de type {category} pour {entity_set[0]}. "
                       f"Date: {doc_date.strftime('%d/%m/%Y')}. "
                       f"Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "processed_at": datetime.now() - timedelta(hours=random.randint(1, 48)),
            "custom_tags": [category, entity_set[0].lower()] + (["urgent"] if random.random() > 0.8 else []),
            "embeddings_id": None
        }
        
        documents.append(document)
    
    return documents