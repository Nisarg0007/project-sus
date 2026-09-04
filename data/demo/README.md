# SUS Demo Dataset — Razorpay Payment Fraud Investigation

## Purpose

A realistic, deterministic demo dataset for demonstrating the SUS (Spike Understanding System) fraud investigation platform. This dataset simulates Razorpay-style payment transaction data with engineered anomaly patterns that the ML pipeline detects, classifies, and surfaces as incidents.

## Dataset Overview

| Property | Value |
|----------|-------|
| **Transactions** | 9,612 rows |
| **Window labels** | 275 rows |
| **Date range** | 2025-07-01 to 2025-08-24 (55 days) |
| **Merchants** | 5 |
| **Amount range** | ₹10.15 – ₹3,234.23 |
| **Success rate** | 95.6% |
| **Deterministic** | Yes (seed=42) |

## Files

- `razorpay_demo_transactions.csv` — Transaction-level data (9,612 rows)
- `razorpay_demo_window_labels.csv` — Merchant-day window labels with ground truth (275 rows)
- `generate_demo_data.py` — Deterministic generator script (regenerate with `python data/demo/generate_demo_data.py`)

## Transaction CSV Schema

| Column | Type | Description |
|--------|------|-------------|
| `transaction_id` | string | Unique transaction identifier |
| `merchant_id` | string | Merchant identifier |
| `timestamp` | datetime | Transaction timestamp (YYYY-MM-DD HH:MM:SS) |
| `date` | date | Transaction date (YYYY-MM-DD) |
| `window_label` | string | Ground truth: `baseline`, `fraud_spike`, or `organic_spike` |
| `customer_id` | string | Customer identifier |
| `customer_is_new` | boolean | Whether customer is new (first transaction) |
| `sku_id` | string | Product/SKU identifier |
| `amount` | float | Transaction amount (INR) |
| `payment_status` | string | `success` or `failed` |
| `is_retry` | boolean | Whether this is a retry transaction |
| `device_id` | string | Device identifier |
| `ip_id` | string | IP address identifier |

## Merchants

| Merchant ID | Name | Baseline Volume | Character |
|-------------|------|----------------|-----------|
| `merchant_electronics` | QuickMart Electronics | 22–38 txns/day | Normal baseline — steady activity |
| `merchant_cloudserve` | CloudServe Digital | 25–40 txns/day | **Fraud spike** — sudden concentrated volume |
| `merchant_grocery` | FreshBasket Grocery | 35–60 txns/day | **Organic spike** — legitimate high-traffic event |
| `merchant_fashion` | StyleHub Fashion | 15–28 txns/day | **Moderate suspicious event** — borderline case |
| `merchant_pharmacy` | MediCare Pharmacy | 10–20 txns/day | Always-normal control merchant |

## Engineered Anomaly Patterns

### Pattern A: Fraud Spike (merchant_cloudserve, days 35–39)

**What happens:** Transaction volume jumps from ~30/day to 150–240/day for 5 consecutive days.

**Fraud signals:**
- 75% new customers (vs 12% baseline)
- 15% payment failure rate (vs 4% baseline)
- Higher transaction amounts (₹360–₹2,160 vs ₹200–₹1,200 baseline)
- Device concentration: only 20 unique devices (vs 250+ baseline)
- Coordinated timing patterns

**Expected pipeline output:** 5 high-confidence fraud incidents with z-scores > 2.0

### Pattern B: Organic Spike (merchant_grocery, days 30–33)

**What happens:** Transaction volume jumps from ~45/day to 160–203/day for 4 consecutive days.

**Organic signals:**
- Normal new customer rate (~20%)
- Normal failure rate (~2%)
- Normal amount distribution
- Diverse device/IP usage
- Typical seasonal/promotional pattern

**Expected pipeline output:** Mix of organic_spike and review_required classifications

### Pattern C: Moderate Suspicious Event (merchant_fashion, days 42–44)

**What happens:** Transaction volume jumps from ~22/day to 59–87/day for 3 days.

**Mixed signals:**
- Some fraud indicators but not all
- Borderline z-scores
- Expected to produce review_required or fraud_spike incidents

### Pattern D: Normal Baseline (all merchants, most days)

All merchants maintain steady baseline activity during non-anomaly periods. Natural variation produces some detected spikes that classify as fraud or organic based on behavioral features.

## Expected Investigation Outcome

When running the pipeline with default settings (z_threshold=0.5, min_history_days=3):

| Metric | Expected Value |
|--------|---------------|
| Total windows | 275 |
| Spikes detected | ~92 |
| Fraud incidents | ~67 |
| Organic incidents | ~6 |
| Review required | ~19 |
| Baseline windows | ~183 |

The **merchant_cloudserve** fraud spike (days 35–39) produces the most dramatic and convincing incidents, with z-scores up to 28.4 and fraud probability >99.9%.

## How to Run the Demo

### Option 1: Via the Web UI

1. Open the SUS application
2. Navigate to **Investigate**
3. Click **Upload CSV** in the DATA section
4. Select `data/demo/razorpay_demo_transactions.csv`
5. Wait for validation to complete (you'll see row count, merchant count, date range)
6. Click **Run Investigation** in the RUN section
7. Wait for results — you'll see fraud/organic/review counts
8. Click **VIEW INCIDENTS** to see the incident work queue
9. Click any high-severity incident to review evidence and take action

### Option 2: Via the API

```bash
# Upload the dataset
curl -X POST http://localhost:8000/api/v1/transactions/upload \
  -F "file=@data/demo/razorpay_demo_transactions.csv"

# Note the dataset_id from the response, then run investigation
curl -X POST http://localhost:8000/api/v1/investigations/run \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "<dataset_id>"}'
```

### Option 3: Via Python

```python
import pandas as pd
from src.pipeline import run_pipeline, get_pipeline_summary

txns = pd.read_csv("data/demo/razorpay_demo_transactions.csv")
wls = pd.read_csv("data/demo/razorpay_demo_window_labels.csv")

results = run_pipeline(txns, wls)
summary = get_pipeline_summary(results)
print(summary)
```

## Regenerating the Dataset

To regenerate (same output due to deterministic seed):

```bash
python data/demo/generate_demo_data.py
```

## Design Notes

- **Deterministic:** Fixed seed (42) ensures identical output on every generation
- **Realistic:** Transaction patterns, amounts, and timing mimic real payment data
- **Progressive:** 55 days provides enough history for z-score computation (requires 3+ prior days)
- **Multi-merchant:** 5 merchants with distinct profiles enable meaningful merchant filtering
- **Mixed outcomes:** Produces fraud, organic, and review-required incidents for a complete demo
- **No secrets:** Contains only synthetic data — no real credentials or PII
