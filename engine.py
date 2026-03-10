import pandas as pd
import numpy as np
import re


# ---------- CLEAN PRICE ----------
def clean_price(x):
    if pd.isna(x):
        return np.nan

    x = str(x)
    x = x.replace(",", "")
    x = re.sub(r"[^\d.]", "", x)

    try:
        return float(x)
    except:
        return np.nan


# ---------- CLEAN ID ----------
def clean_id(x):
    if pd.isna(x):
        return None

    x = str(x)
    match = re.search(r"(\d+)$", x)

    return match.group(1) if match else x.strip()


# ---------- MAIN FUNCTION ----------
def generate_price_change_report(files):

    dfs = []
    labels = []

    for file in files:

        label = file.name.replace(".xlsx", "")
        labels.append(label)

        df = pd.read_excel(file)

        # remove spaces in column names
        df.columns = df.columns.str.strip()

        # make sure required columns exist
        required = ["Product Name", "Price", "ID"]

        for col in required:
            if col not in df.columns:
                raise ValueError(
                    f"{file.name} must contain columns: Product Name, Price, ID"
                )

        # KEEP ONLY THESE COLUMNS (ignore scraper columns)
        df = df[["Product Name", "Price", "ID"]].copy()

        # rename internally
        df.columns = ["Product_Name", "Price", "ID"]

        # clean data
        df["Price"] = df["Price"].apply(clean_price)
        df["ID"] = df["ID"].apply(clean_id)

        df["Product_Name"] = (
            df["Product_Name"]
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

        df = df.dropna(subset=["ID", "Price"])

        dfs.append(df)

    if len(dfs) < 2:
        raise ValueError("Upload at least two Excel files")

    old_df = dfs[0]
    new_df = dfs[-1]

    old_label = labels[0]
    new_label = labels[-1]

    merged = old_df.merge(
        new_df,
        on="ID",
        how="inner",
        suffixes=(f" ({old_label})", f" ({new_label})")
    )

    old_price = f"Price ({old_label})"
    new_price = f"Price ({new_label})"

    merged["Change_Value"] = (merged[new_price] - merged[old_price]).round(2)

    merged = merged[merged["Change_Value"] != 0]

    merged["Change_Amount"] = merged["Change_Value"].apply(
        lambda x: f"+{x}" if x > 0 else str(x)
    )

    return merged[
        [
            f"Product_Name ({old_label})",
            "ID",
            old_price,
            new_price,
            "Change_Amount",
        ]
    ].rename(columns={
        f"Product_Name ({old_label})": "Product_Name"
    })
