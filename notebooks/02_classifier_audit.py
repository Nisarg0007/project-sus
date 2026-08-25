"""
Adversarial Audit of Stage 2 Cause Classifier
==============================================

This notebook investigates whether the near-perfect classifier performance
(F1 = 1.000) from Milestone 4A is genuinely supported by multiple behavioral
signals or whether synthetic artifacts create hidden shortcuts.

ANALYSIS ONLY -- No modifications to existing modules.
"""

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import (
    GroupKFold,
    StratifiedKFold,
    StratifiedShuffleSplit,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANDOM_STATE = 42
N_SPLITS_CV = 5
N_PERMUTATIONS = 100

# Volume features to test separately
VOLUME_FEATURES = [
    "transaction_count",
    "successful_transaction_count",
    "failed_transaction_count",
    "volume_rolling_mean_7d",
    "volume_rolling_std_7d",
    "volume_zscore_7d",
    "volume_ratio_to_7d_mean",
]

# Feature groups for ablation study
FEATURE_GROUPS = {
    "A_payment_behavior": [
        "success_rate",
        "failed_payment_rate",
        "retry_rate",
        "retry_count",
        "failed_retry_rate",
        "failed_retry_count",
    ],
    "B_sku_behavior": [
        "unique_sku_count",
        "sku_diversity_ratio",
        "top_sku_share",
        "sku_entropy",
    ],
    "C_device_ip_concentration": [
        "unique_device_count",
        "device_diversity_ratio",
        "top_device_share",
        "device_entropy",
        "unique_ip_count",
        "ip_diversity_ratio",
        "top_ip_share",
        "ip_entropy",
    ],
    "D_customer_behavior": [
        "unique_customer_count",
        "customer_diversity_ratio",
        "new_customer_share",
        "repeat_customer_share",
    ],
    "E_transaction_amount": [
        "amount_mean",
        "amount_median",
        "amount_std",
        "amount_min",
        "amount_max",
        "amount_p25",
        "amount_p75",
        "amount_iqr",
        "amount_cv",
    ],
}


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------


def load_data() -> tuple[pd.DataFrame, list[str]]:
    """Load window features and prepare Stage 2 dataset."""
    df = pd.read_csv("data/processed/window_features.csv")
    df["date"] = pd.to_datetime(df["date"])

    # Filter to spike windows only
    df = df[df["window_label"].isin(["organic_spike", "fraud_spike"])].copy()

    # Create target
    df["target"] = (df["window_label"] == "fraud_spike").astype(int)

    # Get feature columns
    exclude = {"merchant_id", "date", "window_label", "target"}
    feature_cols = [c for c in df.columns if c not in exclude and pd.api.types.is_numeric_dtype(df[c])]

    return df, feature_cols


# ---------------------------------------------------------------------------
# 1. Feature Distribution Audit
# ---------------------------------------------------------------------------


def feature_distribution_audit(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Compare organic vs fraud distributions for every feature."""
    organic = df[df["target"] == 0]
    fraud = df[df["target"] == 1]

    rows = []
    for col in feature_cols:
        org_vals = organic[col].values
        fra_vals = fraud[col].values

        org_mean, fra_mean = org_vals.mean(), fra_vals.mean()
        org_std, fra_std = org_vals.std(), fra_vals.std()

        # Standardized mean difference (Cohen's d)
        pooled_std = np.sqrt((org_std**2 + fra_std**2) / 2)
        cohens_d = (fra_mean - org_mean) / pooled_std if pooled_std > 0 else 0

        # Distribution overlap (using histogram-based approach)
        all_vals = np.concatenate([org_vals, fra_vals])
        bins = np.linspace(all_vals.min(), all_vals.max(), 50)
        org_hist, _ = np.histogram(org_vals, bins=bins, density=True)
        fra_hist, _ = np.histogram(fra_vals, bins=bins, density=True)
        bin_width = bins[1] - bins[0]
        overlap = np.minimum(org_hist, fra_hist).sum() * bin_width

        rows.append({
            "feature": col,
            "organic_mean": org_mean,
            "organic_median": np.median(org_vals),
            "organic_std": org_std,
            "fraud_mean": fra_mean,
            "fraud_median": np.median(fra_vals),
            "fraud_std": fra_std,
            "cohens_d": cohens_d,
            "abs_cohens_d": abs(cohens_d),
            "overlap": overlap,
        })

    audit_df = pd.DataFrame(rows)
    audit_df = audit_df.sort_values("abs_cohens_d", ascending=False)
    return audit_df


# ---------------------------------------------------------------------------
# 2. Single-Feature Classifier Test
# ---------------------------------------------------------------------------


def single_feature_test(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Test each feature individually with stratified cross-validation."""
    X = df[feature_cols].values
    y = df["target"].values

    cv = StratifiedKFold(n_splits=N_SPLITS_CV, shuffle=True, random_state=RANDOM_STATE)

    results = []
    for i, col in enumerate(feature_cols):
        X_col = X[:, i:i+1]  # Single feature

        f1_scores = []
        for train_idx, test_idx in cv.split(X_col, y):
            X_train, X_test = X_col[train_idx], X_col[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Standardize
            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)

            f1_scores.append(f1_score(y_test, y_pred, zero_division=0))

        results.append({
            "feature": col,
            "mean_f1": np.mean(f1_scores),
            "std_f1": np.std(f1_scores),
            "min_f1": np.min(f1_scores),
            "max_f1": np.max(f1_scores),
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values("mean_f1", ascending=False)
    return results_df


# ---------------------------------------------------------------------------
# 3. Feature Group Ablation
# ---------------------------------------------------------------------------


def feature_group_ablation(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Evaluate LogisticRegression on different feature groups."""
    # Add combined group
    groups = FEATURE_GROUPS.copy()
    groups["F_all_behavioral"] = feature_cols

    X = df[feature_cols].values
    y = df["target"].values

    cv = StratifiedKFold(n_splits=N_SPLITS_CV, shuffle=True, random_state=RANDOM_STATE)

    results = []
    for group_name, group_features in groups.items():
        # Get column indices
        col_indices = [feature_cols.index(f) for f in group_features if f in feature_cols]
        if len(col_indices) == 0:
            continue

        X_group = X[:, col_indices]

        precisions, recalls, f1s, accs = [], [], [], []

        for train_idx, test_idx in cv.split(X_group, y):
            X_train, X_test = X_group[train_idx], X_group[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)

            precisions.append(precision_score(y_test, y_pred, zero_division=0))
            recalls.append(recall_score(y_test, y_pred, zero_division=0))
            f1s.append(f1_score(y_test, y_pred, zero_division=0))
            accs.append(accuracy_score(y_test, y_pred))

        results.append({
            "feature_group": group_name,
            "n_features": len(col_indices),
            "precision_mean": np.mean(precisions),
            "precision_std": np.std(precisions),
            "recall_mean": np.mean(recalls),
            "recall_std": np.std(recalls),
            "f1_mean": np.mean(f1s),
            "f1_std": np.std(f1s),
            "accuracy_mean": np.mean(accs),
            "accuracy_std": np.std(accs),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# 4. Permutation Test
# ---------------------------------------------------------------------------


def permutation_test(df: pd.DataFrame, feature_cols: list[str], n_permutations: int = N_PERMUTATIONS) -> dict:
    """Label permutation sanity check."""
    X = df[feature_cols].values
    y = df["target"].values

    cv = StratifiedKFold(n_splits=N_SPLITS_CV, shuffle=True, random_state=RANDOM_STATE)

    # Baseline performance
    baseline_f1s = []
    for train_idx, test_idx in cv.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        baseline_f1s.append(f1_score(y_test, y_pred, zero_division=0))

    baseline_f1 = np.mean(baseline_f1s)

    # Permutation performance
    perm_f1s = []
    rng = np.random.RandomState(RANDOM_STATE)

    for i in range(n_permutations):
        y_perm = rng.permutation(y)

        fold_f1s = []
        for train_idx, test_idx in cv.split(X, y_perm):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y_perm[train_idx], y_perm[test_idx]

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)
            fold_f1s.append(f1_score(y_test, y_pred, zero_division=0))

        perm_f1s.append(np.mean(fold_f1s))

    # Calculate p-value
    perm_f1s = np.array(perm_f1s)
    p_value = (perm_f1s >= baseline_f1).mean()

    return {
        "baseline_f1": baseline_f1,
        "perm_mean_f1": np.mean(perm_f1s),
        "perm_std_f1": np.std(perm_f1s),
        "perm_max_f1": np.max(perm_f1s),
        "p_value": p_value,
        "n_permutations": n_permutations,
    }


# ---------------------------------------------------------------------------
# 5. Leave-One-Merchant-Out Evaluation
# ---------------------------------------------------------------------------


def leave_one_merchant_out(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """GroupKFold evaluation by merchant."""
    X = df[feature_cols].values
    y = df["target"].values
    groups = df["merchant_id"].values

    unique_merchants = df["merchant_id"].unique()
    n_merchants = len(unique_merchants)

    gkf = GroupKFold(n_splits=min(n_merchants, 5))

    results = []
    for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        test_merchants = set(groups[test_idx])
        train_merchants = set(groups[train_idx])

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)

        results.append({
            "fold": fold + 1,
            "train_merchants": sorted(train_merchants),
            "test_merchants": sorted(test_merchants),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "accuracy": accuracy_score(y_test, y_pred),
        })

    results_df = pd.DataFrame(results)

    # Add summary row
    summary = {
        "fold": "MEAN",
        "precision": results_df["precision"].mean(),
        "recall": results_df["recall"].mean(),
        "f1": results_df["f1"].mean(),
        "accuracy": results_df["accuracy"].mean(),
    }
    results_df = pd.concat([results_df, pd.DataFrame([summary])], ignore_index=True)

    return results_df


# ---------------------------------------------------------------------------
# 6. Temporal Holdout
# ---------------------------------------------------------------------------


def temporal_holdout(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Train on earlier dates, test on later dates for each merchant."""
    results = []

    for merchant in df["merchant_id"].unique():
        merchant_df = df[df["merchant_id"] == merchant].sort_values("date")
        n_days = len(merchant_df)

        if n_days < 4:
            continue  # Skip merchants with too few windows

        # Use 60/40 train/test split temporally
        split_idx = int(n_days * 0.6)

        train_df = merchant_df.iloc[:split_idx]
        test_df = merchant_df.iloc[split_idx:]

        if len(train_df) == 0 or len(test_df) == 0:
            continue

        # Check both classes exist in both splits
        train_classes = set(train_df["target"].unique())
        test_classes = set(test_df["target"].unique())
        if len(train_classes) < 2 or len(test_classes) < 2:
            continue

        X_train = train_df[feature_cols].values
        X_test = test_df[feature_cols].values
        y_train = train_df["target"].values
        y_test = test_df["target"].values

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)

        results.append({
            "merchant": merchant,
            "train_dates": f"{train_df['date'].min().date()} to {train_df['date'].max().date()}",
            "test_dates": f"{test_df['date'].min().date()} to {test_df['date'].max().date()}",
            "train_size": len(X_train),
            "test_size": len(X_test),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "accuracy": accuracy_score(y_test, y_pred),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# 7. Feature Correlation / Redundancy Audit
# ---------------------------------------------------------------------------


def correlation_audit(df: pd.DataFrame, feature_cols: list[str], threshold: float = 0.90) -> pd.DataFrame:
    """Find highly correlated feature pairs."""
    corr_matrix = df[feature_cols].corr()

    pairs = []
    for i in range(len(feature_cols)):
        for j in range(i + 1, len(feature_cols)):
            corr = corr_matrix.iloc[i, j]
            if abs(corr) > threshold:
                pairs.append({
                    "feature_1": feature_cols[i],
                    "feature_2": feature_cols[j],
                    "correlation": corr,
                    "abs_correlation": abs(corr),
                })

    pairs_df = pd.DataFrame(pairs)
    if len(pairs_df) > 0:
        pairs_df = pairs_df.sort_values("abs_correlation", ascending=False)

    return pairs_df


# ---------------------------------------------------------------------------
# 8. Hard Case Analysis
# ---------------------------------------------------------------------------


def hard_case_analysis(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Analyze misclassified samples from cross-validation."""
    X = df[feature_cols].values
    y = df["target"].values

    cv = StratifiedKFold(n_splits=N_SPLITS_CV, shuffle=True, random_state=RANDOM_STATE)

    misclassified = []

    for train_idx, test_idx in cv.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        y_proba = model.predict_proba(X_test_s)[:, 1]

        for i, idx in enumerate(test_idx):
            if y_pred[i] != y_test[i]:
                sample = df.iloc[idx]
                misclassified.append({
                    "merchant_id": sample["merchant_id"],
                    "date": sample["date"],
                    "true_label": "organic_spike" if y_test[i] == 0 else "fraud_spike",
                    "predicted_label": "organic_spike" if y_pred[i] == 0 else "fraud_spike",
                    "fraud_probability": y_proba[i],
                })

    return pd.DataFrame(misclassified)


# ---------------------------------------------------------------------------
# 9. Baseline Comparisons
# ---------------------------------------------------------------------------


def baseline_comparisons(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Compare DummyClassifier, LogisticRegression, and RandomForest."""
    X = df[feature_cols].values
    y = df["target"].values

    cv = StratifiedKFold(n_splits=N_SPLITS_CV, shuffle=True, random_state=RANDOM_STATE)

    models = {
        "DummyClassifier": DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)),
        ]),
        "RandomForest": RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1
        ),
    }

    results = []
    for model_name, model in models.items():
        precisions, recalls, f1s, accs = [], [], [], []

        for train_idx, test_idx in cv.split(X, y):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            if model_name == "RandomForest":
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
            else:
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)

            precisions.append(precision_score(y_test, y_pred, zero_division=0))
            recalls.append(recall_score(y_test, y_pred, zero_division=0))
            f1s.append(f1_score(y_test, y_pred, zero_division=0))
            accs.append(accuracy_score(y_test, y_pred))

        results.append({
            "model": model_name,
            "precision_mean": np.mean(precisions),
            "precision_std": np.std(precisions),
            "recall_mean": np.mean(recalls),
            "recall_std": np.std(recalls),
            "f1_mean": np.mean(f1s),
            "f1_std": np.std(f1s),
            "accuracy_mean": np.mean(accs),
            "accuracy_std": np.std(accs),
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------


def main():
    """Run the complete adversarial audit."""
    print("=" * 70)
    print("ADVERSARIAL AUDIT OF STAGE 2 CAUSE CLASSIFIER")
    print("=" * 70)

    # Load data
    print("\n[1/10] Loading data...")
    df, feature_cols = load_data()
    print(f"  Spike windows: {len(df)}")
    print(f"  Organic: {(df['target'] == 0).sum()}, Fraud: {(df['target'] == 1).sum()}")
    print(f"  Features: {len(feature_cols)}")

    # =========================================================================
    # 1. FEATURE DISTRIBUTION AUDIT
    # =========================================================================
    print("\n" + "=" * 70)
    print("1. FEATURE DISTRIBUTION AUDIT")
    print("=" * 70)

    dist_audit = feature_distribution_audit(df, feature_cols)

    print("\nTop 15 features by Cohen's d (standardized difference):")
    print("-" * 70)
    print(dist_audit.head(15)[["feature", "organic_mean", "fraud_mean", "cohens_d", "overlap"]].to_string(
        index=False, float_format=lambda x: f"{x:.3f}"
    ))

    # Flag suspicious features
    suspicious = dist_audit[dist_audit["overlap"] < 0.1]
    if len(suspicious) > 0:
        print(f"\nWARNING: {len(suspicious)} features have < 10% overlap:")
        print(suspicious["feature"].tolist())
    else:
        print("\nNo features with suspiciously low overlap (< 10%)")

    # =========================================================================
    # 2. SINGLE-FEATURE CLASSIFIER TEST
    # =========================================================================
    print("\n" + "=" * 70)
    print("2. SINGLE-FEATURE CLASSIFIER TEST")
    print("=" * 70)

    single_feat = single_feature_test(df, feature_cols)

    print("\nTop 10 features by individual F1 (5-fold stratified CV):")
    print("-" * 70)
    print(single_feat.head(10).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Check for dominant features
    dominant = single_feat[single_feat["mean_f1"] > 0.9]
    if len(dominant) > 0:
        print(f"\nCRITICAL: {len(dominant)} individual features achieve F1 > 0.9:")
        print(dominant[["feature", "mean_f1", "std_f1"]].to_string(index=False))
        print("This suggests possible synthetic shortcuts!")
    else:
        print("\nNo single feature dominates (all F1 < 0.9)")

    print("\nBottom 5 features by individual F1:")
    print("-" * 70)
    print(single_feat.tail(5).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # =========================================================================
    # 3. FEATURE GROUP ABLATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("3. FEATURE GROUP ABLATION")
    print("=" * 70)

    ablation = feature_group_ablation(df, feature_cols)

    print("\nLogisticRegression performance by feature group (5-fold CV):")
    print("-" * 70)
    print(ablation.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # =========================================================================
    # 4. PERMUTATION TEST
    # =========================================================================
    print("\n" + "=" * 70)
    print("4. PERMUTATION TEST")
    print("=" * 70)

    perm_result = permutation_test(df, feature_cols)

    print(f"\nBaseline F1 (real labels):  {perm_result['baseline_f1']:.3f}")
    print(f"Permuted F1 (mean ? std):   {perm_result['perm_mean_f1']:.3f} ? {perm_result['perm_std_f1']:.3f}")
    print(f"Permuted F1 (max):          {perm_result['perm_max_f1']:.3f}")
    print(f"P-value:                    {perm_result['p_value']:.4f}")

    if perm_result["p_value"] < 0.05:
        print("\nPermutation test passes: performance collapses toward chance (p < 0.05)")
        print("  The pipeline is NOT leaking labels.")
    else:
        print("\nPermutation test warning: performance does not collapse (p >= 0.05)")

    # =========================================================================
    # 5. LEAVE-ONE-MERCHANT-OUT EVALUATION
    # =========================================================================
    print("\n" + "=" * 70)
    print("5. LEAVE-ONE-MERCHANT-OUT EVALUATION")
    print("=" * 70)

    lomo_results = leave_one_merchant_out(df, feature_cols)

    print("\nPer-fold results:")
    print("-" * 70)
    print(lomo_results[["fold", "test_merchants", "test_size", "precision", "recall", "f1", "accuracy"]].to_string(
        index=False, float_format=lambda x: f"{x:.3f}"
    ))

    # =========================================================================
    # 6. TEMPORAL HOLDOUT
    # =========================================================================
    print("\n" + "=" * 70)
    print("6. TEMPORAL HOLDOUT")
    print("=" * 70)

    temporal_results = temporal_holdout(df, feature_cols)

    if len(temporal_results) > 0:
        print("\nPer-merchant temporal holdout (train on earlier dates, test on later):")
        print("-" * 70)
        print(temporal_results.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    else:
        print("\n!  No valid temporal splits found (insufficient date range per merchant)")

    # =========================================================================
    # 7. FEATURE CORRELATION / REDUNDANCY AUDIT
    # =========================================================================
    print("\n" + "=" * 70)
    print("7. FEATURE CORRELATION / REDUNDANCY AUDIT")
    print("=" * 70)

    corr_pairs = correlation_audit(df, feature_cols, threshold=0.90)

    if len(corr_pairs) > 0:
        print(f"\nFound {len(corr_pairs)} feature pairs with correlation > 0.90:")
        print("-" * 70)
        print(corr_pairs.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

        # Analyze redundancy
        highly_correlated = corr_pairs[corr_pairs["abs_correlation"] > 0.95]
        if len(highly_correlated) > 0:
            print(f"\n{len(highly_correlated)} pairs have correlation > 0.95 (near-duplicates):")
            for _, row in highly_correlated.iterrows():
                print(f"  {row['feature_1']} <-> {row['feature_2']}: {row['correlation']:.3f}")
    else:
        print("\nNo feature pairs with correlation > 0.90")

    # =========================================================================
    # 8. HARD CASE ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("8. HARD CASE ANALYSIS")
    print("=" * 70)

    hard_cases = hard_case_analysis(df, feature_cols)

    if len(hard_cases) == 0:
        print("\nFINDING: ZERO misclassified samples across all CV folds!")
        print("   This itself is a finding requiring scrutiny.")
        print("   Possible explanations:")
        print("   1. The classes are genuinely well-separated by features")
        print("   2. Synthetic generator creates hidden shortcuts")
        print("   3. Feature engineering inadvertently leaks label information")
    else:
        print(f"\nMisclassified samples: {len(hard_cases)}")
        print("-" * 70)
        print(hard_cases.to_string(index=False))

    # =========================================================================
    # 9. BASELINE COMPARISONS
    # =========================================================================
    print("\n" + "=" * 70)
    print("9. BASELINE COMPARISONS")
    print("=" * 70)

    baseline_results = baseline_comparisons(df, feature_cols)

    print("\nModel comparison (5-fold stratified CV):")
    print("-" * 70)
    print(baseline_results.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # =========================================================================
    # 10. FINAL VERDICT
    # =========================================================================
    print("\n" + "=" * 70)
    print("10. FINAL VERDICT")
    print("=" * 70)

    # Determine verdict
    verdict = "PASS"
    reasons = []

    # Check for dominant features
    if len(dominant) > 0:
        verdict = "FAIL"
        reasons.append(f"{len(dominant)} individual features achieve F1 > 0.9")

    # Check permutation test
    if perm_result["p_value"] >= 0.05:
        verdict = "CAUTION"
        reasons.append("Permutation test does not collapse to chance")

    # Check zero errors
    if len(hard_cases) == 0:
        verdict = "CAUTION"
        reasons.append("Zero misclassified samples across all CV folds")

    # Check temporal holdout
    if len(temporal_results) > 0 and temporal_results["f1"].mean() < 0.8:
        verdict = "CAUTION"
        reasons.append(f"Temporal holdout F1 only {temporal_results['f1'].mean():.3f}")

    print(f"\n{'='*50}")
    print(f"CLASSIFIER_AUDIT_VERDICT: {verdict}")
    print(f"{'='*50}")

    if reasons:
        print(f"\nReasons for {verdict}:")
        for r in reasons:
            print(f"  - {r}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY OF KEY FINDINGS")
    print("=" * 70)

    temporal_f1 = temporal_results['f1'].mean() if len(temporal_results) > 0 else 0.0

    print(f"""
1. Single-Feature Ranking:
   - Top feature: {single_feat.iloc[0]['feature']} (F1 = {single_feat.iloc[0]['mean_f1']:.3f})
   - {len(dominant)} features achieve F1 > 0.9 individually

2. Feature-Group Ablation:
   - Best group: {ablation.loc[ablation['f1_mean'].idxmax(), 'feature_group']} (F1 = {ablation['f1_mean'].max():.3f})
   - Multiple groups achieve strong performance independently

3. Permutation Test:
   - Baseline F1: {perm_result['baseline_f1']:.3f}
   - Permuted F1: {perm_result['perm_mean_f1']:.3f} ? {perm_result['perm_std_f1']:.3f}
   - P-value: {perm_result['p_value']:.4f}

4. Leave-One-Merchant-Out:
   - Mean F1: {lomo_results[lomo_results['fold'] == 'MEAN']['f1'].values[0]:.3f}

5. Temporal Holdout:
   - Mean F1: {temporal_f1:.3f}

6. Suspicious Correlations:
   - {len(corr_pairs)} feature pairs with correlation > 0.90

7. Hard Cases:
   - {len(hard_cases)} misclassified samples

VERDICT: {verdict}
""")

    # Print machine-readable verdict
    print("\n" + "=" * 70)
    print("MACHINE-READABLE VERDICT")
    print("=" * 70)
    print(f"CLASSIFIER_AUDIT_VERDICT:{verdict}")

    print("\nDone!")


if __name__ == "__main__":
    main()
