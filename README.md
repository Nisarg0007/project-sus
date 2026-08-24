# SUS 🤨

> Not every spike is fraud. But some are definitely sus.

## The Problem

Transaction volume spikes are inherently ambiguous. A sudden surge in payments could mean:

- A legitimate demand surge (festival sale, viral product, promotional campaign)
- A coordinated fraud event (card testing, account abuse, payment abuse)

Traditional anomaly detection systems can identify **when** volume changed, but volume alone cannot reliably explain **why** it changed. A 500% spike from a festival sale and a 500% spike from card testing look identical when you only look at transaction counts.

This ambiguity leads to:
- False positives: Blocking legitimate customers during peak business moments
- False negatives: Missing sophisticated fraud that hides behind organic patterns

## How SUS Works

SUS is a **spike-cause classifier** that distinguishes between three states:

- `baseline` - Normal transaction patterns
- `organic_spike` - Legitimate demand surge
- `fraud_spike` - Coordinated fraud event

### Three-Stage Pipeline

```
Transaction Data
       │
       ▼
Stage 1: Statistical Spike Detection
       │
       ├── No anomaly → Baseline
       │
       ▼
Stage 2: ML Cause Classifier
       │
       ├── Organic spike
       ├── Fraud spike
       │
       ▼
Low-confidence cases only
       │
       ▼
Stage 3: LLM Triage
       │
       ├── Auto-clear
       └── Escalate to human review
```

**Stage 1** detects when something changes (volume anomaly detection).  
**Stage 2** determines the likely cause (spike classification).  
**Stage 3** handles ambiguous cases with contextual reasoning.

## Signals We Analyze

SUS examines multiple behavioral signals to classify spikes:

- **SKU diversity** - Are transactions concentrated on few items (fraud) or spread across inventory (organic)?
- **Price distribution** - Are amounts clustered at round numbers or testing thresholds?
- **Retry-after-failure rate** - Do failed transactions get retried immediately with different cards?
- **Device/IP concentration** - Are many transactions coming from few devices or geolocations?
- **New-account share** - What percentage of transactions come from recently created accounts?
- **Repeat-customer ratio** - Is the spike driven by new or existing customers?

## Project Status

- [x] Project initialization and structure
- [ ] Synthetic transaction data generator
- [ ] Statistical spike detection (Stage 1)
- [ ] Feature engineering pipeline
- [ ] ML cause classifier (Stage 2)
- [ ] LLM triage integration (Stage 3)
- [ ] Dashboard/visualization
- [ ] Evaluation metrics and testing
- [ ] Documentation

## Project Structure

```
project-sus/
├── README.md
├── .gitignore
├── requirements.txt
├── src/
│   └── __init__.py
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   └── processed/
│       └── .gitkeep
├── models/
│   └── .gitkeep
├── notebooks/
│   └── .gitkeep
├── tests/
│   └── __init__.py
└── docs/
    └── .gitkeep
```

## Evaluation Philosophy

We evaluate SUS with metrics that matter for real-world deployment:

**Classification Metrics:**
- Precision, Recall, F1 score
- Confusion matrix

**Business Metrics:**
- False-positive cost (blocking legitimate customers)
- False-negative cost (missing fraud)
- Expected financial cost of errors

The goal is to minimize total cost, not just maximize accuracy.

## Safety

SUS is a **defense-only** system. It:

- Identifies and explains suspicious patterns
- Helps merchants protect their customers
- Does not provide fraud-generation, evasion, or offensive capabilities

We build security tools to protect, not to attack.

## Buildathon

Built for the **Razorpay /buildathon**

**Track 02** — AI Risk Manager

---

*Made with 🤨 by the SUS team*
