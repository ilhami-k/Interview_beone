#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dbfread import DBF
import pandas as pd
from pathlib import Path
#######################LES PATHS NE SONT PAS CONFIGURES
# Configuration des chemins de fichiers
DBF_DIR = Path(r"C:\Users\zenleis\Downloads\test\@CIE@EBS")
SRC_FILE = DBF_DIR / "EBS_ACF.DBF"
OUT_FILE = "accounts_odoo_final_filtered.csv"

# --- LA CORRECTION EST ICI ---
# Liste des comptes standards de Odoo qui ne peuvent pas être supprimés ou recréés.
# Nous allons les exclure de notre importation.
EXISTING_PROTECTED_ACCOUNTS = {
    '100000', '101000', '110900', '111900', '121000', '130000', '131100', '132000',
    '133000', '140000', '150000', '160000', '161000', '173000', '174000', '176000',
    '179000', '200000', '210000', '210009', '220000', '221000', '221009', '230000',
    '240000', '241000', '252000', '252009', '252100', '252109', '260000', '260009',
    '280100', '285000', '288000', '310000', '340000', '400000', '404000', '407000',
    '409000', '410000', '411000', '411200', '412000', '416000', '422000', '423000',
    '423100', '430000', '440000', '444000', '450000', '451000', '451200', '451800',
    '452000', '453000', '454000', '455000', '456000', '459000', '460000', '490000',
    '491000', '492000', '493000', '499000', '530000', '550000', '570000', '580000',
    '600000', '604000', '608000', '609000', '609100', '610000', '610100', '611300',
    '612000', '612200', '613200', '613250', '613310', '613311', '614000', '614500',
    '614600', '617000', '620100', '620200', '620300', '621000', '622000', '623000',
    '630000', '630100', '630200', '634000', '634100', '640000', '640200', '640400',
    '640500', '640600', '640800', '641000', '642000', '643000', '645000', '649000',
    '650000', '650100', '653000', '654000', '655000', '657000', '657100', '657200',
    '659000', '660200', '663000', '663100', '664000', '670000', '670100', '671000',
    '671100', '671200', '690000', '692000', '692100', '693000', '695000', '700100',
    '700500', '708000', '713000', '740000', '741000', '750000', '753000', '754000',
    '755000', '757000', '760000', '760100', '764000', '769000', '771100', '771200',
    '790000', '792000', '793000'
}

def get_account_type(code: str) -> str:
    """Détermine le type de compte Odoo en fonction du préfixe du code comptable."""
    if code.startswith("55"): return "asset_cash"
    if code.startswith("400"): return "liability_payable"
    if code.startswith("440"): return "asset_receivable"
    if code.startswith(("1", "2", "3", "4", "5")): return "asset_current"
    if code.startswith(("6", "7")): return "expense"
    return "equity"

def import_chart_of_accounts():
    """
    Charge le plan comptable, filtre les comptes déjà existants dans Odoo,
    supprime les doublons, et l'exporte en un CSV prêt pour l'importation.
    """
    print(f"📥 Chargement de {SRC_FILE}...")
    if not SRC_FILE.exists():
        raise SystemExit(f"Fichier DBF introuvable: {SRC_FILE}")

    table = DBF(str(SRC_FILE), encoding="latin-1", char_decode_errors='ignore')
    df = pd.DataFrame(iter(table))
    df.columns = [c.strip().upper() for c in df.columns]

    name_col = df.get("NAME11") if "NAME11" in df.columns else df.get("NAME12")
    
    accounts = pd.DataFrame()
    accounts["code"] = df["NUMBER"].astype(str).str.strip()
    accounts["name"] = name_col.astype(str).str.strip() if name_col is not None else ""
    
    accounts = accounts[accounts["code"].ne("")].copy()
    accounts.drop_duplicates(subset=["code"], keep="first", inplace=True)

    # Filtre pour exclure les comptes protégés
    original_count = len(accounts)
    accounts = accounts[~accounts["code"].isin(EXISTING_PROTECTED_ACCOUNTS)]
    print(f"ℹ️ {original_count - len(accounts)} comptes existants ont été exclus de l'importation.")

    accounts["id"] = "beone_winbooks_account_" + accounts["code"]
    accounts["account_type"] = accounts["code"].apply(get_account_type)
    accounts["reconcile"] = accounts["account_type"].isin(["liability_payable", "asset_receivable"])

    final_cols = ["id", "code", "name", "account_type", "reconcile"]
    accounts = accounts[final_cols]

    accounts.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ {len(accounts)} nouveaux comptes uniques exportés vers {OUT_FILE}")

if __name__ == "__main__":
    import_chart_of_accounts()