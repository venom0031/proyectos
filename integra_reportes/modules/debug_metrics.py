
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import re

# Add current directory to path so we can import modules
sys.path.append(os.getcwd())

from etl import load_week_excel, load_historic_excel, normalize_est_name

def debug_specifics():
    print("Loading files...")
    try:
        # 1. Load Weekly and detect week
        df_week = load_week_excel("reporte_generado_semanal_20250927_20251003_cache_raw_consolidado.xlsx")
        
        current_week = None
        if "N° Semana" in df_week.columns:
            try:
                current_week = int(df_week["N° Semana"].dropna().max())
            except:
                pass
        
        if current_week is None:
             # Fallback filename logic
            filename = "reporte_generado_semanal_20250927_20251003_cache_raw_consolidado.xlsx"
            match = re.search(r"(\d{8})_(\d{8})", filename)
            if match:
                date_str = match.group(2)
                dt = datetime.strptime(date_str, "%Y%m%d")
                current_week = dt.isocalendar()[1]
        
        print(f"Detected Current Week: {current_week}")
        
        # 2. Load Historic
        df_hist = load_historic_excel("HISTORICO PERSISTENTE.xlsx")
        
        # 3. Check specific problematic establishments
        targets = ["La Esperanza"]
        
        print(f"\n--- Inspecting Targets ({len(targets)}) ---")
        for t in targets:
            norm_t = normalize_est_name(t)
            print(f"\nTarget: '{t}' (Normalized: '{norm_t}')")
            
            # Check existence in Historic
            hist_matches = df_hist[df_hist["Establecimiento"] == norm_t]
            if hist_matches.empty:
                print("  -> NOT FOUND in Historic file (after normalization).")
            else:
                print(f"  -> Found {len(hist_matches)} rows in Historic.")
                
                # Drop rows with no week
                hist_matches = hist_matches.dropna(subset=["N° Semana"])
                
                # Check weeks
                weeks_available = sorted(hist_matches["N° Semana"].unique())
                print(f"  -> Last 10 weeks available: {weeks_available[-10:]}")
                
                # Check dates for the last few weeks to align with filename
                if "Fecha" in hist_matches.columns:
                    last_weeks = weeks_available[-5:]
                    print("\n  -> Dates for last 5 weeks:")
                    for w in last_weeks:
                        dates = hist_matches[hist_matches["N° Semana"] == w]["Fecha"].unique()
                        # Format dates as string to avoid long output
                        date_strs = [pd.to_datetime(d).strftime('%Y-%m-%d') for d in dates if pd.notna(d)]
                        print(f"     Week {w}: {date_strs}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_specifics()
