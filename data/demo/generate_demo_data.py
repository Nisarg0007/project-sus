#!/usr/bin/env python3
"""
Deterministic demo dataset generator for SUS.

Creates a realistic payment fraud investigation dataset with engineered
anomaly patterns that the existing ML pipeline will detect and classify.

Produces:
  data/demo/razorpay_demo_transactions.csv
  data/demo/razorpay_demo_window_labels.csv

Usage:
    python data/demo/generate_demo_data.py
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Deterministic seed
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
START_DATE = datetime(2025, 7, 1)
NUM_DAYS = 55  # 55 days of data

MERCHANTS = {
    # Baseline merchant — normal steady activity, no anomalies
    "merchant_electronics": {
        "name": "QuickMart Electronics",
        "baseline_range": (22, 38),  # transactions per day
        "amount_range": (150, 800),
        "sku_pool_size": 120,
        "customer_pool_size": 600,
        "new_customer_rate": 0.15,
        "failure_rate": 0.03,
        "retry_rate": 0.08,
        "device_pool_size": 400,
        "ip_pool_size": 300,
    },
    # Fraud spike merchant — sudden volume spike with fraud signals
    "merchant_cloudserve": {
        "name": "CloudServe Digital",
        "baseline_range": (25, 40),
        "amount_range": (200, 1200),
        "sku_pool_size": 40,
        "customer_pool_size": 300,
        "new_customer_rate": 0.12,
        "failure_rate": 0.04,
        "retry_rate": 0.07,
        "device_pool_size": 250,
        "ip_pool_size": 200,
    },
    # Organic spike merchant — legitimate high-traffic event
    "merchant_grocery": {
        "name": "FreshBasket Grocery",
        "baseline_range": (35, 60),
        "amount_range": (20, 150),
        "sku_pool_size": 200,
        "customer_pool_size": 1200,
        "new_customer_rate": 0.20,
        "failure_rate": 0.02,
        "retry_rate": 0.05,
        "device_pool_size": 800,
        "ip_pool_size": 600,
    },
    # Moderate suspicious event — borderline case
    "merchant_fashion": {
        "name": "StyleHub Fashion",
        "baseline_range": (15, 28),
        "amount_range": (80, 500),
        "sku_pool_size": 80,
        "customer_pool_size": 400,
        "new_customer_rate": 0.18,
        "failure_rate": 0.05,
        "retry_rate": 0.10,
        "device_pool_size": 300,
        "ip_pool_size": 250,
    },
    # Always-normal merchant — control
    "merchant_pharmacy": {
        "name": "MediCare Pharmacy",
        "baseline_range": (10, 20),
        "amount_range": (10, 80),
        "sku_pool_size": 150,
        "customer_pool_size": 500,
        "new_customer_rate": 0.10,
        "failure_rate": 0.01,
        "retry_rate": 0.03,
        "device_pool_size": 350,
        "ip_pool_size": 280,
    },
}

# ---------------------------------------------------------------------------
# Anomaly patterns — engineered windows
# ---------------------------------------------------------------------------

# Fraud spike: days 35-39 (merchant_cloudserve)
# Sudden concentrated volume, new customers, high amounts, device clustering,
# elevated failures — should look like coordinated fraud.
FRAUD_SPIKE_DAYS = list(range(35, 40))  # 5 days
FRAUD_SPIKE_MULTIPLIER = 6  # 6x normal volume
FRAUD_SPIKE_NEW_CUSTOMER_RATE = 0.75  # mostly new accounts
FRAUD_SPIKE_FAILURE_RATE = 0.15  # elevated failures
FRAUD_SPIKE_AMOUNT_BUMP = 1.8  # higher amounts
FRAUD_SPIKE_DEVICE_REUSE = True  # same devices across transactions

# Organic spike: days 30-33 (merchant_grocery)
# High volume but normal behavioral patterns — flash sale / festival
ORGANIC_SPIKE_DAYS = list(range(30, 34))  # 4 days
ORGANIC_SPIKE_MULTIPLIER = 3.5  # 3.5x normal volume
# Behavioral patterns remain normal

# Moderate suspicious event: days 42-44 (merchant_fashion)
# Volume increase with some but not all fraud signals
MODERATE_SPIKE_DAYS = list(range(42, 45))
MODERATE_SPIKE_MULTIPLIER = 3.5


# ---------------------------------------------------------------------------
# Transaction generation
# ---------------------------------------------------------------------------

def generate_transactions() -> list[dict]:
    """Generate all transactions deterministically."""
    all_txns: list[dict] = []
    txn_counter = 0

    for day_offset in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")

        for merchant_id, config in MERCHANTS.items():
            # Determine transaction count for this day
            base_count = random.randint(*config["baseline_range"])
            txn_count = base_count

            # Apply anomaly multipliers
            is_fraud_spike = merchant_id == "merchant_cloudserve" and day_offset in FRAUD_SPIKE_DAYS
            is_organic_spike = merchant_id == "merchant_grocery" and day_offset in ORGANIC_SPIKE_DAYS
            is_moderate_spike = merchant_id == "merchant_fashion" and day_offset in MODERATE_SPIKE_DAYS

            if is_fraud_spike:
                txn_count = int(base_count * FRAUD_SPIKE_MULTIPLIER)
            elif is_organic_spike:
                txn_count = int(base_count * ORGANIC_SPIKE_MULTIPLIER)
            elif is_moderate_spike:
                txn_count = int(base_count * MODERATE_SPIKE_MULTIPLIER)

            # Determine behavioral parameters for this day
            new_customer_rate = config["new_customer_rate"]
            failure_rate = config["failure_rate"]
            amount_low, amount_high = config["amount_range"]
            device_pool = list(range(1, config["device_pool_size"] + 1))

            if is_fraud_spike:
                new_customer_rate = FRAUD_SPIKE_NEW_CUSTOMER_RATE
                failure_rate = FRAUD_SPIKE_FAILURE_RATE
                amount_high = int(amount_high * FRAUD_SPIKE_AMOUNT_BUMP)
                # Fraud: only 20 devices used (concentrated)
                device_pool = list(range(1, 21))

            # Generate window_label (ground truth for training, not used in demo upload)
            if is_fraud_spike:
                window_label = "fraud_spike"
            elif is_organic_spike:
                window_label = "organic_spike"
            else:
                window_label = "baseline"

            for i in range(txn_count):
                txn_counter += 1

                # Timestamp: spread across the day
                hour = random.randint(0, 23)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                ts = current_date.replace(hour=hour, minute=minute, second=second)
                timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")

                # Transaction ID
                txn_id = f"txn_{merchant_id}_{date_str}_{i:06d}"

                # Customer
                customer_pool_size = config["customer_pool_size"]
                is_new = random.random() < new_customer_rate
                if is_new:
                    customer_id = f"cust_{merchant_id}_new_{date_str}_{i:04d}"
                else:
                    customer_id = f"cust_{merchant_id}_existing_{random.randint(1, customer_pool_size)}"

                # SKU
                sku_id = f"sku_{random.randint(1, config['sku_pool_size']):04d}"

                # Amount
                if is_fraud_spike:
                    # Fraud: slightly higher amounts, occasionally very high
                    if random.random() < 0.1:
                        amount = round(random.uniform(amount_low * 2, amount_high * 1.5), 2)
                    else:
                        amount = round(random.uniform(amount_low, amount_high), 2)
                else:
                    amount = round(random.uniform(amount_low, amount_high), 2)

                # Payment status
                if random.random() < failure_rate:
                    payment_status = "failed"
                else:
                    payment_status = "success"

                # Retry
                is_retry = random.random() < config["retry_rate"]

                # Device
                if is_fraud_spike and FRAUD_SPIKE_DEVICE_REUSE:
                    # Fraud: concentrated on few devices
                    device_id = f"dev_{random.choice(device_pool):05d}"
                else:
                    device_id = f"dev_{random.choice(device_pool):05d}"

                # IP
                ip_pool_size = config["ip_pool_size"]
                ip_id = f"ip_{random.randint(1, ip_pool_size):05d}"

                all_txns.append({
                    "transaction_id": txn_id,
                    "merchant_id": merchant_id,
                    "timestamp": timestamp_str,
                    "date": date_str,
                    "window_label": window_label,
                    "customer_id": customer_id,
                    "customer_is_new": is_new,
                    "sku_id": sku_id,
                    "amount": amount,
                    "payment_status": payment_status,
                    "is_retry": is_retry,
                    "device_id": device_id,
                    "ip_id": ip_id,
                })

    return all_txns


def generate_window_labels(transactions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transactions into window labels (merchant_id, date, window_label, transaction_count)."""
    windows = (
        transactions.groupby(["merchant_id", "date", "window_label"])
        .size()
        .reset_index(name="transaction_count")
    )
    return windows[["merchant_id", "date", "window_label", "transaction_count"]]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate the demo dataset."""
    output_dir = Path(__file__).parent

    print("=" * 60)
    print("SUS Demo Dataset Generator")
    print("=" * 60)

    # Generate transactions
    print("\n[1/3] Generating transactions...")
    txns = generate_transactions()
    txn_df = pd.DataFrame(txns)
    print(f"  Generated {len(txn_df):,} transactions")

    # Generate window labels
    print("[2/3] Generating window labels...")
    window_df = generate_window_labels(txn_df)
    print(f"  Generated {len(window_df)} window labels")

    # Save CSVs
    print("[3/3] Saving files...")
    txn_path = output_dir / "razorpay_demo_transactions.csv"
    window_path = output_dir / "razorpay_demo_window_labels.csv"

    txn_df.to_csv(txn_path, index=False)
    window_df.to_csv(window_path, index=False)

    print(f"\n  Transactions: {txn_path}")
    print(f"  Window labels: {window_path}")

    # Summary
    print(f"\n{'=' * 60}")
    print("DATASET SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total transactions: {len(txn_df):,}")
    print(f"  Date range: {txn_df['date'].min()} to {txn_df['date'].max()}")
    print(f"  Merchants: {txn_df['merchant_id'].nunique()}")
    print(f"  Window labels: {len(window_df)}")

    print(f"\n  Merchant breakdown:")
    for merchant in sorted(txn_df["merchant_id"].unique()):
        m_txns = txn_df[txn_df["merchant_id"] == merchant]
        print(f"    {merchant}: {len(m_txns):,} txns, {m_txns['date'].nunique()} days")

    print(f"\n  Window label distribution:")
    for label, count in window_df["window_label"].value_counts().items():
        print(f"    {label}: {count} windows")

    print(f"\n  Fraud spike days (merchant_cloudserve): days {FRAUD_SPIKE_DAYS}")
    print(f"  Organic spike days (merchant_grocery): days {ORGANIC_SPIKE_DAYS}")
    print(f"  Moderate spike days (merchant_fashion): days {MODERATE_SPIKE_DAYS}")

    print(f"\n  Amount range: {txn_df['amount'].min():.2f} - {txn_df['amount'].max():.2f}")
    print(f"  Success rate: {(txn_df['payment_status'] == 'success').mean():.1%}")
    print(f"  New customer rate: {txn_df['customer_is_new'].mean():.1%}")

    print(f"\n{'=' * 60}")
    print("Done!")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
