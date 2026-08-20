"""
Initialise une base de données VIDE, prête pour la mise en service réelle :
aucun professeur, classe, matière ou élève de démonstration — juste le
compte administrateur et une fiche établissement à compléter.

Utilisation : python init_db_production.py

(Pour tester rapidement avec des données d'exemple, utilise plutôt
init_db.py.)
"""
from app import create_app
from app.models import db, Etablissement, Utilisateur

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    db.session.add(Etablissement(
        nom="", code_creation="", statut="", drena="", annee_scolaire="", email="",
    ))

    admin = Utilisateur(identifiant="admin", role="admin")
    admin.set_password("admin123")
    db.session.add(admin)

    db.session.commit()
    print("Base vide initialisée avec succès.")
    print("Connexion admin -> identifiant: admin / mot de passe: admin123")
    print("⚠️  Change ce mot de passe dès la première connexion (page Professeurs "
          "n'a pas d'équivalent pour l'admin pour l'instant : modifie-le directement "
          "en base ou demande-le si besoin).")
    print("Pense à compléter la page 'Établissement' avant de créer tes classes, "
          "matières, professeurs et élèves.")
