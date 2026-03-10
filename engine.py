import pandas as pd
import numpy as np
import re
from datetime import datetime


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


# ---------- EXTRACT DATE ----------
def extract_date(filename):

    m = re.search(r'(\d{1,2})[_-](\d{1,2})[_-](\d{2,4})', filename)

    if not m:
        return None

    d, mth, y = m.groups()

    y = int(y)
    if y < 100:
        y += 2000

    try:
        return datetime(y, int(mth), int(d)).date()
    except:
        return None


# ---------- TIME RANK ----------
def time_rank(filename):

    name = filename.lower()

    if "morning" in name or re.search(r'\bmor\b', name):
        return 0

    if "afternoon" in name or re.search(r'\baft\b', name):
        return 1

    if "evening" in name or re.search(r'\beve\b', name):
        return 2

    return 3


# ---------- MAIN FUNCTION ----------
def generate_price_change_report(files):

    file_meta = []

    for f in files:

        name = f.name

        dt = extract_date(name)
        tr = time_rank(name)

        if dt is None:
            raise ValueError(f"Could not detect date in filename: {name}")

        file_meta.append((dt, tr, f))

    file_meta.sort(key=lambda x: (x[0], x[1]))

    old_file = file_meta[0][2]
    new_file = file_meta[-1][2]

    old_label = old_file.name.replace(".xlsx", "")
    new_label = new_file.name.replace(".xlsx", "")

    old_df = pd.read_excel(old_file)
    new_df = pd.read_excel(new_file)

    old_df.columns = old_df.columns.str.strip()
    new_df.columns = new_df.columns.str.strip()

    required = ["Product Name", "Price", "ID"]

    for col in required:
        if col not in old_df.columns or col not in new_df.columns:
            raise ValueError("Excel must contain: Product Name, Price, ID")

    old_df = old_df[required].copy()
    new_df = new_df[required].copy()

    old_df.columns = ["Product_Name", "Price", "ID"]
    new_df.columns = ["Product_Name", "Price", "ID"]

    old_df["Price"] = old_df["Price"].apply(clean_price)
    new_df["Price"] = new_df["Price"].apply(clean_price)

    old_df["ID"] = old_df["ID"].apply(clean_id)
    new_df["ID"] = new_df["ID"].apply(clean_id)

    old_df["Product_Name"] = (
        old_df["Product_Name"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    new_df["Product_Name"] = (
        new_df["Product_Name"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    old_df = old_df.dropna(subset=["ID", "Price"])
    new_df = new_df.dropna(subset=["ID", "Price"])

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
