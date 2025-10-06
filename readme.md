
---

# 🧾 Scripts de Migration de Données de Winbooks vers Odoo

Ce dépôt contient un ensemble de **scripts Python** conçus pour faciliter la **migration des données comptables** d’un système **Winbooks** (utilisant des fichiers `.dbf`) vers **Odoo**.
Les scripts gèrent l’extraction, la transformation et le formatage des **comptes**, **clients** et **écritures de journal**.

---

## ⚠️ Avertissement 🤖

Une partie importante du code de ce dépôt a été **générée avec l’aide d’une IA**.
---

## 🔍 Aperçu

L’objectif de ces scripts est d’automatiser le processus complexe de **transfert de données financières**.
Ils lisent les fichiers `.dbf` propriétaires, nettoient les données, valident les écritures et les convertissent en fichiers **CSV** formatés pour une importation transparente dans **Odoo**.

### Les quatre scripts principaux :

1. **`dbf_read.py`** – Outil d’inspection initial pour explorer le contenu des fichiers `.dbf`
2. **`accounts_transfer.py`** – Migration du plan comptable
3. **`customers_transfer.py`** – Migration des clients et fournisseurs
4. **`journal_transfer.py`** – Migration des écritures du journal comptable

---

## 🧩 Description des Scripts

### 1. `dbf_read.py`

**Objectif :** Reconnaissance initiale de tous les fichiers `.dbf` dans le répertoire source.
**Fonctionnalités :**

* Itère à travers tous les fichiers `.dbf` dans le dossier spécifié
* Lit chaque fichier et liste ses **colonnes** et le **nombre total de lignes**
* Fournit un **aperçu des premières lignes de données**
* Enregistre la sortie complète dans `dbf_inspect_output.txt` pour analyse

---

### 2. `accounts_transfer.py`

**Objectif :** Préparer le **plan comptable** pour l’importation dans Odoo.
**Fonctionnalités :**

* Charge les données du plan comptable depuis `EBS_ACF.DBF`
* Exclut une liste prédéfinie de **comptes standards protégés** d’Odoo
* Attribue le bon **`account_type`** selon le préfixe du code de compte
* Génère un **ID externe unique** (`id`) pour chaque compte
* Exporte les données vers `accounts_odoo_final_filtered.csv`

---

### 3. `customers_transfer.py`

**Objectif :** Migrer les **contacts clients et fournisseurs**.
**Fonctionnalités :**

* Charge les données depuis `EBS_CSF.DBF`
* Nettoie et formate les champs critiques (téléphone, pays, adresse)
* Valide et formate les **numéros de TVA** selon le pays (BE, IE, NL, etc.)
* Définit automatiquement le **Type de Société** sur *Particulier* si la TVA est invalide
* Génère un **ID externe unique** (`beone_winbooks_partner_...`)
* Exporte les contacts vers `customers_odoo_contacts_template_CLEAN.csv`
* Journalise les problèmes de TVA dans `customers_odoo_contacts_VAT_ISSUES.csv`

---

### 4. `journal_transfer.py`

**Objectif :** Extraire, valider et formater les **écritures du journal comptable**.
**Fonctionnalités :**

* Charge les écritures depuis `EBS_ACT.DBF`
* Crée un fichier `journals_to_create.csv` pour générer les journaux dans Odoo
* Lie les postes de journal aux **partenaires migrés** via leur ID externe
* **Validation Phase 1 :** Filtre les partenaires sans activité nette
* **Validation Phase 2 :** Vérifie l’équilibre des écritures (débits = crédits)
* Exporte les écritures valides vers `entries_odoo_final_balanced.csv`
* Enregistre les écritures non équilibrées dans `entries_odoo_UNBALANCED.csv`

---

## ⚙️ Configuration Requise

> ⚠️ Les chemins de fichiers (`DBF_DIR`, `OUT_FILE`, etc.) dans les scripts sont **exemples** et doivent être adaptés à votre environnement local.

---

## 🚀 Comment Utiliser

### 1. Configuration

Ouvrez chaque script `.py` et mettez à jour les chemins de fichiers selon votre environnement.

### 2. Dépendances

Installez les bibliothèques Python nécessaires :

```bash
pip install dbfread pandas python-dateutil numpy
```

### 3. Ordre d’Exécution

Exécutez les scripts dans cet ordre :

```bash
python dbf_read.py          # (Optionnel) Inspection initiale
python accounts_transfer.py
python customers_transfer.py
python journal_transfer.py
```

### 4. Importation dans Odoo

Utilisez les fichiers CSV générés (`accounts_...`, `customers_...`, `journals_...`, `entries_...`) pour importer les données via l’outil d’importation intégré d’Odoo.

---

