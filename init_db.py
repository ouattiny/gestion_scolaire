"""
Initialise la base de données avec une structure de démonstration
minimale (établissement, une classe, les matières, les trimestres et un
élève d'exemple), MAIS SANS AUCUN PROFESSEUR NI AFFECTATION PAR DÉFAUT :
c'est à l'administrateur de les créer lui-même dans l'application
(pages Professeurs puis Affectations), avec ses propres noms et
identifiants de connexion.

Utilisation : python init_db.py
"""
from app import create_app
from app.models import db, Etablissement, Niveau, Classe, Matiere, Eleve, Trimestre, Utilisateur, AnneeScolaire
from app.utils import creer_niveaux_canoniques

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    annee = AnneeScolaire(libelle="2025-2026", statut="active")
    db.session.add(annee)
    db.session.flush()

    etablissement = Etablissement(
        nom="EPC DA-AWAT EL ISLAMIYAT BOUAKE",
        code_creation="2145",
        statut="PRIVEE",
        drena="DRENA Bouaké 2",
        annee_scolaire="2025-2026",
        email="daawateelislamiyat@gmail.com",
    )
    db.session.add(etablissement)

    # Les 7 niveaux (premier cycle 6e->3e + second cycle 2nde->Terminale)
    # sont toujours créés dès l'installation : aucune classe n'y est
    # rattachée automatiquement, mais ils sont disponibles dans le menu
    # déroulant "Niveau" dès la première utilisation de la page Classes.
    creer_niveaux_canoniques()
    niveau_3e = Niveau.query.filter_by(nom="3e").first()
    db.session.flush()

    classe_3e = Classe(nom="3eme", niveau_id=niveau_3e.id, annee_scolaire_id=annee.id)
    db.session.add(classe_3e)
    db.session.flush()

    matieres = [
        Matiere(nom="Français", coefficient=4, groupe="Lettres", annee_scolaire_id=annee.id),
        Matiere(nom="Anglais", coefficient=2, groupe="Lettres", annee_scolaire_id=annee.id),
        Matiere(nom="Hist-Geo", coefficient=2, groupe="Lettres", annee_scolaire_id=annee.id),
        Matiere(nom="Espagnol", coefficient=1, groupe="Lettres", annee_scolaire_id=annee.id),
        Matiere(nom="Maths", coefficient=3, groupe="Sciences", annee_scolaire_id=annee.id),
        Matiere(nom="SVT", coefficient=2, groupe="Sciences", annee_scolaire_id=annee.id),
        Matiere(nom="Phys-Chimie", coefficient=2, groupe="Sciences", annee_scolaire_id=annee.id),
        Matiere(nom="EDHC", coefficient=1, groupe="Autres", annee_scolaire_id=annee.id),
        Matiere(nom="EPS", coefficient=1, groupe="Autres", annee_scolaire_id=annee.id),
        Matiere(nom="Conduite", coefficient=1, groupe="Autres", annee_scolaire_id=annee.id),
    ]
    db.session.add_all(matieres)

    for numero in (1, 2, 3):
        db.session.add(Trimestre(
            numero=numero, annee_scolaire="2025-2026", annee_scolaire_id=annee.id,
            date_debut={"1": "16/09/2025", "2": "05/01/2026", "3": "23/03/2026"}[str(numero)],
            date_fin={"1": "19/12/2025", "2": "20/03/2026", "3": "30/06/2026"}[str(numero)],
        ))

    eleve = Eleve(
        matricule="21791803 L", nom="DIARRA", prenoms="ADJARA", sexe="F",
        date_naissance="16/11/2009", lieu_naissance="Bouaké", classe_id=classe_3e.id,
        annee_scolaire_id=annee.id,
    )
    db.session.add(eleve)

    admin = Utilisateur(identifiant="admin", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)

    db.session.commit()
    print("Base initialisée avec succès (aucun professeur par défaut).")
    print("Connexion admin -> identifiant: admin / mot de passe: admin123")
    print("")
    print("Prochaines étapes dans l'application :")
    print("  1. Page Professeurs : créer chaque professeur avec ses identifiants")
    print("  2. Page Affectations : relier professeur + classe + matière + coefficient")
    print("  3. Page Emploi du temps : configurer les créneaux de la classe")
