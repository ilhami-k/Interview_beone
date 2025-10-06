#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dbfread import DBF
import pandas as pd
from pathlib import Path
from dateutil.parser import parse
import re
import csv
import numpy as np
###################LES PATHS NE SONT PAS CONFIGURES
# --- Configuration ---
DBF_DIR = Path(r"C:\Users\zenleis\Downloads\test\@CIE@EBS")
SRC_FILE = Path(DBF_DIR) / "EBS_ACT.dbf"
PARTNERS_CSV = Path("customers_odoo_contacts_template_CLEAN.csv")

# --- Noms des fichiers de sortie ---
JOURNALS_OUT_FILE = "journals_to_create.csv"
ENTRIES_OUT_FILE = "entries_odoo_final_balanced.csv"
UNBALANCED_FILE = "entries_odoo_UNBALANCED.csv"

def sanitize_external_id(name: str) -> str:
    """Nettoie une chaîne pour qu'elle soit utilisable comme ID externe."""
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', name or "")

def run_importer():
    """
    Exécute le processus d'importation avec la logique de validation correcte :
    1. Valide les partenaires en s'assurant que la somme de leurs débits/crédits est > 0.
    2. Filtre les écritures pour ne conserver que celles des partenaires valides.
    3. VALIDE que la somme des débits est égale à la somme des crédits pour chaque écriture.
    4. Arrondit et formate la sortie pour Odoo.
    """
    print(f"📥 Phase 1: Analyse de {SRC_FILE}...")
    if not SRC_FILE.exists():
        raise SystemExit(f"Fichier DBF introuvable: {SRC_FILE}")
    
    table = DBF(str(SRC_FILE), encoding="latin-1", char_decode_errors='ignore')
    df = pd.DataFrame(iter(table))
    df.columns = [c.strip().upper() for c in df.columns]

    # --- Phase 1: Création du fichier des journaux ---
    cleaned_journal_codes = df["DBKCODE"].astype(str).str.strip().str.upper()
    unique_journal_codes = cleaned_journal_codes.dropna().unique()
    unique_journal_codes = [code for code in unique_journal_codes if code]

    journals_df = pd.DataFrame({"name": unique_journal_codes, "code": unique_journal_codes, "type": "general"})
    journals_df.to_csv(JOURNALS_OUT_FILE, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    print(f"✅ Fichier de journaux '{JOURNALS_OUT_FILE}' créé.")
    
    # --- Phase 2: Préparation des données ---
    print("\n📥 Phase 2: Préparation des écritures comptables...")
    if not PARTNERS_CSV.exists():
        raise SystemExit(f"Fichier partenaires '{PARTNERS_CSV}' introuvable.")
        
    valid_partners_from_csv = pd.read_csv(PARTNERS_CSV)
    valid_partner_ids = set(valid_partners_from_csv['id'])

    entries = df.copy()
    
    entries['Reference'] = entries["DOCNUMBER"].astype(str).str.strip().str.upper()
    entries['Journal'] = entries["DBKCODE"].astype(str).str.strip().str.upper()
    entries['Account'] = entries["ACCOUNTGL"].astype(str).str.strip()
    entries['PartnerRaw'] = entries["ACCOUNTRP"].astype(str).str.strip()
    
    partner_id_raw = "beone_winbooks_partner_" + entries['PartnerRaw'].apply(sanitize_external_id)
    entries['Partner'] = partner_id_raw.where(partner_id_raw.isin(valid_partner_ids), "")

    entries['Date'] = entries["DATE"].apply(lambda s: parse(str(s)).date().isoformat() if s else None)
    entries['Label'] = entries["COMMENTEXT"].astype(str).str.strip()
    
    amt = pd.to_numeric(entries["AMOUNTEUR"], errors="coerce").fillna(0).abs()
    ispos = pd.to_numeric(entries['ISPOSITIVE'], errors='coerce').fillna(0).astype(bool)
    
    entries['Debit'] = np.where(ispos, amt, 0)
    entries['Credit'] = np.where(~ispos, amt, 0)

    entries.dropna(subset=['Reference'], inplace=True)
    entries = entries[entries['Reference'] != '']
    
    # --- Phase 3: Validation par partenaire ---
    print("\n⚙️ Phase 3: Validation de l'activité par partenaire...")
    
    # Ne considérer que les lignes qui ont un partenaire
    partner_entries = entries[entries['Partner'] != ''].copy()
    
    partner_totals = partner_entries.groupby('Partner').agg(TotalDebit=('Debit', 'sum'), TotalCredit=('Credit', 'sum')).reset_index()
    partner_totals['TotalActivity'] = partner_totals['TotalDebit'] + partner_totals['TotalCredit']
    
    # Identifier les partenaires avec une activité totale > 0
    valid_partners = partner_totals[partner_totals['TotalActivity'] > 0]['Partner']
    
    # Conserver toutes les lignes des partenaires valides, plus toutes les lignes qui n'ont pas de partenaire
    validated_entries = entries[entries['Partner'].isin(valid_partners) | (entries['Partner'] == '')].copy()
    
    # --- Phase 4: Validation de l'équilibre des écritures ---
    print("\n⚙️ Phase 4: Validation de l'équilibre sur les écritures filtrées...")

    balance_check = validated_entries.groupby('Reference').agg(TotalDebit=('Debit', 'sum'), TotalCredit=('Credit', 'sum')).reset_index()

    is_balanced_mask = np.isclose(balance_check['TotalDebit'], balance_check['TotalCredit'])
    balanced_refs = balance_check[is_balanced_mask]['Reference']
    
    balanced_df = validated_entries[validated_entries['Reference'].isin(balanced_refs)].copy()
    unbalanced_df = validated_entries[~validated_entries['Reference'].isin(balanced_refs)]

    # --- Phase 5: Arrondir et formater pour l'export ---
    print("\n⚙️ Phase 5: Formatage du fichier de sortie pour Odoo...")

    balanced_df['Debit'] = balanced_df['Debit'].round(2)
    balanced_df['Credit'] = balanced_df['Credit'].round(2)

    final_columns = ["Reference", "Date", "Journal*", "Journal Items/Account*", "Journal Items/Partner/ID", "Journal Items/Label", "Journal Items/Debit", "Journal Items/Credit"]
    output_rows = []

    for ref, group in balanced_df.groupby('Reference'):
        group = group.sort_index()
        is_first_line = True
        for index, row in group.iterrows():
            if is_first_line:
                output_rows.append({
                    "Reference": row['Reference'], "Date": row['Date'], "Journal*": row['Journal'],
                    "Journal Items/Account*": row['Account'], "Journal Items/Partner/ID": row['Partner'],
                    "Journal Items/Label": row['Label'], "Journal Items/Debit": row['Debit'], "Journal Items/Credit": row['Credit']
                })
                is_first_line = False
            else:
                output_rows.append({
                    "Reference": "", "Date": "", "Journal*": "",
                    "Journal Items/Account*": row['Account'], "Journal Items/Partner/ID": row['Partner'],
                    "Journal Items/Label": row['Label'], "Journal Items/Debit": row['Debit'], "Journal Items/Credit": row['Credit']
                })

    final_df_formatted = pd.DataFrame(output_rows, columns=final_columns)
    
    final_df_formatted.to_csv(ENTRIES_OUT_FILE, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    unbalanced_df.to_csv(UNBALANCED_FILE, index=False, encoding="utf-8-sig")

    unbalanced_count = unbalanced_df.groupby('Reference').ngroups
    print(f"\n✅ {len(balanced_refs)} écritures valides formatées et exportées vers {ENTRIES_OUT_FILE}")
    print(f"⚠️ {unbalanced_count} écritures non équilibrées ont été écartées et sauvées dans {UNBALANCED_FILE} pour analyse.")

if __name__ == "__main__":
    run_importer()