"""
Synthetic Transaction Data Generator for SUS 🤨

Generates reproducible transaction-level data with merchant-day window labels
(baseline, organic_spike, fraud_spike) for training the spike-cause classifier.

Usage:
    python -m src.generate_data

Output:
    data/raw/transactions.csv
    data/raw/window_labels.csv
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_MERCHANTS = 8
NUM_DAYS = 45
DEFAULT_SEED = 42

# Class distribution targets (approximate proportions)
# With 45 days per merchant and max_run=3, we need enough non-baseline labels
# to separate baseline into groups of <=3. ceil(b/3)-1 <= (45-b), so b <= 34.
BASELINE_PROPORTION = 0.73  # -> 33 baselines, 12 non-baselines per merchant
ORGANIC_SPIKE_PROPORTION = 0.14  # -> 6 organic per merchant
FRAUD_SPIKE_PROPORTION = 0.13  # -> 6 fraud per merchant

# Transaction volume multipliers for spikes
ORGANIC_VOLUME_MULTIPLIER_MIN = 1.5
ORGANIC_VOLUME_MULTIPLIER_MAX = 3.5
FRAUD_VOLUME_MULTIPLIER_MIN = 1.3
FRAUD_VOLUME_MULTIPLIER_MAX = 4.0

# Date range
START_DATE = "2025-07-01"


# ---------------------------------------------------------------------------
# Merchant profile dataclass
# ---------------------------------------------------------------------------

@dataclass
class MerchantProfile:
    """Persistent characteristics defining a merchant's normal behavior."""
    merchant_id: str
    base_daily_volume: int
    amount_min: float
    amount_max: float
    catalog_size: int
    customer_pool_size: int
    repeat_customer_rate: float
    base_failure_rate: float
    retry_given_failure_rate: float
    device_pool_size: int
    ip_pool_size: int

    def __post_init__(self) -> None:
        # Derived values for internal use
        self.sku_weights: np.ndarray = np.array([])
        self.customer_ids: list[str] = []
        self.device_ids: list[str] = []
        self.ip_ids: list[str] = []


# ---------------------------------------------------------------------------
# Create merchant profiles
# ---------------------------------------------------------------------------

def create_merchant_profiles(seed: int = DEFAULT_SEED) -> list[MerchantProfile]:
    """
    Create 8 distinct merchant profiles with persistent characteristics.

    Each merchant has unique baseline behavior: volume, pricing, catalog size,
    customer base, and payment patterns.
    """
    rng = np.random.RandomState(seed)

    profiles = [
        # High-volume, low-AOV, large catalog (e.g., grocery / e-commerce)
        MerchantProfile(
            merchant_id="merchant_001",
            base_daily_volume=650,
            amount_min=50.0, amount_max=500.0,
            catalog_size=500,
            customer_pool_size=8000,
            repeat_customer_rate=0.45,
            base_failure_rate=0.03,
            retry_given_failure_rate=0.25,
            device_pool_size=4000,
            ip_pool_size=3000,
        ),
        # Medium volume, medium AOV, medium catalog
        MerchantProfile(
            merchant_id="merchant_002",
            base_daily_volume=420,
            amount_min=200.0, amount_max=2000.0,
            catalog_size=150,
            customer_pool_size=3000,
            repeat_customer_rate=0.55,
            base_failure_rate=0.04,
            retry_given_failure_rate=0.30,
            device_pool_size=1800,
            ip_pool_size=1400,
        ),
        # High volume, low AOV, very large catalog (e.g., marketplace)
        MerchantProfile(
            merchant_id="merchant_003",
            base_daily_volume=850,
            amount_min=30.0, amount_max=300.0,
            catalog_size=1200,
            customer_pool_size=12000,
            repeat_customer_rate=0.35,
            base_failure_rate=0.05,
            retry_given_failure_rate=0.20,
            device_pool_size=6000,
            ip_pool_size=5000,
        ),
        # Low volume, high AOV, small catalog (e.g., luxury / B2B)
        MerchantProfile(
            merchant_id="merchant_004",
            base_daily_volume=300,
            amount_min=1000.0, amount_max=10000.0,
            catalog_size=30,
            customer_pool_size=800,
            repeat_customer_rate=0.65,
            base_failure_rate=0.02,
            retry_given_failure_rate=0.15,
            device_pool_size=500,
            ip_pool_size=400,
        ),
        # Medium-high volume, medium AOV, medium catalog
        MerchantProfile(
            merchant_id="merchant_005",
            base_daily_volume=580,
            amount_min=150.0, amount_max=1500.0,
            catalog_size=200,
            customer_pool_size=5000,
            repeat_customer_rate=0.50,
            base_failure_rate=0.04,
            retry_given_failure_rate=0.28,
            device_pool_size=3000,
            ip_pool_size=2500,
        ),
        # Medium volume, medium-high AOV, small catalog
        MerchantProfile(
            merchant_id="merchant_006",
            base_daily_volume=480,
            amount_min=300.0, amount_max=3000.0,
            catalog_size=60,
            customer_pool_size=2000,
            repeat_customer_rate=0.60,
            base_failure_rate=0.03,
            retry_given_failure_rate=0.22,
            device_pool_size=1200,
            ip_pool_size=1000,
        ),
        # High volume, low-medium AOV, large catalog (e.g., SaaS subscriptions)
        MerchantProfile(
            merchant_id="merchant_007",
            base_daily_volume=720,
            amount_min=100.0, amount_max=800.0,
            catalog_size=400,
            customer_pool_size=7000,
            repeat_customer_rate=0.58,
            base_failure_rate=0.06,
            retry_given_failure_rate=0.35,
            device_pool_size=3500,
            ip_pool_size=3000,
        ),
        # Medium volume, medium AOV, medium catalog
        MerchantProfile(
            merchant_id="merchant_008",
            base_daily_volume=520,
            amount_min=250.0, amount_max=2500.0,
            catalog_size=100,
            customer_pool_size=4000,
            repeat_customer_rate=0.52,
            base_failure_rate=0.03,
            retry_given_failure_rate=0.25,
            device_pool_size=2200,
            ip_pool_size=1800,
        ),
    ]

    # Generate deterministic IDs and weights for each merchant
    for p in profiles:
        # SKU popularity weights (Zipf-like distribution)
        ranks = np.arange(1, p.catalog_size + 1, dtype=float)
        p.sku_weights = 1.0 / (ranks ** 0.8)
        p.sku_weights = p.sku_weights / p.sku_weights.sum()

        # Deterministic customer IDs
        p.customer_ids = [f"{p.merchant_id}_cust_{i:05d}" for i in range(p.customer_pool_size)]
        # Deterministic device IDs
        p.device_ids = [f"{p.merchant_id}_dev_{i:05d}" for i in range(p.device_pool_size)]
        # Deterministic IP IDs
        p.ip_ids = [f"{p.merchant_id}_ip_{i:05d}" for i in range(p.ip_pool_size)]

    return profiles


# ---------------------------------------------------------------------------
# Schedule window labels
# ---------------------------------------------------------------------------

def _assign_labels_no_long_runs(
    rng: np.random.RandomState,
    num_items: int,
    label_counts: dict[str, int],
    max_run: int = 3,
) -> list[str]:
    """
    Assign labels ensuring no label appears more than max_run times consecutively.

    Deterministic interleaving: sort by frequency, place the most common label
    in groups of max_run, separated by other labels. Then insert any remaining
    other labels at valid positions.
    """
    sorted_labels = sorted(label_counts.items(), key=lambda x: -x[1])
    majority_label, majority_count = sorted_labels[0]
    other_counts = {l: c for l, c in sorted_labels[1:]}

    # Build pool of non-majority labels
    others_pool: list[str] = []
    for l, c in other_counts.items():
        others_pool.extend([l] * c)
    rng.shuffle(others_pool)

    # Place majority in groups of max_run, each followed by a separator
    result: list[str] = []
    remaining_majority = majority_count

    while remaining_majority > 0:
        chunk = min(max_run, remaining_majority)
        result.extend([majority_label] * chunk)
        remaining_majority -= chunk
        if remaining_majority > 0 and others_pool:
            result.append(others_pool.pop(0))

    # Insert any remaining other labels at valid positions
    while others_pool:
        label = others_pool.pop(0)
        inserted = False
        for i in range(len(result) + 1):
            # Would inserting at position i create a run of this label > max_run?
            ok = True
            # Check left: how many consecutive 'label' are to the left of i?
            left_count = 0
            j = i - 1
            while j >= 0 and result[j] == label:
                left_count += 1
                j -= 1
            # Check right: how many consecutive 'label' are to the right of i?
            right_count = 0
            j = i
            while j < len(result) and result[j] == label:
                right_count += 1
                j += 1
            if left_count + 1 + right_count > max_run:
                ok = False
            if ok:
                result.insert(i, label)
                inserted = True
                break
        if not inserted:
            result.append(label)

    return result[:num_items]


def schedule_window_labels(
    profiles: list[MerchantProfile],
    num_days: int,
    seed: int = DEFAULT_SEED,
) -> list[dict]:
    """
    Assign a window label to each merchant-day.

    Returns a list of dicts with keys: merchant_id, date, window_label.
    Class imbalance: ~75% baseline, ~13% organic_spike, ~12% fraud_spike.
    No merchant gets the same label more than 3 days in a row.
    """
    rng = np.random.RandomState(seed)
    start = pd.Timestamp(START_DATE)

    # Base target counts per merchant
    base_organic = int(num_days * ORGANIC_SPIKE_PROPORTION)
    base_fraud = int(num_days * FRAUD_SPIKE_PROPORTION)

    # Max baselines allowed with max_run=3: baseline <= (non_baseline + 1) * 3
    # For 45 days: max baselines = 34 (need 11 non-baselines)
    max_run = 3

    windows: list[dict] = []
    for p in profiles:
        # Randomize per-merchant counts with small perturbation
        merchant_organic = max(1, base_organic + rng.randint(-2, 3))
        merchant_fraud = max(1, base_fraud + rng.randint(-2, 3))

        # Enforce constraint: baseline <= (organic + fraud + 1) * max_run
        non_baseline = merchant_organic + merchant_fraud
        max_baseline = (non_baseline + 1) * max_run
        merchant_baseline = num_days - non_baseline

        if merchant_baseline > max_baseline:
            # Need more non-baselines. Reduce baselines by adding spikes.
            merchant_baseline = min(merchant_baseline, max_baseline)
            non_baseline = num_days - merchant_baseline
            # Redistribute non-baseline between organic and fraud
            merchant_organic = max(1, non_baseline // 2)
            merchant_fraud = non_baseline - merchant_organic

        label_counts = {
            "baseline": merchant_baseline,
            "organic_spike": merchant_organic,
            "fraud_spike": merchant_fraud,
        }

        merchant_labels = _assign_labels_no_long_runs(
            rng, num_days, label_counts, max_run=max_run
        )

        for d in range(num_days):
            windows.append({
                "merchant_id": p.merchant_id,
                "date": (start + pd.Timedelta(days=d)).date(),
                "window_label": merchant_labels[d],
            })

    return windows


# ---------------------------------------------------------------------------
# Generate transactions for a single merchant-day
# ---------------------------------------------------------------------------

def _generate_customer_set(
    rng: np.random.RandomState,
    profile: MerchantProfile,
    day_existing_customers: set[str],
    all_time_customers: dict[str, set[str]],
    merchant_id: str,
) -> tuple[list[str], list[bool]]:
    """
    Generate customer IDs for a batch of transactions, tracking new vs returning.

    Returns (customer_ids, is_new_flags).
    """
    pool = profile.customer_ids
    num_txns = len(day_existing_customers)  # placeholder; actual count passed in
    # This is called with the right size from generate_day_transactions
    pass  # placeholder; actual implementation below inlined in caller


def generate_day_transactions(
    rng: np.random.RandomState,
    profile: MerchantProfile,
    date: pd.Timestamp,
    window_label: str,
    all_time_customers: dict[str, set[str]],
    all_time_devices: dict[str, set[str]],
    all_time_ips: dict[str, set[str]],
) -> list[dict]:
    """
    Generate all transactions for a single merchant-day window.

    Behavior is determined by the window label and merchant profile.
    """
    # Determine transaction count
    base_vol = profile.base_daily_volume
    if window_label == "baseline":
        # Baseline: natural variation around base volume
        vol_multiplier = rng.uniform(0.7, 1.3)
    elif window_label == "organic_spike":
        vol_multiplier = rng.uniform(ORGANIC_VOLUME_MULTIPLIER_MIN, ORGANIC_VOLUME_MULTIPLIER_MAX)
    else:  # fraud_spike
        vol_multiplier = rng.uniform(FRAUD_VOLUME_MULTIPLIER_MIN, FRAUD_VOLUME_MULTIPLIER_MAX)

    num_txns = max(1, int(base_vol * vol_multiplier))

    # Determine behavioral adjustments based on label
    if window_label == "baseline":
        sku_concentration = 1.0  # normal distribution
        failure_rate_mult = 1.0
        device_concentration = 1.0
        ip_concentration = 1.0
        amount_shift = 0.0
        # repeat_customer_rate = proportion of customers who are repeat buyers
        # new_customer_rate = proportion of customers who are new = 1 - repeat_rate
        new_customer_rate = 1.0 - profile.repeat_customer_rate
    elif window_label == "organic_spike":
        # Organic: mostly healthy, but sometimes concentrated (viral product)
        sku_concentration = rng.choice([1.0, 0.6, 0.4], p=[0.5, 0.3, 0.2])
        failure_rate_mult = rng.uniform(0.8, 1.2)
        device_concentration = rng.uniform(0.9, 1.1)
        ip_concentration = rng.uniform(0.9, 1.1)
        amount_shift = rng.choice([0.0, -0.15, 0.05], p=[0.5, 0.3, 0.2])
        # More new customers during organic (fewer repeats)
        repeat_rate = profile.repeat_customer_rate * rng.uniform(0.6, 1.0)
        new_customer_rate = min(0.9, 1.0 - repeat_rate)
    else:  # fraud_spike
        # Fraud: concentrated in many cases, but with hard exceptions
        sku_concentration = rng.choice([0.3, 0.5, 0.7, 1.0], p=[0.35, 0.30, 0.20, 0.15])
        failure_rate_mult = rng.uniform(1.5, 4.0)
        device_concentration = rng.choice([0.3, 0.5, 0.8, 1.0], p=[0.30, 0.30, 0.25, 0.15])
        ip_concentration = rng.choice([0.3, 0.5, 0.8, 1.0], p=[0.30, 0.30, 0.25, 0.15])
        amount_shift = rng.choice([0.0, -0.1, -0.2], p=[0.4, 0.3, 0.3])
        # Mostly new customers (very few repeats)
        new_customer_rate = min(0.95, rng.uniform(0.6, 0.9))

    # Adjusted failure rate
    adjusted_failure_rate = min(0.3, profile.base_failure_rate * failure_rate_mult)

    # SKU selection weights (concentrated = fewer SKUs used)
    if sku_concentration < 1.0:
        weights = profile.sku_weights.copy()
        # Boost top SKUs
        boost = int(profile.catalog_size * (1.0 - sku_concentration))
        weights[:boost] *= 3.0
        weights = weights / weights.sum()
    else:
        weights = profile.sku_weights

    # Device/IP pools: concentration affects how many unique are used
    n_devices_pool = min(profile.device_pool_size, max(1, int(profile.device_pool_size * device_concentration)))
    n_ips_pool = min(profile.ip_pool_size, max(1, int(profile.ip_pool_size * ip_concentration)))

    merchant_id = profile.merchant_id
    date_str = date.strftime('%Y%m%d')
    seen_customers = all_time_customers[merchant_id]

    # --- Vectorized random draws ---
    txn_indices = np.arange(num_txns)

    # Customer selection: decide new vs returning
    cust_is_new_flags = rng.random(num_txns) < (1.0 - new_customer_rate)
    returning_indices = rng.randint(0, len(profile.customer_ids), size=num_txns)
    returning_cust_ids = [profile.customer_ids[i] for i in returning_indices]

    # For pool-selected customers, check if they've been seen before
    is_new_flags = np.copy(cust_is_new_flags)
    for i in range(num_txns):
        if not is_new_flags[i]:
            cid = returning_cust_ids[i]
            if cid not in seen_customers:
                is_new_flags[i] = True

    # Mix: occasionally force a returning customer to count as new (2% chance)
    mix_mask = (~is_new_flags) & (rng.random(num_txns) < 0.02)
    is_new_flags[mix_mask] = True

    # Build customer IDs
    customer_ids = []
    for i in range(num_txns):
        if is_new_flags[i]:
            customer_ids.append(f"{merchant_id}_new_{date_str}_{i:05d}")
        else:
            customer_ids.append(returning_cust_ids[i])

    # Track ALL selected pool customers so future days can recognize them
    for cid in returning_cust_ids:
        all_time_customers[merchant_id].add(cid)
    # Track generated new customer IDs too
    for i in range(num_txns):
        if is_new_flags[i]:
            all_time_customers[merchant_id].add(customer_ids[i])

    # SKU selection
    sku_indices = rng.choice(profile.catalog_size, size=num_txns, p=weights)
    sku_ids = [f"{merchant_id}_sku_{idx:04d}" for idx in sku_indices]

    # Amounts
    base_amounts = rng.uniform(profile.amount_min, profile.amount_max, size=num_txns)
    amounts = np.maximum(1.0, base_amounts * (1.0 + amount_shift))
    amounts = np.round(amounts, 2)

    # Device selection
    dev_indices = rng.randint(0, n_devices_pool, size=num_txns)
    device_ids = [profile.device_ids[i] for i in dev_indices]
    for did in device_ids:
        all_time_devices[merchant_id].add(did)

    # IP selection
    ip_indices = rng.randint(0, n_ips_pool, size=num_txns)
    ip_ids_list = [profile.ip_ids[i] for i in ip_indices]
    for iid in ip_ids_list:
        all_time_ips[merchant_id].add(iid)

    # Payment status and retry
    is_failed = rng.random(num_txns) < adjusted_failure_rate
    payment_statuses = np.where(is_failed, "failed", "success")
    is_retry_flags = np.zeros(num_txns, dtype=bool)
    failed_mask = is_failed
    is_retry_flags[failed_mask] = rng.random(failed_mask.sum()) < profile.retry_given_failure_rate

    # Timestamps: spread throughout the day
    hours = rng.randint(0, 24, size=num_txns)
    minutes = rng.randint(0, 60, size=num_txns)
    seconds = rng.randint(0, 60, size=num_txns)
    timestamps = [
        pd.Timestamp(year=date.year, month=date.month, day=date.day,
                     hour=int(h), minute=int(m), second=int(s))
        for h, m, s in zip(hours, minutes, seconds)
    ]

    # Transaction IDs
    txn_ids = [f"txn_{merchant_id}_{date_str}_{i:06d}" for i in txn_indices]

    # Build list of dicts (fast since all values are pre-computed)
    transactions = []
    for i in range(num_txns):
        transactions.append({
            "transaction_id": txn_ids[i],
            "merchant_id": merchant_id,
            "timestamp": timestamps[i],
            "date": date,
            "window_label": window_label,
            "customer_id": customer_ids[i],
            "customer_is_new": bool(is_new_flags[i]),
            "sku_id": sku_ids[i],
            "amount": float(amounts[i]),
            "payment_status": payment_statuses[i],
            "is_retry": bool(is_retry_flags[i]),
            "device_id": device_ids[i],
            "ip_id": ip_ids_list[i],
        })

    return transactions


# ---------------------------------------------------------------------------
# Generate full dataset
# ---------------------------------------------------------------------------

def generate_transactions(
    profiles: list[MerchantProfile],
    window_labels: list[dict],
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    """
    Generate the complete transaction dataset.
    """
    rng = np.random.RandomState(seed)

    # Persistent tracking dicts for customer/device/IP history across days
    all_time_customers: dict[str, set[str]] = {p.merchant_id: set() for p in profiles}
    all_time_devices: dict[str, set[str]] = {p.merchant_id: set() for p in profiles}
    all_time_ips: dict[str, set[str]] = {p.merchant_id: set() for p in profiles}

    profile_map = {p.merchant_id: p for p in profiles}

    all_transactions = []
    for wl in window_labels:
        p = profile_map[wl["merchant_id"]]
        date = pd.Timestamp(wl["date"])
        txns = generate_day_transactions(
            rng=rng,
            profile=p,
            date=date,
            window_label=wl["window_label"],
            all_time_customers=all_time_customers,
            all_time_devices=all_time_devices,
            all_time_ips=all_time_ips,
        )
        all_transactions.extend(txns)

    return pd.DataFrame(all_transactions)


# ---------------------------------------------------------------------------
# Validate generated data
# ---------------------------------------------------------------------------

def validate_generated_data(
    transactions: pd.DataFrame,
    window_labels_df: pd.DataFrame,
) -> list[str]:
    """
    Validate invariants on the generated dataset. Returns a list of errors (empty = valid).
    """
    errors: list[str] = []

    # 1. Exactly 8 unique merchants
    unique_merchants = transactions["merchant_id"].nunique()
    if unique_merchants != NUM_MERCHANTS:
        errors.append(f"Expected {NUM_MERCHANTS} merchants, got {unique_merchants}")

    # 2. Exactly 45 dates per merchant
    dates_per_merchant = transactions.groupby("merchant_id")["date"].nunique()
    for mid, count in dates_per_merchant.items():
        if count != NUM_DAYS:
            errors.append(f"Merchant {mid} has {count} dates, expected {NUM_DAYS}")

    # 3. Exactly 360 merchant-day windows
    total_windows = len(window_labels_df)
    expected_windows = NUM_MERCHANTS * NUM_DAYS
    if total_windows != expected_windows:
        errors.append(f"Expected {expected_windows} windows, got {total_windows}")

    # 4. Every transaction belongs to a valid window
    valid_keys = set(
        zip(window_labels_df["merchant_id"], window_labels_df["date"].astype(str))
    )
    txn_keys = set(
        zip(transactions["merchant_id"], transactions["date"].astype(str))
    )
    invalid = txn_keys - valid_keys
    if invalid:
        errors.append(f"{len(invalid)} transactions belong to invalid windows")

    # 5. Transaction IDs are unique
    if transactions["transaction_id"].duplicated().any():
        dup_count = transactions["transaction_id"].duplicated().sum()
        errors.append(f"{dup_count} duplicate transaction IDs found")

    # 6. No zero or negative amounts
    if (transactions["amount"] <= 0).any():
        errors.append("Found zero or negative transaction amounts")

    # 7. Window label transaction counts match
    txn_counts = transactions.groupby(["merchant_id", "date"]).size().reset_index(name="txn_count")
    txn_counts["date"] = txn_counts["date"].astype(str)
    window_labels_df_copy = window_labels_df.copy()
    window_labels_df_copy["date"] = window_labels_df_copy["date"].astype(str)
    merged = window_labels_df_copy.merge(txn_counts, on=["merchant_id", "date"], how="left")
    mismatches = merged[merged["transaction_count"] != merged["txn_count"]]
    if len(mismatches) > 0:
        errors.append(f"{len(mismatches)} windows have mismatched transaction counts")

    # 8. All three classes exist
    labels = set(window_labels_df["window_label"].unique())
    expected_labels = {"baseline", "organic_spike", "fraud_spike"}
    if labels != expected_labels:
        errors.append(f"Expected labels {expected_labels}, got {labels}")

    # 9. Baseline is the majority class
    label_counts = window_labels_df["window_label"].value_counts()
    if label_counts["baseline"] <= label_counts.get("organic_spike", 0):
        errors.append("Baseline is not the majority class")
    if label_counts["baseline"] <= label_counts.get("fraud_spike", 0):
        errors.append("Baseline is not the majority class")

    # 10. At least one organic and one fraud spike
    if label_counts.get("organic_spike", 0) < 1:
        errors.append("No organic spike windows found")
    if label_counts.get("fraud_spike", 0) < 1:
        errors.append("No fraud spike windows found")

    # 11. Reproducibility check is done externally

    return errors


# ---------------------------------------------------------------------------
# Save data
# ---------------------------------------------------------------------------

def save_data(
    transactions: pd.DataFrame,
    window_labels_df: pd.DataFrame,
    output_dir: str = "data/raw",
) -> tuple[str, str]:
    """Save generated data to CSV files, creating directories if needed."""
    os.makedirs(output_dir, exist_ok=True)

    txn_path = os.path.join(output_dir, "transactions.csv")
    labels_path = os.path.join(output_dir, "window_labels.csv")

    transactions.to_csv(txn_path, index=False)
    window_labels_df.to_csv(labels_path, index=False)

    return txn_path, labels_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(seed: int = DEFAULT_SEED) -> None:
    """Generate synthetic transaction data and save to disk."""
    print("=" * 60)
    print("SUS - Synthetic Transaction Data Generator")
    print("=" * 60)

    # Step 1: Create merchant profiles
    print("\n[1/5] Creating merchant profiles...")
    profiles = create_merchant_profiles(seed)
    print(f"  Created {len(profiles)} merchant profiles")

    # Step 2: Schedule window labels
    print("\n[2/5] Scheduling window labels...")
    window_labels_raw = schedule_window_labels(profiles, NUM_DAYS, seed)
    window_labels_df = pd.DataFrame(window_labels_raw)

    label_dist = window_labels_df["window_label"].value_counts()
    print(f"  Total windows: {len(window_labels_df)}")
    for label, count in label_dist.items():
        print(f"    {label}: {count} ({count / len(window_labels_df) * 100:.1f}%)")

    # Step 3: Generate transactions
    print("\n[3/5] Generating transactions...")
    transactions_df = generate_transactions(profiles, window_labels_raw, seed)

    # Attach transaction counts to window labels
    txn_counts = transactions_df.groupby(["merchant_id", "date"]).size().reset_index(name="transaction_count")
    # Ensure date types match for merge
    window_labels_df["date"] = pd.to_datetime(window_labels_df["date"])
    window_labels_df = window_labels_df.merge(txn_counts, on=["merchant_id", "date"])

    print(f"  Total transactions: {len(transactions_df):,}")

    # Step 4: Validate
    print("\n[4/5] Validating generated data...")
    errors = validate_generated_data(transactions_df, window_labels_df)
    if errors:
        print("  ERRORS found:")
        for e in errors:
            print(f"    ✗ {e}")
        raise ValueError("Validation failed. See errors above.")
    print("  All validation checks passed")

    # Step 5: Save
    print("\n[5/5] Saving data...")
    txn_path, labels_path = save_data(transactions_df, window_labels_df)
    print(f"  Transactions: {txn_path}")
    print(f"  Window labels: {labels_path}")

    # Summary
    print("\n" + "=" * 60)
    print("Dataset Summary")
    print("=" * 60)
    print(f"  Merchants:           {transactions_df['merchant_id'].nunique()}")
    print(f"  Date range:          {transactions_df['date'].min()} to {transactions_df['date'].max()}")
    print(f"  Total transactions:  {len(transactions_df):,}")
    print(f"  Total windows:       {len(window_labels_df)}")
    print(f"\n  Window label distribution:")
    for label, count in label_dist.items():
        print(f"    {label:20s} {count:>5d} ({count / len(window_labels_df) * 100:.1f}%)")

    txn_by_label = window_labels_df.groupby("window_label")["transaction_count"].sum()
    print(f"\n  Transaction counts by class:")
    for label, count in txn_by_label.items():
        print(f"    {label:20s} {count:>10,d}")

    print(f"\n  Avg transactions per baseline day: "
          f"{txn_by_label.get('baseline', 0) / label_dist.get('baseline', 1):.0f}")
    print(f"  Avg transactions per organic spike day: "
          f"{txn_by_label.get('organic_spike', 0) / label_dist.get('organic_spike', 1):.0f}")
    print(f"  Avg transactions per fraud spike day: "
          f"{txn_by_label.get('fraud_spike', 0) / label_dist.get('fraud_spike', 1):.0f}")

    print("\nDone!")


if __name__ == "__main__":
    main()
