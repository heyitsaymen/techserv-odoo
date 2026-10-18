# TechServ – Gestion des interventions (Odoo 19 Community)

Épreuve pratique « TechServ » : installation et dépannage de climatiseurs, groupes
électrogènes et pompes chez les clients.

**Principe directeur : partir du standard Odoo et l'étendre**, sans jamais modifier le
code d'Odoo. Pour chaque besoin, j'ai suivi le même ordre de décision :

1. ça existe déjà en standard → je l'utilise tel quel ;
2. ça se configure (étapes, séquences, modèles d'e-mail, règles automatisées) → je le livre en XML ;
3. il manque un peu → j'étends un modèle existant (`_inherit`) ;
4. rien ne correspond → seulement là, je crée un modèle.

Résultat : **un seul nouveau modèle métier** (`techserv.intervention.part`, les pièces
utilisées), plus trois assistants (modèles transitoires).

---

## 1. Architecture

| Module | Rôle | Dépendances |
|---|---|---|
| `techserv_intervention` | Exercices 1 à 4 | `maintenance`, `hr`, `hr_hourly_cost`, `hr_fleet`, `hr_skills`, `product`, `sale_management`, `account`, `stock`, `mail`, `base_automation` |
| `techserv_portal` | Bonus : portail client (consultation et signature en ligne) | `techserv_intervention`, `portal` |

Le portail est un module séparé pour rester **optionnel** : un client qui n'en veut pas ne
l'installe pas.

### Correspondance concept métier → modèle Odoo

| Concept du sujet | Modèle utilisé | Ce qui est ajouté |
|---|---|---|
| Équipement client | `maintenance.equipment` **étendu** | `customer_id` (le `partner_id` standard est le **fournisseur**), `product_id`, `is_under_warranty` (calculé) |
| Intervention | `maintenance.request` **étendu** | référence (`ir.sequence`), client, état technique, vente d'origine, facture, temps passé, pièces, signature |
| Étapes | `maintenance.stage` **livrées en XML** | champ `techserv_state` pour ne pas dépendre des libellés |
| Technicien | `hr.employee` lié à `res.users` | rien : coût horaire (`hr_hourly_cost`), véhicule (`hr_fleet`), certifications (`hr_skills`) sont standard |
| Pièces utilisées | `techserv.intervention.part` (**nouveau**) + `stock.picking` standard | voir « Pourquoi un nouveau modèle » ci-dessous |
| Facture | `account.move` standard | lien intervention ↔ facture, références sur la facture imprimée |

**Alternatives envisagées et écartées :**

- **`repair.order` (module Réparation)** : orienté atelier (le produit vient chez nous), avec sa
  propre logique de garantie qui *n'impute pas les pièces*, alors que TechServ facture les
  pièces et offre la main-d'œuvre sous garantie : c'est l'inverse du besoin.
- **Field Service (`industry_fsm`)** : idéal fonctionnellement, mais c'est un module
  **Enterprise**, non disponible en Community.
- **Modèles entièrement nouveaux** (`techserv.equipment`, `techserv.intervention`…) : on perdrait
  le chatter, le kanban par étape, le calendrier, les activités, les statistiques MTBF/MTTR, les
  équipes de maintenance… qu'il faudrait recoder et maintenir à chaque version.

**Pourquoi un nouveau modèle pour les pièces ?** Les techniciens ne sont pas utilisateurs de
l'Inventaire : ils n'ont pas le droit de lire `stock.picking` / `stock.move`. La ligne de pièce
« métier » est lisible par le technicien, le portail, le bon d'intervention et la facturation,
et garde un lien (`move_id`) vers le mouvement de stock standard, qui reste la vérité côté stock.

---

## 2. Installation

### Avec Docker (recommandé pour la correction)

```bash
docker compose up -d
# Base neuve avec données de démonstration et les deux modules :
docker compose run --rm odoo odoo -d techserv --with-demo \
    -i techserv_intervention,techserv_portal --stop-after-init
docker compose restart odoo
```

Puis ouvrir <http://localhost:8069> (base `techserv`, utilisateur `admin` / mot de passe `admin`).

### Sur une installation Odoo existante

1. Copier les dossiers `techserv_intervention` et `techserv_portal` dans un dossier d'addons.
2. Ajouter ce dossier à l'`addons_path` (ou le passer en option `--addons-path`).
3. Mettre à jour la liste des applications puis installer **TechServ - Interventions**
   (et **TechServ - Customer Portal** pour le bonus).

### Lancer les tests

```bash
odoo -d techserv_test --with-demo -i techserv_intervention,techserv_portal \
     --test-enable --test-tags /techserv_intervention,/techserv_portal --stop-after-init
```

Avec Docker :

```bash
docker compose run --rm odoo odoo -d techserv_test -i techserv_intervention,techserv_portal \
    --test-enable --test-tags /techserv_intervention,/techserv_portal --stop-after-init
```

### Comptes de démonstration

| Identifiant | Mot de passe | Profil |
|---|---|---|
| `admin` | `admin` | Administrateur (Responsable TechServ) |
| `responsable` | `techserv` | Responsable TechServ, sociétés Alger et Oran |
| `technicien1`, `technicien2` | `techserv` | Techniciens (TechServ Alger) |
| `technicien.oran` | `techserv` | Technicienne (TechServ Oran) |
| `client` | `techserv` | Utilisateur **portail** de la Clinique Les Oliviers (bonus : `/my/interventions`) |

> Astuce : si une autre base Odoo tourne sur la même machine (même adresse, autre port), le
> navigateur partage le cookie de session entre les deux et la connexion échoue (« Session
> expired »). Utiliser une fenêtre privée ou le nom d'hôte de la machine plutôt que son IP.

### Apparence (optionnel)

En Community, le sélecteur d'applications est une liste. Pour retrouver une grille d'icônes
(comme en Enterprise), on peut ajouter le module OCA **`web_responsive`**
(<https://github.com/OCA/web>). Il n'est volontairement **pas** une dépendance des modules
TechServ : ils fonctionnent sur un Odoo 19 Community standard.

---

## 3. Utilisation

- **Application TechServ** : icône *TechServ* sur l'écran d'accueil (Interventions, Planning, Parc client, Facturer les interventions, Configuration) ; ce sont des raccourcis vers les écrans standard de Maintenance.
- **Parc client** : *TechServ > Parc client* (ou *Maintenance > Équipements*). Filtres « Sous garantie » / « Garantie expirée »,
  regroupement par client, onglet *Interventions* (historique) et bouton **Nouvelle intervention**.
- **Interventions** : *Maintenance > Maintenance > Demandes de maintenance* (kanban par étape,
  liste, calendrier). La référence `INT/AAAA/NNNNN` est cherchable directement.
- **Planification groupée** : dans la liste, sélectionner des demandes → *Action > Attribuer à un
  technicien* : technicien, heure de départ ; les créneaux s'enchaînent (les plus urgentes d'abord).
- **Démarrer / Clôturer** : boutons sur l'intervention. La clôture demande le temps passé, les
  pièces et la **signature** du client ; elle crée et valide le bon de sortie de stock.
- **Facturation** : *Maintenance > Maintenance > Facturer les interventions* (ou *Action* depuis
  la liste) : une facture par intervention ou par client.
- **Bon d'intervention** : *Imprimer > Bon d'intervention* sur l'intervention.
- **Ventes** : cocher « Crée une intervention » sur un produit (ex. *Installation de
  climatiseur*) ; à la confirmation du devis, l'intervention est créée et l'équipe est prévenue.
- **Contacts** : boutons *Équipements* / *Interventions* sur la fiche, filtre « A des équipements ».
- **Portail** (module bonus) : le client voit *Interventions* dans son espace, télécharge le bon
  et signe en ligne une intervention planifiée ou en cours.

### Import Excel du parc (Exercice 3.4)

On utilise **l'import standard d'Odoo**, rien n'est codé :

1. *Maintenance > Équipements*, vue liste, menu ⚙ (*Actions*) > **Importer des enregistrements**.
2. Le lien **« Import Template for Customer Equipment »** télécharge le modèle
   `techserv_intervention/static/import/equipment_import_template.xlsx`.
3. Charger le fichier Excel ; les colonnes sont reconnues automatiquement (nom technique des champs).
4. Cliquer sur **Tester** : Odoo simule l'import et **liste les lignes en erreur** (client
   inconnu, date invalide, numéro de série en double…) sans rien enregistrer.
5. Corriger le fichier, retester, puis **Importer**.

Le fichier `equipment_import_example_with_errors.xlsx` contient volontairement 3 erreurs pour
voir le fonctionnement du bouton *Tester*.

---

## 4. Besoin → Solution → Pourquoi → Alternative écartée

### Exercice 1 – Le parc client et les interventions

| # | Besoin | Solution | Pourquoi | Alternative écartée |
|---|---|---|---|---|
| 1.1 | Équipements par client : produit, n° de série, date d'installation, garantie ; n° de série unique | `maintenance.equipment` étendu : `customer_id`, `product_id`. Réutilisation de `serial_no`, `effective_date` (renommée « Date d'installation »), `warranty_date`. **Unicité : contrainte SQL déjà présente en standard** (`_serial_no = models.Constraint('unique(serial_no)')`), testée | Aucun champ dupliqué ; une contrainte SQL est garantie par la base, même en import massif ou en accès concurrent | Champ `partner_id` standard : c'est le *fournisseur*, le détourner casserait sa sémantique. Contrainte Python : contournable en cas d'accès concurrent |
| 1.2 | Référence unique donnée au téléphone ; étapes reçue → planifiée → en cours → terminée → facturée ; annulation tant que le technicien n'est pas parti | `ir.sequence` `INT/%(year)s/` (+ contrainte `unique(reference)`, `_rec_names_search`) ; 6 étapes `maintenance.stage` en XML (les 4 standard réutilisées et renommées + Planifiée, Facturée) avec un `techserv_state` ; contrôle dans `write()` : annulation refusée dès « En cours » | La règle porte sur l'état technique, pas sur le libellé (renommable / traduisible) ; le contrôle dans `write()` couvre tous les chemins (bouton, barre d'étapes, glisser-déposer kanban, import, RPC) | Champ `state` Selection en dur : doublon avec les étapes, plus de kanban configurable. Contrôle dans le bouton seulement : contournable |
| 1.3 | Retrouver les équipements sous garantie ; historique des interventions | Champ calculé **non stocké** `is_under_warranty` + méthode `search=` + filtres ; historique : smart button standard (demandes) + onglet *Interventions* ajouté | La valeur dépend de la date du jour : stockée, elle serait fausse le lendemain sans recalcul. La méthode `search=` la rend filtrable quand même | Champ stocké + cron quotidien de recalcul : plus lourd et faux entre deux passages |
| 1.4 | Technicien jamais à deux endroits ; pas de suppression d'une intervention commencée ; traçabilité | `@api.constrains` sur `user_id`/`schedule_date`/`schedule_end` (la date de fin `schedule_end` est **déjà stockée en standard**), annulées ignorées ; `@api.ondelete(at_uninstall=False)` ; `tracking=True` sur les champs ajoutés et clés | Chevauchement = comparaison d'intervalles entre lignes : impossible en contrainte SQL simple. `@api.ondelete` est la façon Odoo de bloquer une suppression sans casser la désinstallation | Surcharger `unlink()` : bloquerait aussi la désinstallation du module. Champ de fin recalculé à la main : le standard l'a déjà |
| 1.5 | Techniciens : coût horaire, véhicule, certifications, et contacts sans double saisie | **Uniquement du standard** : `hr.employee` lié à `res.users` (contact de travail = partenaire de l'utilisateur), `hr_hourly_cost`, `hr_fleet` (conducteur du véhicule), `hr_skills` (type de compétence « certification » avec dates de validité, livré en données). Sur l'intervention : le technicien reste `user_id`, son téléphone est lu sur sa fiche employé | Zéro duplication : l'adresse et le téléphone sont saisis une seule fois sur l'employé | Modèle `techserv.technician` ou `techserv.certification` : réinventerait RH / Flotte / Compétences. Champ Many2one véhicule ajouté : `hr_fleet` gère déjà l'affectation et son historique |

### Exercice 2 – Ventes, contacts, comptabilité

| # | Besoin | Solution | Pourquoi | Alternative écartée |
|---|---|---|---|---|
| 2.1 | Équipe technique prévenue à la confirmation du devis, sans changer la vente | Case `create_intervention` sur `product.template` ; surcharge de `sale.order.action_confirm()` qui appelle **`super()` d'abord**, puis crée une intervention par ligne concernée et une **activité** pour les membres de l'équipe de maintenance (ou les responsables) ; pas de doublon si le devis est reconfirmé | Le flux de vente reste strictement le standard. La création passe par `sudo()` limité (comme `sale_project` pour les tâches) : le commercial n'a pas à avoir les droits Maintenance ; il est abonné pour garder la visibilité | Règle automatisée sur `sale.order` : moins lisible pour créer des enregistrements liés ligne par ligne. Nouveau bouton « Créer l'intervention » : change la façon de travailler du commercial |
| 2.2 | Nombre d'équipements / d'interventions sur le client et la commande, accès en un clic | Smart buttons + compteurs **non stockés** sur `res.partner` (avec `child_of` : une société voit ses contacts) et `sale.order` | Un compteur non stocké est toujours exact et ne coûte qu'à l'affichage de la fiche | Compteur stocké : recalculs à chaque modification d'intervention, risque de désynchronisation |
| 2.3 | Filtrer les contacts qui ont des équipements | One2many `equipment_ids` sur `res.partner` + filtre `[('equipment_ids', '!=', False)]` | Un One2many est cherchable ; un compteur non stocké ne l'est pas | Compteur stocké uniquement pour filtrer : redondant |
| 2.4 | Référence d'intervention et n° de série sur la facture imprimée | Héritage QWeb de `account.report_invoice_document` par `xpath` : tableau Intervention / Équipement / N° de série sous le bloc d'informations ; les lignes de facture reprennent aussi la référence et le n° de série (section) | Le template standard n'est jamais modifié ; `sudo()` dans le template : la comptable imprime même sans accès aux interventions | Copier le template de facture : perdrait les évolutions et corrections d'Odoo |
| 2.5 | Bon d'intervention signé, en PDF aux couleurs de la société | Rapport QWeb `ir.actions.report` basé sur **`web.external_layout`** (logo, couleurs, en-tête / pied de page de la société), avec temps passé, pièces et signature | Le style suit le paramétrage *Mise en page des documents* de chaque société, sans code | Mise en page HTML/CSS spécifique : à maintenir, et ne suit pas le multi-société |

### Exercice 3 – Le quotidien

| # | Besoin | Solution | Pourquoi | Alternative écartée |
|---|---|---|---|---|
| 3.1 | Attribuer plusieurs demandes d'un coup à un technicien, à partir d'une heure | Assistant (TransientModel) lié au menu *Action* de la liste (`binding_model_id`) : créneaux enchaînés selon la durée (valeur par défaut sinon), priorité d'abord, passage à « Planifiée ». **Notification : l'activité standard de Maintenance** créée par `write()` dès qu'on renseigne technicien + date | Réutilise le mécanisme d'activité et d'abonnement du standard ; la contrainte de chevauchement s'applique à chaque écriture (tout ou rien) | Édition en masse de la liste : pas de calcul de créneaux. Activité codée à la main : doublon du standard |
| 3.2 | Clôture en une étape : temps passé, pièces, signature obligatoire ; sortie de stock | Assistant de clôture : `UserError` sans signature (et contrôle aussi dans `write()` si on force l'étape « Terminée ») ; lignes de pièces → `techserv.intervention.part` ; création et validation d'un **`stock.picking` de sortie standard** (type de sortie de l'entrepôt de la société) | Une seule action pour le technicien ; le stock est mouvementé par le mécanisme standard (traçabilité, valorisation). `sudo()` limité à la création du bon : le technicien n'est pas magasinier | Ajuster les quants directement : contourne la traçabilité de l'Inventaire. Laisser le magasinier saisir la sortie : double saisie |
| 3.3 | Facturation groupée ; main-d'œuvre gratuite sous garantie, pièces facturées | Assistant « une facture par intervention / par client (et société) » ; produit service *Main-d'œuvre* livré en données (quantité = temps passé) **omis si l'équipement est sous garantie à la date de l'intervention** (une ligne de note l'indique) ; pièces toujours facturées ; passage à « Facturée » + lien vers la facture | `account.move` standard : taxes, comptes, numérotation, envoi, paiement inchangés. La garantie est évaluée à la date de l'intervention, pas à la date de facturation | Facturer via un devis `sale.order` : étape inutile pour du dépannage. `repair.order` : logique de garantie inverse |
| 3.4 | Importer le parc Excel et voir les lignes en erreur avant | **Import standard d'Odoo** (bouton *Tester*), rien n'est codé ; modèle de fichier livré dans le module et proposé dans l'écran d'import (`get_import_templates`) | L'import standard sait déjà valider, mapper les colonnes et lister les erreurs | Assistant d'import spécifique : du code à maintenir pour refaire l'existant |
| 3.5 | Créer une intervention depuis l'équipement sans ressaisir | Bouton *Nouvelle intervention* : action avec contexte `default_equipment_id`, `default_customer_id`, `default_company_id` | Mécanisme standard des valeurs par défaut par contexte | Recopier les valeurs en Python après création : plus de code, moins lisible |

### Exercice 4 – Contrôle et fiabilité

| # | Besoin | Solution | Pourquoi | Alternative écartée |
|---|---|---|---|---|
| 4.1 | Le technicien ne voit que ses interventions, ne peut ni facturer, ni annuler, ni supprimer ; le responsable peut tout | Groupes **Technicien** et **Responsable** (le responsable implique le technicien, le responsable Maintenance et la facturation). **Règles globales** : le technicien ne voit / modifie que `user_id = lui`, et ne supprime rien. **Contrôles Python** : annuler, rouvrir, supprimer, facturer, planifier réservés au responsable (`AccessError`) | **Les droits Odoo sont cumulatifs** : Maintenance donne déjà lecture/écriture/création/suppression des demandes à *tous* les utilisateurs internes, et sa règle de groupe (créateur / abonné / technicien) s'additionne à toute règle de groupe ajoutée. Seules les règles **globales** (combinées en ET) peuvent restreindre ; leur domaine ne vise que « technicien sans être responsable ». Les boutons sont aussi masqués, mais ce n'est que du confort : la sécurité est côté serveur | Masquer les boutons seulement : contournable (RPC, kanban, import). Modifier la règle standard de Maintenance : toucherait tous les utilisateurs et serait écrasée/perdue aux mises à jour |
| 4.2 | Deux sociétés, chacune ses données | `company_id` présent partout (standard sur demandes, équipements, ventes, factures, stock ; `related` stocké sur les pièces) ; `_check_company_auto` + `check_company=True` sur les nouveaux liens ; règles multi-société **standard** conservées, règle ajoutée pour le nouveau modèle ; équipe de maintenance et entrepôt par société | Le standard couvre déjà l'essentiel : on le complète seulement là où on ajoute un modèle | Règles multi-société dupliquées sur les modèles standard : redondant |
| 4.3 | Alerte si une urgence n'est pas planifiée 24 h après sa création ; e-mail au client à la planification | Deux **règles automatisées** (`base_automation`) livrées en XML : « 24 h après création » (priorité urgente, état reçue) → activité d'alerte pour chaque responsable, sans doublon ; « changement d'étape » vers Planifiée → `mail.template` envoyé au client | Configurable sans code par un administrateur, le moteur gère la fenêtre de temps (chaque demande n'est traitée qu'une fois) ; testable en appelant la même recherche que la tâche planifiée | `ir.cron` + méthode Python : il faudrait gérer soi-même la fenêtre de temps et les doublons, et le paramétrage serait figé dans le code |
| 4.4 | Prouver que tout fonctionne après une mise à jour | 37 tests `TransactionCase` / `HttpCase` (32 + 5 pour le portail), `@tagged('post_install', '-at_install')` (liste ci-dessous) | `post_install` : les tests tournent quand tous les modules sont installés, comme en production | Tests manuels : non reproductibles |

### Bonus – Portail client (`techserv_portal`)

| Besoin | Solution | Pourquoi | Alternative écartée |
|---|---|---|---|
| Le client consulte ses interventions et signe le bon en ligne | `portal.mixin` ajouté à `maintenance.request` (URL portail, jeton de partage) ; contrôleur héritant de `CustomerPortal` (liste paginée, fiche, PDF, signature) ; **compteur** sur l'accueil du portail ; **composant standard `portal.signature_form`** (le même que la signature des devis) ; règle d'accès lecture pour le groupe Portail (`customer_id child_of` société du client) | Tout repose sur le portail standard : sécurité (`_document_check_access` : droits du client ou jeton), mise en page, chatter. La signature en ligne est reprise automatiquement par l'assistant de clôture du technicien | Page web spécifique avec son propre widget de signature : à sécuriser et maintenir soi-même |

---

## 5. Points techniques Odoo 19

Vérifiés directement dans le code source de la branche 19.0 :

- Contraintes SQL : attribut `models.Constraint(...)` (remplace `_sql_constraints`).
- Groupes : `res.groups.privilege` (`privilege_id`), `user_ids`, `implied_ids` ; actions : `group_ids`.
- Vues : `<list>`, attributs `invisible="..."` / `readonly="..."` (plus de `attrs` / `states`).
- Méthode `search=` d'un champ calculé : l'ORM transmet `('in', {valeurs})` et gère la négation
  si la méthode renvoie `NotImplemented`.
- Traductions : `self.env._("...")`.
- `stock.move` n'a plus de champ `name` ; `button_validate()` gère quantité / `picked`.
- `mail.template` : `use_default_to=False` est nécessaire pour que `partner_to` soit utilisé.
- Une nouvelle société n'a plus d'entrepôt automatiquement (hors tests) : il faut en créer un
  pour pouvoir clôturer avec des pièces (fait dans la démo pour TechServ Oran).

---

## 6. Tests automatisés

`techserv_intervention/tests/` et `techserv_portal/tests/` :

| Règle testée | Test |
|---|---|
| Unicité du n° de série | `test_equipment.test_serial_number_unique` |
| Recherche « sous garantie » (champ non stocké) | `test_equipment.test_under_warranty_search` |
| Chevauchement technicien (annulées ignorées) | `test_intervention.test_technician_overlap` |
| Suppression interdite après démarrage | `test_intervention.test_delete_forbidden_after_start` |
| Annulation interdite après démarrage (bouton et étape forcée) | `test_intervention.test_cancel_forbidden_after_start` |
| Clôture impossible sans signature | `test_wizards.TestCloseWizard.test_close_without_signature` |
| Sortie de stock à la clôture (par un technicien sans droits Inventaire) | `test_wizards.TestCloseWizard.test_close_creates_stock_exit` |
| Facturation sous garantie (pas de main-d'œuvre, pièces facturées) | `test_wizards.TestInvoiceWizard.test_invoice_under_warranty` |
| Facturation hors garantie | `test_wizards.TestInvoiceWizard.test_invoice_out_of_warranty` |
| Garantie évaluée à la date de l'intervention | `test_wizards.TestInvoiceWizard.test_warranty_checked_at_intervention_date` |
| Une facture par client / par intervention | `test_wizards.TestInvoiceWizard.test_grouping` |
| Attribution groupée (créneaux, activité du technicien, chevauchement) | `test_wizards.TestPlanWizard.*` |
| Intervention créée à la confirmation du devis | `test_sale.test_confirm_quotation_creates_intervention` |
| Isolement des données du technicien (`with_user`) | `test_security.test_technician_sees_only_his_interventions` |
| Technicien : ni annuler, ni supprimer, ni facturer, ni planifier | `test_security.test_technician_cannot_cancel_delete_or_invoice` |
| Multi-société | `test_security.test_multi_company` |
| Alerte 24 h (et absence de doublon) | `test_alerts.test_urgent_not_planned_after_24h` |
| E-mail au client à la planification | `test_alerts.test_email_customer_when_planned` |
| Bon d'intervention et facture imprimée | `test_reports.*` |
| Portail : isolement, pages, compteur, signature en ligne puis clôture | `techserv_portal/tests/test_portal.py` |

---

## 7. Limites et pistes d'amélioration

- Les libellés sont en anglais dans le code (convention Odoo) et traduits dans `i18n/fr.po`
  (activer le français dans *Paramètres > Langues*). Les aides des champs standard redéclarés
  gardent la traduction de leur module d'origine.
- Les demandes créées depuis une vente ne sont pas rattachées automatiquement à un équipement
  (pour une installation, l'équipement n'existe pas encore) : le planificateur le choisit.
- La 2ᵉ société de démonstration n'a pas de plan comptable : charger un plan comptable avant
  de facturer dans TechServ Oran.
- Pistes : planning visuel par technicien (vue Gantt, Enterprise), contrats de maintenance
  récurrents (maintenance préventive standard), géolocalisation des clients.
