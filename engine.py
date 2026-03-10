import pandas as pd
import numpy as np
import re


# ---------- CLEAN BUY NOW PRICE ----------
def clean_price(x):
    if pd.isna(x):
        return np.nan
    x = str(x)
    x = re.sub(r"[^\d.]", "", x)
    try:
        return float(x)
    except:
        return np.nan


# ---------- CLEAN LISTING ID ----------
def clean_listing_id(x):
    if pd.isna(x):
        return None
    x = str(x)
    match = re.search(r"(\d+)$", x)
    return match.group(1) if match else x.strip()


# ---------- FILE SORT KEY ----------
def file_sort_key(filename):
    """
    Ensures:
    - Morning file ALWAYS first
    - Evening file ALWAYS last
    """
    date_match = re.search(r"(\d{2}[_-]\d{2}[_-]\d{2})", filename)
    date_key = date_match.group(1) if date_match else ""

    name = filename.lower()

    if "morning" in name:
        time_key = 0
    elif "evening" in name:
        time_key = 1
    else:
        time_key = 2  # fallback

    return (date_key, time_key)


# ---------- MAIN LOGIC ----------
def generate_price_change_report(files):

    # 🔥 GUARANTEED ORDER: Morning → Evening
    files = sorted(files, key=lambda f: file_sort_key(f.name))

    dfs = []
    labels = []

    for file in files:
        label = file.name.replace(".xlsx", "")
        labels.append(label)

        df = pd.read_excel(file)

        df = df[["Listing_ID", "Product_Name", "Buy Now"]].copy()

        df["Listing_ID"] = df["Listing_ID"].apply(clean_listing_id)
        df["Buy Now"] = df["Buy Now"].apply(clean_price)

        df = df.dropna(subset=["Listing_ID", "Buy Now"])

        # ONE PRICE PER LISTING_ID PER FILE
        df = (
            df.sort_values("Buy Now")
              .groupby("Listing_ID", as_index=False)
              .last()
        )

        dfs.append(df)

    # OLD = MORNING
    # NEW = EVENING
    old_df, new_df = dfs[0], dfs[-1]
    old_label, new_label = labels[0], labels[-1]

    merged = old_df.merge(
        new_df,
        on="Listing_ID",
        how="inner",
        suffixes=(f" ({old_label})", f" ({new_label})")
    )

    old_price_col = f"Buy Now ({old_label})"
    new_price_col = f"Buy Now ({new_label})"

    # ✅ ALWAYS: Evening - Morning
    merged["Change_Value"] = (merged[new_price_col] - merged[old_price_col]).round(2)

    merged = merged[merged["Change_Value"] != 0]

    merged["Change_Amount"] = merged["Change_Value"].apply(
        lambda x: f"+{x}" if x > 0 else str(x)
    )

    return merged[
        [
            f"Product_Name ({old_label})",
            "Listing_ID",
            old_price_col,
            new_price_col,
            "Change_Amount",
        ]
    ].rename(columns={
        f"Product_Name ({old_label})": "Product_Name"
    })
