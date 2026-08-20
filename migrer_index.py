"""
Ajoute les index de performance sur une base de données EXISTANTE, sans
rien supprimer (contrairement à init_db.py qui repart de zéro). À lancer
une fois après avoir mis à jour le code, si tu as déjà des données que
tu ne veux pas perdre.

Utilisation : python migrer_index.py
"""
from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    print("Ajout des index de performance (sans toucher aux données existantes)...")
    # db.create_all() ne supprime jamais rien : il ne fait qu'ajouter ce
    # qui manque (nouvelles tables, et — avec SQLAlchemy récent — les
    # index déclarés sur les colonnes existantes ne sont PAS ajoutés
    # automatiquement par create_all() sur des tables déjà là ; on les
    # crée donc explicitement ci-dessous, de façon idempotente.
    db.create_all()

    inspecteur = db.inspect(db.engine)
    with db.engine.connect() as connexion:
        for table in db.metadata.sorted_tables:
            index_existants = {ix["name"] for ix in inspecteur.get_indexes(table.name)}
            for index in table.indexes:
                if index.name in index_existants:
                    continue
                print(f"  création de l'index {index.name} sur {table.name}...")
                index.create(bind=connexion)
        connexion.commit()

    print("Terminé. Les index de performance sont en place.")
