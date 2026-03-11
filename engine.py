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


# ---------- CLEAN LISTING ID ----------
def clean_id(x):

    if pd.isna(x):
        return None

    x = str(x).strip()

    # BIDBUD URL
    m = re.search(r"/(\d+)$", x)
    if m:
        return m.group(1)

    # KOGAN IMAGE URL
    m = re.search(r"/images/[^/]+/([^/]+)/", x)
    if m:
        return m.group(1)

    return x


# ---------- EXTRACT DATE FROM FILENAME ----------
def extract_date(filename):

    match = re.search(r"(\d{1,2})[_-](\d{1,2})[_-](\d{2,4})", filename)

    if not match:
        return None

    d, m, y = match.groups()

    y = int(y)
    if y < 100:
        y += 2000

    try:
        return datetime(y, int(m), int(d)).date()
    except:
        return None


# ---------- TIME OF DAY RANK ----------
def time_rank(filename):

    name = filename.lower()

    if "morning" in name or re.search(r"\bmor\b", name):
        return 0

    if "afternoon" in name or re.search(r"\baft\b", name):
        return 1

    if "evening" in name or re.search(r"\beve\b", name):
        return 2

    return 3


# ---------- MAIN FUNCTION ----------
def generate_price_change_report(files):

    file_meta = []

    for f in files:

        filename = f.name

        date_value = extract_date(filename)
        time_value = time_rank(filename)

        if date_value is None:
            raise ValueError(f"Could not detect date in filename: {filename}")

        file_meta.append((date_value, time_value, f))

    # sort files by date + time
    file_meta.sort(key=lambda x: (x[0], x[1]))

    old_file = file_meta[0][2]
    new_file = file_meta[-1][2]

    old_label = old_file.name.replace(".xlsx", "")
    new_label = new_file.name.replace(".xlsx", "")

    old_df = pd.read_excel(old_file)
    new_df = pd.read_excel(new_file)

    # clean column names
    old_df.columns = old_df.columns.str.strip()
    new_df.columns = new_df.columns.str.strip()

    # normalize column names
    old_df.columns = old_df.columns.str.lower()
    new_df.columns = new_df.columns.str.lower()

    required = ["product name", "price", "listing id"]

    for col in required:
        if col not in old_df.columns or col not in new_df.columns:
            raise ValueError("Excel must contain: Product Name, Price, Listing ID")

    # keep only required columns
    old_df = old_df[required].copy()
    new_df = new_df[required].copy()

    # rename internally
    old_df.columns = ["Product_Name", "Price", "Listing_ID"]
    new_df.columns = ["Product_Name", "Price", "Listing_ID"]

    # clean data
    old_df["Price"] = old_df["Price"].apply(clean_price)
    new_df["Price"] = new_df["Price"].apply(clean_price)

    old_df["Listing_ID"] = old_df["Listing_ID"].apply(clean_id)
    new_df["Listing_ID"] = new_df["Listing_ID"].apply(clean_id)

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

    # remove invalid rows
    old_df = old_df.dropna(subset=["Listing_ID", "Price"])
    new_df = new_df.dropna(subset=["Listing_ID", "Price"])

    # merge on listing id
    merged = old_df.merge(
        new_df,
        on="Listing_ID",
        how="inner",
        suffixes=(f" ({old_label})", f" ({new_label})")
    )

    old_price = f"Price ({old_label})"
    new_price = f"Price ({new_label})"

    # calculate price difference
    merged["Change_Value"] = (merged[new_price] - merged[old_price]).round(2)

    merged = merged[merged["Change_Value"] != 0]

    merged["Change_Amount"] = merged["Change_Value"].apply(
        lambda x: f"+{x}" if x > 0 else str(x)
    )

    return merged[
        [
            f"Product_Name ({old_label})",
            "Listing_ID",
            old_price,
            new_price,
            "Change_Amount",
        ]
    ].rename(columns={
        f"Product_Name ({old_label})": "Product_Name"
    })
