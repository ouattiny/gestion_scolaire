"""
Ajoute le verrouillage progressif des tentatives de connexion (côté
serveur, en base de données) sur une base PostgreSQL EXISTANTE, sans
rien supprimer ni modifier les comptes déjà créés.

Étapes (rejouable sans risque si le script est relancé) :
1. Ajoute à la table utilisateur les colonnes de suivi des tentatives de
   connexion (tentatives_echouees, niveau_verrouillage, etc.) — tous les
   comptes existants démarrent à "0 échec, jamais verrouillé", donc rien
   ne change pour les utilisateurs déjà en place.
2. Crée la table journal_connexion (journal de sécurité).

Utilisation : python migrer_securite_connexion.py
"""
from sqlalchemy import text
from app import create_app
from app.models import db

app = create_app()


def colonne_existe(connexion, table, colonne):
    return connexion.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :colonne"
    ), {"table": table, "colonne": colonne}).first() is not None


COLONNES = [
    ("tentatives_echouees", "INTEGER NOT NULL DEFAULT 0"),
    ("derniere_tentative", "TIMESTAMP"),
    ("niveau_verrouillage", "INTEGER NOT NULL DEFAULT 0"),
    ("verrouille_depuis", "TIMESTAMP"),
    ("verrouille_jusqu_a", "TIMESTAMP"),
    ("derniere_connexion_reussie", "TIMESTAMP"),
]

with app.app_context():
    with db.engine.connect() as connexion:
        for nom, definition in COLONNES:
            if not colonne_existe(connexion, "utilisateur", nom):
                print(f"utilisateur : ajout de la colonne {nom}...")
                connexion.execute(text(f"ALTER TABLE utilisateur ADD COLUMN {nom} {definition}"))
        connexion.commit()

    db.create_all()  # crée journal_connexion si elle n'existe pas encore

    print("Migration terminée. Aucun compte existant n'a été verrouillé ni modifié.")
