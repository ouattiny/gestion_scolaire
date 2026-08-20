"""
Ajoute la table compteur_recu (numérotation atomique et illimitée des
reçus) sur une base de données EXISTANTE, sans rien supprimer.

Corrige un bug de l'ancienne méthode de numérotation des reçus : elle
relisait TOUS les paiements à chaque reçu généré (lent avec un grand
volume) et pouvait, en théorie, produire deux fois le même numéro si
deux utilisateurs enregistraient un paiement au même instant. La
nouvelle méthode verrouille une ligne compteur unique (SELECT ... FOR
UPDATE) : un seul numéro ne peut jamais être distribué deux fois, quel
que soit le nombre d'utilisateurs connectés en même temps.

À lancer une seule fois après avoir mis à jour le code (sans danger si
relancé plusieurs fois : le compteur n'est initialisé qu'une seule fois).

Utilisation : python migrer_compteur_recu.py
"""
import re
from app import create_app
from app.models import db, Paiement, CompteurRecu

app = create_app()

with app.app_context():
    db.create_all()  # crée la table compteur_recu si elle n'existe pas encore

    existant = db.session.execute(db.select(CompteurRecu)).scalar_one_or_none()
    if existant is not None:
        print(f"Compteur déjà initialisé (dernier numéro : {existant.dernier_numero}). Rien à faire.")
    else:
        plus_grand = 0
        for p in Paiement.query.all():
            trouve = re.match(r"REC-(\d+)$", p.numero_recu or "")
            if trouve:
                plus_grand = max(plus_grand, int(trouve.group(1)))
        db.session.add(CompteurRecu(dernier_numero=plus_grand))
        db.session.commit()
        print(f"Compteur de reçus initialisé à {plus_grand} (prochain reçu : REC-{plus_grand + 1:06d}).")
