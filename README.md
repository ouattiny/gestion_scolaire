# Gestion Scolaire — EPC DA-AWAT EL ISLAMIYAT BOUAKE

Application web locale (intranet) de gestion scolaire et d'édition de
bulletins, conforme au cahier des charges (collège 6e-3e, DRENA Bouaké 2).

## 🚀 Mise en production (changement majeur)

L'application est passée de SQLite à **PostgreSQL**, et a reçu un
renforcement de sécurité complet. À faire avant de relancer le projet :

### 1. Base de données PostgreSQL
```
createdb gestion_scolaire
```
Par défaut, l'app se connecte à `postgresql://postgres@localhost/gestion_scolaire`.
Pour un autre serveur (ex. déploiement hébergé), définis la variable
d'environnement `DATABASE_URL` (ex. `postgresql://user:motdepasse@hote:5432/nom_base`)
— elle est automatiquement prioritaire.

Le pilote utilisé est **`pg8000`** (100% Python, aucune compilation
native nécessaire) plutôt que `psycopg2` — celui-ci échoue à
l'installation sur certains environnements sans compilateur C (Termux
sur Android notamment). Peu importe comment `DATABASE_URL` est écrite
(`postgresql://...`), l'application bascule automatiquement sur
`postgresql+pg8000://...` en interne.

### 2. Variables d'environnement (recommandé en production)
| Variable | Rôle | Défaut |
|---|---|---|
| `DATABASE_URL` | Connexion PostgreSQL | `postgresql://postgres@localhost/gestion_scolaire` |
| `SECRET_KEY` | Clé de session Flask — **change-la en production** | valeur de développement |
| `FORCE_HTTPS` | `true` pour activer cookies "Secure", HSTS et redirection HTTPS | `false` |

⚠️ **Sur le réseau Wi-Fi local de l'école (HTTP simple, sans certificat)**,
laisse `FORCE_HTTPS=false` (ou ne la définis pas) — sinon les navigateurs
refuseront le cookie de session et la connexion échouera. Active
`FORCE_HTTPS=true` uniquement si l'application est servie derrière un
certificat HTTPS valide (déploiement hébergé, reverse-proxy, etc.).

### 3. Sécurité mise en place
- **Mots de passe** : hachés (`werkzeug.security`), jamais stockés en clair.
- **Anti-bruteforce** : `Flask-Limiter` (10 tentatives/minute par IP sur la
  connexion) + verrouillage progressif par identifiant après 5 échecs
  (pause croissante jusqu'à 5 min).
- **Cookies de session** : `HttpOnly`, `SameSite=Lax`, `Secure` si `FORCE_HTTPS=true`.
- **En-têtes HTTP** (`Flask-Talisman`) : CSP stricte (`self` uniquement —
  l'app est 100% autonome, aucun script/CSS externe), `X-Frame-Options`,
  `X-Content-Type-Options`, HSTS si `FORCE_HTTPS=true`.
- **CSRF** : `Flask-WTF` (`CSRFProtect`) actif globalement — chaque
  formulaire POST embarque un jeton CSRF vérifié côté serveur.
- **XSS** : protection native de Jinja2 (échappement automatique de
  toutes les variables affichées), jamais désactivée dans le projet.

### 4. Sauvegarde PostgreSQL
Le bouton **Sauvegarde** (espace admin) exporte désormais la base via
`pg_dump` dans un fichier `.sql` horodaté, dans `sauvegardes/`. Les
outils clients PostgreSQL (`pg_dump`) doivent être installés sur le
serveur (`apt install postgresql-client` sous Debian/Ubuntu, ou installés
avec le serveur PostgreSQL lui-même).

### 5. Interface modernisée
- Cartes à coins arrondis et ombres douces (tableaux, formulaires,
  statistiques) au lieu de blocs plats.
- Menu mobile en tiroir fluide, avec calque d'arrière-plan flouté.
- Micro-animations : survol des boutons (légère élévation), lignes de
  tableau surlignées au survol, focus des champs mis en valeur.
- **Notifications toast** : les messages de succès/erreur apparaissent en
  haut à droite, glissent à l'écran, et disparaissent automatiquement
  (les erreurs restent affichées plus longtemps) — remplace les bandeaux
  fixes du haut de page.
- Boutons et champs agrandis sur mobile/tablette pour un usage tactile
  confortable (espace profs, saisie des notes, T1/T2/T3...).

## 📈 Passage à l'échelle (5000+ élèves, 50+ connexions simultanées)

- **Bug de performance corrigé** : le moteur de calcul (moyennes, rangs,
  bulletins) faisait auparavant une requête par élève × par matière × par
  autre élève de la classe pour calculer un simple classement — invivable
  au-delà de quelques dizaines d'élèves (des dizaines de milliers de
  requêtes pour une seule fiche). Il calcule maintenant tout en mémoire à
  partir de 2-3 requêtes groupées par classe/trimestre, avec un cache le
  temps d'une page (`flask.g`) pour ne jamais refaire deux fois le même
  calcul sur une même page.
- **Bug de fiabilité corrigé au passage** : les dates (jj/mm/aaaa) étaient
  comparées comme du texte brut dans certains calculs d'absences, ce qui
  peut donner un ordre chronologique faux (ex. "05/01/2026" < "16/09/2025"
  en comparaison de texte, alors que janvier 2026 est bien après). Les
  comparaisons de dates utilisent désormais un vrai parsing chronologique.
- **Index de base de données** : toutes les clés étrangères (classe_id,
  eleve_id, affectation_id, trimestre_id...) sont indexées. Si tu as déjà
  des données que tu ne veux pas perdre, lance `python migrer_index.py`
  après cette mise à jour (ajoute les index sans rien supprimer) — sinon
  `init_db.py`/`init_db_production.py` les créent directement.
- **Pool de connexions PostgreSQL** dimensionné pour ~50 utilisateurs
  simultanés (20 connexions prêtes + 30 en pic).
- **Serveur de production** : le serveur intégré de Flask (`python app.py`)
  reste pratique pour tester, mais n'est pas fait pour beaucoup de
  connexions à la fois. Pour un usage réel avec plusieurs dizaines de
  professeurs connectés en même temps, lance plutôt :
  ```
  waitress-serve --host=0.0.0.0 --port=5000 --threads=16 app:app
  ```
  (inclus dans `requirements.txt`).
- **Liste des élèves paginée** (100 par page) avec filtre par classe et
  recherche par nom/prénom/matricule — afficher 5000 lignes d'un coup
  dans un tableau aurait été lent, surtout sur mobile.

## ⚠️ Mise à jour importante (précédente)

Le schéma de la base de données a changé (3 nouvelles tables : frais de
scolarité, échéancier, paiements). Relance `python init_db.py` (ou
`init_db_production.py`) sur ta base PostgreSQL avant de tester, sinon
l'application plantera au démarrage.

## Vérification d'authenticité d'un reçu

Nouvelle page **Vérifier un reçu** (menu Pédagogie / Consultation) :
saisis un numéro de reçu et l'application indique s'il correspond à un
paiement réellement enregistré (élève, classe, montant, date) ou s'il
est introuvable — pratique pour contrôler un reçu présenté par un élève
ou un parent. Le numéro de reçu n'est modifiable nulle part dans
l'application (attribué une seule fois, automatiquement), pour éviter
toute tentative de fraude.

## Numéro de reçu automatique &amp; statistiques de scolarité

Le numéro de reçu d'un paiement (format `REC-000001`, `REC-000002`...)
est désormais attribué automatiquement par l'application à chaque
versement — plus aucune saisie manuelle, et l'unicité est garantie même
après suppression d'un ancien paiement.

Nouvelle page **Statistiques scolarité** (menu Pédagogie / Consultation,
accessible aussi au directeur, au censeur et au chef d'établissement) :
montant total dû, payé et restant, **par classe** et **pour toutes les
classes combinées**, avec un graphique du taux de recouvrement par
classe.

## Module Scolarité (paiements par tranches)

Nouvelle page **Scolarité** (menu Pédagogie / Consultation) :
- Définis le **montant total** de la scolarité pour chaque classe et
  chaque année scolaire.
- Configure un **échéancier flexible** (nombre de tranches libre — 3, 4,
  ou plus), chaque tranche précisant son montant et à partir de quel
  trimestre elle est exigible.
- Enregistre les **paiements** de chaque élève (montant, date, n° de
  reçu).
- La **fiche de scolarité** d'un élève (accessible depuis la page Élèves)
  récapitule le statut de chaque tranche (Payée / Partiellement payée /
  Non payée) et indique clairement pour quel(s) trimestre(s) il est
  autorisé à retirer son bulletin.

**Blocage de l'impression** : si un élève n'est pas à jour pour le
trimestre demandé, l'impression du bulletin est bloquée avec le montant
restant à payer affiché — trimestre par trimestre (être à jour pour le
T1 ne suffit pas pour retirer le bulletin du T2 si la tranche du T2 n'est
pas encore soldée). L'administrateur peut forcer l'impression en
dérogation si besoin (action tracée dans l'Audit). L'impression par lot
d'une classe écarte automatiquement les élèves non à jour et les liste à
part, sans bloquer les autres. Si aucun montant de scolarité n'est
configuré pour une classe, rien n'est bloqué.

## Aucun professeur par défaut

`init_db.py` ne crée plus que la structure de base (établissement, une
classe, les matières, les trimestres, un élève d'exemple) et le compte
administrateur — plus aucun nom de professeur n'est préinstallé. Chaque
professeur doit être créé par l'administrateur (page Professeurs), avec
son propre identifiant et mot de passe.

## Matières modifiables et supprimables

Page **Matières & coefficients** : le nom, le coefficient par défaut et
le groupe d'une matière sont modifiables directement dans le tableau.
Une matière peut aussi être supprimée — bloqué automatiquement si elle
est déjà affectée à une classe (retire d'abord ses affectations).

## Tri alphabétique

Toutes les listes d'élèves (page Élèves, listes par classe, contacts,
pointage, saisie des notes, etc.) sont désormais triées par ordre
alphabétique (nom puis prénom).

## Module Bulletins

Nouvelle page **Bulletins** (menu Pédagogie / Consultation) : choisis une
classe et un trimestre, puis :
- **Par élève** : lien "Voir / Imprimer" pour chacun.
- **Par lot** : un bouton génère en un seul document tous les bulletins
  de la classe (saut de page automatique entre chaque élève), pratique
  pour tout imprimer ou exporter en PDF d'un coup.

## Menu en catégories repliables

Le menu latéral est maintenant organisé en catégories (Pédagogie,
Résultats, Organisation, Paramètres...) repliées par défaut : clique sur
le nom d'une catégorie pour dérouler ses pages. La catégorie contenant la
page actuelle s'ouvre automatiquement, et le navigateur se souvient de
tes catégories ouvertes d'une page à l'autre.

## Absence automatique des professeurs

Si un professeur avait un cours prévu à l'emploi du temps un jour donné
et n'a pointé AUCUN de ses élèves ce jour-là, il est marqué automatiquement
absent (non justifié) sur ce créneau dès que la journée est terminée. Le
motif affiché est *"Absence automatique : aucun pointage des élèves n'a
été effectué pour ce créneau."* — l'administration peut ensuite le
requalifier en justifié si besoin, comme n'importe quelle autre absence
(page Pointage des professeurs). Cette vérification tourne automatiquement
à chaque ouverture des pages de pointage/absences (30 derniers jours),
sans réglage à faire.

## Module Vérification des moyennes

Page **Vérification des moyennes** (menu Résultats) : fiche imprimable
par classe et par trimestre, avec toutes les matières en colonnes
(moyenne et moyenne×coefficient), le total de points, la moyenne
trimestrielle et le rang de chaque élève. Pour le 3e trimestre, un
second bouton imprime en plus la **fiche de vérification de la moyenne
générale annuelle** (rappel T1/T2/T3, moyenne annuelle, rang annuel).

## Contact parent à l'inscription

Le formulaire d'ajout d'un élève (page Élèves) demande maintenant aussi
le contact d'un parent (nom, fonction, téléphone) dès l'inscription. Pour
ajouter un second contact (ex. père et mère), utilise la page Contact
Parents.

## Module Archives

Page **Archives** (menu Organisation) : avant de faire passer les élèves
dans la classe supérieure ou de changer les affectations/coefficients
pour une nouvelle année, clique sur **Archiver cette année** (en
choisissant l'année scolaire concernée). Cela génère et fige une copie
de tous les bulletins (chaque élève × chaque trimestre) et de toutes les
listes de classe de cette année. Une fois archivés, ces documents restent
consultables et imprimables tels quels, même après avoir modifié les
données pour la nouvelle année scolaire. Relancer l'archivage sur une
même année remplace le contenu précédent (utile après une correction de
notes). Le portail Direction peut consulter les archives, seul l'admin
peut archiver ou supprimer une archive.

## Portail Direction

Depuis la page **Direction** (menu admin), crée un compte pour le
Directeur, le Censeur et/ou le Chef d'établissement (nom, fonction,
identifiant, mot de passe). Ces comptes donnent accès à un portail de
consultation en lecture seule : statistiques, moyennes par matière,
listes par classe, bulletins, absences — aucune modification de données
n'y est possible. Les identifiants sont modifiables à tout moment par
l'administrateur (bouton « Identifiants » sur la page Direction).

## Installation (sur l'ordinateur qui servira de serveur)

1. Installer Python 3.10+ et PostgreSQL.
2. Créer la base : `createdb gestion_scolaire`
   (ou `psql -U postgres -c "CREATE DATABASE gestion_scolaire;"`)
3. Ouvrir un terminal dans ce dossier et installer les dépendances :
   ```
   pip install -r requirements.txt
   ```
4. Initialiser les tables :
   - **Pour tester tout de suite** avec des données d'exemple (reprend le
     modèle DIARRA ADJARA) :
     ```
     python init_db.py
     ```
   - **Pour une mise en service réelle**, base vide sans aucune donnée de
     démonstration (juste le compte admin) :
     ```
     python init_db_production.py
     ```
5. Lancer le serveur :
   ```
   python app.py
   ```
6. Ouvrir `http://localhost:5000` sur l'ordinateur serveur, ou
   `http://<adresse-ip-du-serveur>:5000` depuis un autre appareil
   connecté au même Wi-Fi de l'établissement.

## Comptes de démonstration (créés par init_db.py)

- **Administrateur** : `admin` / `admin123`
- **Professeur** (ex. Mr Moctar) : `prof.moctar` / `motdepasse123`
  (un compte est créé pour chaque professeur de l'exemple)

⚠️ À changer avant toute mise en service réelle (voir aussi `SECRET_KEY`
dans `app/__init__.py`).

## Structure du projet

```
app.py                 -> point d'entrée (lance le serveur)
init_db.py              -> crée la base + données de démonstration
requirements.txt
app/
  models.py              -> les 11 tables du cahier des charges
  calculs.py             -> moteur de calcul (moyennes, rangs, conduite, sanctions)
  auth.py                 -> connexion + contrôle des rôles admin/professeur
  routes_auth.py           -> connexion / déconnexion
  routes_admin.py          -> classes, matières, professeurs, élèves, calendrier, audit, sauvegarde USB
  routes_professeur.py      -> saisie des notes, pointage des absences
  routes_bulletin.py        -> prévisualisation du bulletin (calculs + rendu)
  templates/
    bulletin.html            -> le bulletin A4 (déjà validé avec toi)
    admin/ , professeur/      -> pages de gestion
  static/style.css
```

## Ce qui est déjà fonctionnel

- Base de données complète (11 entités du cahier des charges, section 3).
- Rôles admin / professeur avec contrôle d'accès strict par décorateurs.
- Gestion complète des professeurs par l'admin : création (nom + identifiants),
  modification du nom, réinitialisation identifiant/mot de passe (en cas
  d'oubli), suppression (bloquée si des notes existent déjà pour éviter
  toute perte de données — réaffecte plutôt la matière à un autre professeur).
- Moteur de calcul : moyenne pondérée par matière, classement avec
  gestion des ex æquo et genre (1er/1ère), conduite automatique sur 16,
  sanctions et distinctions selon les seuils définis.
- Génération du bulletin A4 à partir des vraies données (notes, absences,
  classement), avec le bloc "Bilan de fin d'année" qui n'apparaît qu'au T3.
- Sauvegarde de la base en un clic (module admin), enregistrée directement
  dans le dossier `sauvegardes/` du projet.
- Journal d'audit des modifications de notes.

## Limites connues à ce stade (à finaliser ensemble)

- Les pages d'administration sont fonctionnelles mais simples (pas encore
  de suppression/modification des enregistrements, seulement la création).
- Le calcul de la moyenne annuelle (T3) doit encore relire automatiquement
  les moyennes du T1 et du T2 réellement enregistrées.
- Pas encore d'upload de logo/photo depuis l'interface (les champs existent
  en base, mais pas encore le formulaire d'envoi de fichier).
- Cette version n'a pas pu être testée en conditions réelles dans cet
  environnement (pas d'accès internet ici pour installer Flask-SQLAlchemy) ;
  la syntaxe Python et les templates ont été vérifiés, mais teste bien le
  lancement chez toi avec `python init_db.py` puis `python app.py` et
  dis-moi si une erreur apparaît.

## Prochaine étape suggérée

Le module de saisie des notes (côté professeur) — vérifier ensemble que
le flux de saisie (0 à 20, verrouillage hors des dates du trimestre,
messages d'erreur) correspond à ce que veulent tes enseignants.
