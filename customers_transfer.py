#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import re
import pandas as pd
from dbfread import DBF
####################### LES PATHS NE SONT PAS CONFIGURES
DBF_DIR = Path(r"C:\Users\zenleis\Downloads\test\@CIE@EBS") # replacez le par votre path 
DBF_FILE = DBF_DIR / "EBS_CSF.DBF"
OUT_FILE = Path(r"C:\Users\zenleis\Documents\GitHub\Interview_beone\customers_odoo_contacts_template_CLEAN.csv")
ISSUES_CSV = Path(r"C:\Users\zenleis\Documents\GitHub\Interview_beone\customers_odoo_contacts_VAT_ISSUES.csv")

def get_country_code(country: str) -> str:
    """Traduit le nom complet d'un pays en son code ISO à deux lettres."""
    country = (country or "").strip().upper()
    COUNTRY_MAP = {
        "BELGIUM": "BE", "BELGIQUE": "BE", "BELGIE": "BE", "PAYS-BAS": "NL",
        "NETHERLANDS": "NL", "LUXEMBOURG": "LU", "FRANCE": "FR", "IRELAND": "IE",
        "EU": "BE",
    }
    return COUNTRY_MAP.get(country, country if len(country) == 2 else "")

def digits(s: str) -> str:
    """Extrait uniquement les caractères numériques d'une chaîne de caractères."""
    return re.sub(r"\D", "", s or "")

def sanitize_external_id(name: str) -> str:
    """Nettoie une chaîne de caractères pour la rendre utilisable comme ID externe."""
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', name or "")

def be_checksum_ok(v10: str) -> bool:
    """Vérifie la validité d'un numéro de TVA belge grâce à sa somme de contrôle."""
    if not v10.isdigit() or len(v10) != 10: return False
    body, check = int(v10[:-2]), int(v10[-2:])
    return (97 - (body % 97)) == check

def format_vat(vat_raw: str, country_code: str) -> str:
    """Formate un numéro de TVA en fonction de son code pays et retourne une chaîne vide s'il est invalide."""
    vat = (vat_raw or "").strip().upper()
    if not vat: return ""

    if country_code == "BE":
        d = digits(vat)
        if len(d) == 9: d = "0" + d
        return f"BE{d}" if be_checksum_ok(d) else ""

    if country_code == "IE":
        clean_vat = "IE" + "".join(filter(str.isalnum, vat))
        if re.match(r"IE\d{7}[A-Z]{1,2}$", clean_vat):
            return clean_vat
        return ""

    if country_code == "NL":
        nl_match = re.match(r"(?:NL)?(\d{9}B\d{2})", vat)
        return f"NL{nl_match.group(1)}" if nl_match else ""

    if country_code:
        return country_code + digits(vat)
        
    return ""

print(f"📥 Chargement de {DBF_FILE} ...")
if not DBF_FILE.exists(): raise SystemExit(f"Fichier DBF introuvable: {DBF_FILE}")

tbl = DBF(str(DBF_FILE), encoding="latin-1", char_decode_errors='ignore')
raw = pd.DataFrame(iter(tbl))
raw.columns = [c.strip().upper() for c in raw.columns]

def pick(cols):
    """Sélectionne la première colonne existante dans le DataFrame."""
    for n in cols:
        if n in raw.columns: return raw[n].astype(str).str.strip()
    return pd.Series([""] * len(raw))

contacts = pd.DataFrame({
    "id": "beone_winbooks_partner_" + pick(["NUMBER"]).apply(sanitize_external_id),
    "Name*": pick(["NAME1"]),
    "Company Type*": pick(["VATNUMBER"]).apply(lambda v: "Company" if v else "Person"),
    "Email": pick(["EREMINDERS"]),
    "Phone": pick(["TELNUMBER"]),
    "Street": pick(["ADRESS1"]),
    "Street2": pick(["ADRESS2"]),
    "City": pick(["CITY"]),
    "Zip": pick(["ZIPCODE"]),
    "Country": pick(["COUNTRY"]).apply(get_country_code),
    "Tax ID": pick(["VATNUMBER"]),
    "Notes": "",
})

issues = []
for i, row in contacts.iterrows():
    vat_raw = row["Tax ID"]
    country_code = row["Country"]
    
    if re.match(r"(?:IE)?\d{7}[A-Z]{1,2}", (vat_raw or "").upper()):
        country_code = "IE"
    elif re.match(r"(?:NL)?\d{9}B\d{2}", (vat_raw or "").upper()):
        country_code = "NL"
    
    contacts.loc[i, "Country"] = country_code
    
    clean_vat = format_vat(vat_raw, country_code)
    contacts.loc[i, "Tax ID"] = clean_vat

    if row["Company Type*"] == "Company" and not clean_vat:
        contacts.loc[i, "Company Type*"] = "Person"
        contacts.loc[i, "Notes"] = f"TVA originale '{vat_raw}' invalide. Changé en Personne."
        issues.append({
            "Name": row["Name*"],
            "Original VAT": vat_raw,
            "Issue": "TVA invalide, changé en Personne"
        })

mask_missing_name = contacts["Name*"].eq("")
contacts.loc[mask_missing_name, "Name*"] = "Partenaire sans nom " + contacts.loc[mask_missing_name, "id"]

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
contacts.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
pd.DataFrame(issues).to_csv(ISSUES_CSV, index=False, encoding="utf-8-sig")

print(f"✅ Contacts exportés (version finale): {OUT_FILE}")
print(f"📝 Problèmes enregistrés: {ISSUES_CSV}")