"""
Lance l'application sur le réseau local de l'établissement.

En développement/test : python app.py
    -> utilise le serveur intégré de Flask (pratique, mais limité :
       ne gère pas bien plusieurs dizaines de connexions à la fois).

En production (recommandé dès qu'il y a plusieurs professeurs
connectés en même temps) : lance plutôt via Waitress, un serveur WSGI
robuste et multi-thread, inclus dans requirements.txt :
    waitress-serve --host=0.0.0.0 --port=5000 --threads=64 app:app

--threads=64 : pour tenir au moins 50 connexions simultanées sans
qu'aucune requête n'attende un thread libre (le pool de connexions
PostgreSQL, configuré dans app/__init__.py, autorise jusqu'à 50
connexions en parallèle — 20 "prêtes" + 30 en pic — ce qui correspond
au nombre de threads Waitress pouvant réellement travailler en même
temps).

Puis, depuis un autre appareil connecté au même Wi-Fi :
    http://<adresse-ip-du-serveur>:5000
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # threaded=True : permet de traiter plusieurs requêtes en parallèle
    # avec le serveur de développement Flask (mieux que rien, mais reste
    # moins robuste que Waitress — voir la note ci-dessus pour la prod).
    # host="0.0.0.0" rend le serveur accessible depuis tout le réseau local.
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
