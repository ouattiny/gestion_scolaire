"""
Introduit la séparation des données par année scolaire (AnneeScolaire) sur
une base PostgreSQL EXISTANTE, sans rien supprimer ni modifier les
données déjà saisies.

Étapes (toutes rejouables sans risque si le script est relancé) :
1. Crée la table annee_scolaire (via db.create_all() : ne touche pas aux
   tables déjà existantes).
2. Crée UNE SEULE AnneeScolaire (statut "active"), à partir du libellé déjà
   présent dans Établissement > Année scolaire (ou "2025-2026" par défaut).
3. Ajoute la colonne annee_scolaire_id sur classe, matiere, professeur,
   eleve et trimestre (ALTER TABLE ADD COLUMN — db.create_all() ne le fait
   PAS tout seul sur des tables déjà existantes).
4. Rattache toutes les lignes déjà existantes de ces tables à cette
   année : rien ne change dans ce que voient les utilisateurs aujourd'hui.
5. Rend la colonne obligatoire (NOT NULL) et ajoute la clé étrangère,
   maintenant qu'elle est renseignée partout.
6. Fait glisser les contraintes d'unicité globales (eleve.matricule,
   matiere.nom) vers des contraintes "par année" (matricule/nom unique au
   sein d'une même année scolaire, mais réutilisable d'une année à l'autre).

Utilisation : python migrer_annees_scolaires.py
"""
from sqlalchemy import text
from app import create_app
from app.models import db

app = create_app()

TABLES = ["classe", "matiere", "professeur", "eleve", "trimestre"]


def colonne_existe(connexion, table, colonne):
    return connexion.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :colonne"
    ), {"table": table, "colonne": colonne}).first() is not None


def contrainte_existe(connexion, table, nom):
    return connexion.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name = :table AND constraint_name = :nom"
    ), {"table": table, "nom": nom}).first() is not None


def contrainte_unique_colonne(connexion, table, colonne):
    """Nom d'une contrainte UNIQUE portant exactement sur cette seule
    colonne (créée automatiquement par Postgres pour unique=True), ou
    None si absente / déjà retirée."""
    resultat = connexion.execute(text("""
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_name = kcu.table_name
        WHERE tc.table_name = :table AND tc.constraint_type = 'UNIQUE'
        GROUP BY tc.constraint_name
        HAVING COUNT(*) = 1 AND MAX(kcu.column_name) = :colonne
    """), {"table": table, "colonne": colonne}).first()
    return resultat[0] if resultat else None


with app.app_context():
    db.create_all()  # crée la table annee_scolaire si elle n'existe pas encore

    with db.engine.connect() as connexion:
        annee_id = connexion.execute(
            text("SELECT id FROM annee_scolaire WHERE statut = 'active' LIMIT 1")
        ).scalar()

        if annee_id is None:
            etab = connexion.execute(text("SELECT annee_scolaire FROM etablissement LIMIT 1")).first()
            libelle = (etab[0].strip() if etab and etab[0] else "") or "2025-2026"
            annee_id = connexion.execute(text(
                "INSERT INTO annee_scolaire (libelle, statut, date_creation) "
                "VALUES (:libelle, 'active', now()) RETURNING id"
            ), {"libelle": libelle}).scalar()
            print(f"Année scolaire active créée : {libelle} (id={annee_id})")
        else:
            print(f"Année scolaire active déjà présente (id={annee_id}), poursuite de la migration.")

        for table in TABLES:
            if not colonne_existe(connexion, table, "annee_scolaire_id"):
                print(f"  {table} : ajout de la colonne annee_scolaire_id...")
                connexion.execute(text(f"ALTER TABLE {table} ADD COLUMN annee_scolaire_id INTEGER"))

            nb = connexion.execute(text(
                f"UPDATE {table} SET annee_scolaire_id = :annee_id WHERE annee_scolaire_id IS NULL"
            ), {"annee_id": annee_id}).rowcount
            if nb:
                print(f"  {table} : {nb} ligne(s) rattachée(s) à l'année active")

            connexion.execute(text(f"ALTER TABLE {table} ALTER COLUMN annee_scolaire_id SET NOT NULL"))

            if not contrainte_existe(connexion, table, f"fk_{table}_annee_scolaire_id"):
                connexion.execute(text(
                    f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_annee_scolaire_id "
                    f"FOREIGN KEY (annee_scolaire_id) REFERENCES annee_scolaire (id)"
                ))
                connexion.execute(text(
                    f"CREATE INDEX IF NOT EXISTS ix_{table}_annee_scolaire_id ON {table} (annee_scolaire_id)"
                ))

        # Glisse les anciennes contraintes uniques globales vers des
        # contraintes "par année" (matricule/nom réutilisables d'une année
        # sur l'autre, mais toujours uniques au sein d'une même année).
        vieille = contrainte_unique_colonne(connexion, "eleve", "matricule")
        if vieille:
            connexion.execute(text(f"ALTER TABLE eleve DROP CONSTRAINT {vieille}"))
        if not contrainte_existe(connexion, "eleve", "uq_eleve_matricule_annee"):
            connexion.execute(text(
                "ALTER TABLE eleve ADD CONSTRAINT uq_eleve_matricule_annee "
                "UNIQUE (matricule, annee_scolaire_id)"
            ))

        vieille = contrainte_unique_colonne(connexion, "matiere", "nom")
        if vieille:
            connexion.execute(text(f"ALTER TABLE matiere DROP CONSTRAINT {vieille}"))
        if not contrainte_existe(connexion, "matiere", "uq_matiere_nom_annee"):
            connexion.execute(text(
                "ALTER TABLE matiere ADD CONSTRAINT uq_matiere_nom_annee "
                "UNIQUE (nom, annee_scolaire_id)"
            ))

        # Classe n'avait pas de contrainte unique sur "nom" auparavant :
        # on ajoute simplement la nouvelle contrainte par année si absente,
        # sauf si des doublons existent déjà (cas très improbable) — dans
        # ce cas on prévient plutôt que de planter la migration.
        if not contrainte_existe(connexion, "classe", "uq_classe_nom_annee"):
            doublons = connexion.execute(text(
                "SELECT nom, annee_scolaire_id, COUNT(*) FROM classe "
                "GROUP BY nom, annee_scolaire_id HAVING COUNT(*) > 1"
            )).fetchall()
            if doublons:
                print("  ATTENTION : des classes ont le même nom au sein de la même année "
                      f"({doublons}) — contrainte uq_classe_nom_annee NON ajoutée, "
                      "à corriger manuellement puis relancer ce script.")
            else:
                connexion.execute(text(
                    "ALTER TABLE classe ADD CONSTRAINT uq_classe_nom_annee UNIQUE (nom, annee_scolaire_id)"
                ))

        connexion.commit()

    print("Migration terminée. Aucune donnée existante n'a été supprimée ou modifiée.")
