"""Funciones compartidas para formateo de números y DataFrames con locale español."""
import pandas as pd


def format_number_spanish(x):
    """
    Convierte un número a formato español: 1.234,56
    (punto para miles, coma para decimales)
    """
    if pd.isna(x):
        return ""
    if isinstance(x, (int, float)):
        # Formato: dos decimales, separador de miles
        formatted = f"{x:,.2f}"  # 1,234.56
        # Intercambiar coma y punto: 1.234,56
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return str(x)


def format_dataframe_for_display(df: pd.DataFrame) -> tuple:
    """
    Formatea un DataFrame para mostrar números con formato español.
    Retorna (df_formatted, column_config)
    """
    df_display = df.copy()
    column_config = {}
    
    for col in df_display.columns:
        try:
            if pd.api.types.is_numeric_dtype(df_display[col]):
                # Convertir a string con formato español
                df_display[col] = df_display[col].apply(format_number_spanish)
        except:
            pass
    
    return df_display, None
