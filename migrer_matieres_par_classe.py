"""
Fait évoluer une base PostgreSQL EXISTANTE pour la gestion des matières
par classe et l'extension au second cycle (2nde, 1ère, Terminale), sans
rien supprimer ni modifier les données déjà saisies.

Étapes (toutes rejouables sans risque si le script est relancé) :
1. Ajoute la colonne "cycle" à Niveau, et la déduit automatiquement pour
   les niveaux déjà existants (6e/5e/4e/3e -> premier_cycle, tout le
   reste -> premier_cycle par défaut, à corriger manuellement au besoin
   si un niveau au nom inhabituel existait déjà).
2. Crée les 3 niveaux du second cycle (2nde, 1ère, Terminale) s'ils
   n'existent pas déjà — aucune classe n'y est automatiquement rattachée,
   c'est à l'administrateur de créer ses classes de 2nde/1ère/Terminale
   depuis la page Classes.
3. Sur Affectation : rend professeur_id optionnel, ajoute "active"
   (toutes les affectations existantes restent actives, donc RIEN ne
   change dans les bulletins/notes/moyennes déjà en place) et
   "ordre_affichage" (initialisé pour préserver EXACTEMENT l'ordre
   d'affichage actuel — groupe Lettres/Sciences/Autres puis id — pour
   qu'aucun bulletin existant ne change d'ordre après la migration).

Utilisation : python migrer_matieres_par_classe.py
"""
from sqlalchemy import text
from app import create_app
from app.models import db
from app.utils import creer_niveaux_canoniques

app = create_app()

NIVEAUX_PREMIER_CYCLE = ("6e", "5e", "4e", "3e")


def colonne_existe(connexion, table, colonne):
    return connexion.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :colonne"
    ), {"table": table, "colonne": colonne}).first() is not None


with app.app_context():
    with db.engine.connect() as connexion:
        # --- 1. Niveau.cycle ---
        if not colonne_existe(connexion, "niveau", "cycle"):
            print("niveau : ajout de la colonne cycle...")
            connexion.execute(text(
                "ALTER TABLE niveau ADD COLUMN cycle VARCHAR(20) NOT NULL DEFAULT 'premier_cycle'"
            ))
        nb = connexion.execute(text(
            "UPDATE niveau SET cycle = 'premier_cycle' WHERE nom = ANY(:noms) AND cycle IS DISTINCT FROM 'premier_cycle'"
        ), {"noms": list(NIVEAUX_PREMIER_CYCLE)}).rowcount
        if nb:
            print(f"niveau : {nb} niveau(x) du premier cycle confirmé(s)")

        # --- 2. Affectation.professeur_id nullable, active, ordre_affichage ---
        connexion.execute(text("ALTER TABLE affectation ALTER COLUMN professeur_id DROP NOT NULL"))

        if not colonne_existe(connexion, "affectation", "active"):
            print("affectation : ajout de la colonne active...")
            connexion.execute(text(
                "ALTER TABLE affectation ADD COLUMN active BOOLEAN NOT NULL DEFAULT true"
            ))

        if not colonne_existe(connexion, "affectation", "ordre_affichage"):
            print("affectation : ajout de la colonne ordre_affichage...")
            connexion.execute(text(
                "ALTER TABLE affectation ADD COLUMN ordre_affichage INTEGER NOT NULL DEFAULT 0"
            ))
            # Préserve l'ordre d'affichage ACTUEL (celui utilisé jusqu'ici dans
            # les bulletins : groupe Lettres/Sciences/Autres, puis id) en le
            # figeant explicitement dans ordre_affichage, pour qu'aucun
            # bulletin déjà en place ne change d'ordre après la migration.
            connexion.execute(text("""
                WITH ordonnees AS (
                    SELECT
                        a.id,
                        ROW_NUMBER() OVER (
                            PARTITION BY a.classe_id
                            ORDER BY
                                CASE m.groupe
                                    WHEN 'Lettres' THEN 0
                                    WHEN 'Sciences' THEN 1
                                    ELSE 2
                                END,
                                a.id
                        ) AS position
                    FROM affectation a
                    JOIN matiere m ON m.id = a.matiere_id
                )
                UPDATE affectation
                SET ordre_affichage = ordonnees.position
                FROM ordonnees
                WHERE affectation.id = ordonnees.id
            """))
            print("affectation : ordre_affichage initialisé (ordre actuel préservé)")

        connexion.commit()

    # --- 3. Niveaux du second cycle (2nde, 1ère, Terminale) ---
    creer_niveaux_canoniques()
    print("Niveaux canoniques (premier + second cycle) disponibles.")

    print("Migration terminée. Aucune donnée existante n'a été supprimée ou modifiée.")
