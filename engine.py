import pandas as pd
import numpy as np
import re


# ---------- CLEAN PRICE ----------
def clean_price(x):
    if pd.isna(x):
        return np.nan

    x = str(x)

    # remove commas
    x = x.replace(",", "")

    # keep only numbers and decimal
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

    name = filename.lower()

    if "morning" in name:
        return 0
    elif "evening" in name:
        return 1
    else:
        return 2


# ---------- MAIN LOGIC ----------
def generate_price_change_report(files):

    files = sorted(files, key=lambda f: file_sort_key(f.name))

    dfs = []
    labels = []

    for file in files:

        label = file.name.replace(".xlsx", "")
        labels.append(label)

        df = pd.read_excel(file)

        # ---------- CLEAN COLUMN NAMES ----------
        df.columns = df.columns.str.strip()

        # ---------- CHECK REQUIRED COLUMNS ----------
        required_cols = ["Product Name", "Price", "ID"]

        missing = [c for c in required_cols if c not in df.columns]

        if missing:
            raise ValueError(
                f"{file.name} is missing columns: {', '.join(missing)}"
            )

        # ---------- KEEP ONLY NEEDED COLUMNS ----------
        df = df[["Product Name", "Price", "ID"]].copy()

        # ---------- RENAME FOR INTERNAL USE ----------
        df.columns = ["Product_Name", "Buy Now", "Listing_ID"]

        # ---------- CLEAN DATA ----------
        df["Buy Now"] = df["Buy Now"].apply(clean_price)
        df["Listing_ID"] = df["Listing_ID"].apply(clean_listing_id)

        # remove line breaks in product names
        df["Product_Name"] = (
            df["Product_Name"]
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

        # remove invalid rows
        df = df.dropna(subset=["Listing_ID", "Buy Now"])

        # ensure one price per listing
        df = (
            df.sort_values("Buy Now")
            .groupby("Listing_ID", as_index=False)
            .last()
        )

        dfs.append(df)

    if len(dfs) < 2:
        raise ValueError("Upload at least TWO Excel files")

    old_df = dfs[0]
    new_df = dfs[-1]

    old_label = labels[0]
    new_label = labels[-1]

    merged = old_df.merge(
        new_df,
        on="Listing_ID",
        how="inner",
        suffixes=(f" ({old_label})", f" ({new_label})")
    )

    old_price_col = f"Buy Now ({old_label})"
    new_price_col = f"Buy Now ({new_label})"

    # ---------- PRICE DIFFERENCE ----------
    merged["Change_Value"] = (
        merged[new_price_col] - merged[old_price_col]
    ).round(2)

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
