from dbfread import DBF
from pathlib import Path
import pandas as pd
import sys

# Path to your extracted files
BASE = r"PATH_ICI"
OUT_FILE = "dbf_inspect_output.txt"

p = Path(BASE)
out_lines = []

def cols(df): return [c.strip().upper() for c in df.columns]

for f in sorted(p.glob("*.dbf")):
    try:
        dbf = DBF(str(f), encoding="latin-1")
        df = pd.DataFrame(iter(dbf))
        df.columns = cols(df)
        out_lines.append(f"\n=== {f.name} === rows={len(df)}")
        out_lines.append("Columns: " + ", ".join(df.columns))
        if not df.empty:
            out_lines.append("Preview:")
            out_lines.append(df.head(3).to_string(index=False))
    except Exception as e:
        out_lines.append(f"\n=== {f.name} === (read error) {e}")

# Save everything to file
Path(OUT_FILE).write_text("\n".join(out_lines), encoding="utf-8")
print(f"✅ Inspection complete. Results saved to: {OUT_FILE}")
