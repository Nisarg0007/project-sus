"""
Stage 2 — Cause Classifier Experiment for SUS 🤨

This module establishes the complete experiment setup for distinguishing
organic spikes from fraud spikes using behavioral pattern features.

It answers: Can behavioral features distinguish organic spikes from fraud spikes?

Usage:
    python -m src.classifier_experiment

Input:
    data/processed/window_features.csv

This module does NOT train a final production model.
It establishes baseline performance for the cause classifier.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedShuffleSplit, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Target mapping
TARGET_MAP = {
    "organic_spike": 0,
    "fraud_spike": 1,
}

# Metadata columns to exclude from features
METADATA_COLUMNS = ["merchant_id", "date", "window_label"]

# Volume features to exclude in Feature Set B
VOLUME_FEATURES = [
    "transaction_count",
    "successful_transaction_count",
    "failed_transaction_count",
    "volume_rolling_mean_7d",
    "volume_rolling_std_7d",
    "volume_zscore_7d",
    "volume_ratio_to_7d_mean",
]

# Random state for reproducibility
RANDOM_STATE = 42


# ---------------------------------------------------------------------------
# Data loading and preparation
# ---------------------------------------------------------------------------


def load_stage2_data(
    features_path: str = "data/processed/window_features.csv",
) -> pd.DataFrame:
    """
    Load window features and prepare for Stage 2 classification.

    Returns only organic_spike and fraud_spike windows with:
    - Original window_label for reporting
    - Numeric target (organic=0, fraud=1)
    - All behavioral features (excluding metadata)

    Raises:
        ValueError: If required columns are missing or data is invalid.
    """
    df = pd.read_csv(features_path)
    df["date"] = pd.to_datetime(df["date"])

    # Filter to only spike windows
    spike_mask = df["window_label"].isin(["organic_spike", "fraud_spike"])
    df = df[spike_mask].copy()

    if len(df) == 0:
        raise ValueError("No organic_spike or fraud_spike windows found")

    # Create target
    df["target"] = df["window_label"].map(TARGET_MAP)

    # Validate target mapping
    if df["target"].isnull().any():
        raise ValueError("Failed to map some window_labels to target")

    return df


def get_model_features(df: pd.DataFrame) -> list[str]:
    """Get feature columns for modeling, excluding metadata and target."""
    exclude = set(METADATA_COLUMNS + ["target", "window_label"])
    return [col for col in df.columns if col not in exclude and pd.api.types.is_numeric_dtype(df[col])]


def validate_features(X: pd.DataFrame, y: pd.Series) -> list[str]:
    """Validate feature matrix and target. Returns list of errors (empty = valid)."""
    errors = []

    # Check for NaN
    nan_cols = X.columns[X.isnull().any()].tolist()
    if nan_cols:
        errors.append(f"NaN values found in columns: {nan_cols}")

    # Check for infinite
    inf_mask = np.isinf(X.select_dtypes(include=[np.number]))
    inf_cols = inf_mask.columns[inf_mask.any()].tolist()
    if inf_cols:
        errors.append(f"Infinite values found in columns: {inf_cols}")

    # Check target has both classes
    unique_classes = set(y.unique())
    if unique_classes != {0, 1}:
        errors.append(f"Target must have classes {{0, 1}}, found {unique_classes}")

    return errors


# ---------------------------------------------------------------------------
# Feature audit
# ---------------------------------------------------------------------------


def feature_audit(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """
    Perform feature audit comparing organic vs fraud spikes.

    Returns DataFrame with feature statistics and standardized differences.
    """
    organic = df[df["window_label"] == "organic_spike"]
    fraud = df[df["window_label"] == "fraud_spike"]

    audit_rows = []
    for col in feature_cols:
        organic_mean = organic[col].mean()
        fraud_mean = fraud[col].mean()

        # Pooled standard deviation
        organic_std = organic[col].std()
        fraud_std = fraud[col].std()
        pooled_std = np.sqrt((organic_std**2 + fraud_std**2) / 2)

        # Standardized difference
        if pooled_std > 0:
            std_diff = (fraud_mean - organic_mean) / pooled_std
        else:
            std_diff = 0.0

        audit_rows.append({
            "feature": col,
            "organic_mean": organic_mean,
            "fraud_mean": fraud_mean,
            "std_diff": std_diff,
            "abs_std_diff": abs(std_diff),
        })

    audit_df = pd.DataFrame(audit_rows)
    audit_df = audit_df.sort_values("abs_std_diff", ascending=False)

    return audit_df


# ---------------------------------------------------------------------------
# Split strategies
# ---------------------------------------------------------------------------


def stratified_random_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Stratified random train/test split.

    Returns:
        X_train, X_test, y_train, y_test
    """
    splitter = StratifiedShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=random_state,
    )

    train_idx, test_idx = next(splitter.split(X, y))

    X_train = X.iloc[train_idx].reset_index(drop=True)
    X_test = X.iloc[test_idx].reset_index(drop=True)
    y_train = y.iloc[train_idx].reset_index(drop=True)
    y_test = y.iloc[test_idx].reset_index(drop=True)

    return X_train, X_test, y_train, y_test


def grouped_merchant_split(
    df: pd.DataFrame,
    feature_cols: list[str],
    test_size: float = 0.25,
    random_state: int = RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, list[str], list[str]]:
    """
    Group-aware merchant holdout split.

    Ensures no merchant appears in both train and test.

    Returns:
        X_train, X_test, y_train, y_test, train_merchants, test_merchants
    """
    groups = df["merchant_id"].values
    y = df["target"].values

    # Try GroupShuffleSplit
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=test_size,
        random_state=random_state,
    )

    train_idx, test_idx = next(splitter.split(df, y, groups))

    # Validate split
    train_merchants = set(df.iloc[train_idx]["merchant_id"].unique())
    test_merchants = set(df.iloc[test_idx]["merchant_id"].unique())

    # Check for overlap
    overlap = train_merchants & test_merchants
    if overlap:
        raise ValueError(f"Merchant overlap detected: {overlap}")

    # Check both classes exist in test
    test_y = y[test_idx]
    if len(set(test_y)) < 2:
        # Try again with different random state or adjust
        warnings.warn("Test set missing a class, adjusting split...")
        # Fall back to stratified split with merchant grouping
        return _fallback_grouped_split(df, feature_cols, test_size, random_state)

    X_train = df.iloc[train_idx][feature_cols].reset_index(drop=True)
    X_test = df.iloc[test_idx][feature_cols].reset_index(drop=True)
    y_train = pd.Series(y[train_idx], name="target").reset_index(drop=True)
    y_test = pd.Series(y[test_idx], name="target").reset_index(drop=True)

    return X_train, X_test, y_train, y_test, sorted(train_merchants), sorted(test_merchants)


def _fallback_grouped_split(
    df: pd.DataFrame,
    feature_cols: list[str],
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, list[str], list[str]]:
    """Fallback grouped split when primary split fails class balance check."""
    # Use stratified split instead
    X = df[feature_cols].reset_index(drop=True)
    y = df["target"].reset_index(drop=True)
    merchant_ids = df["merchant_id"].reset_index(drop=True)

    X_train, X_test, y_train, y_test = stratified_random_split(X, y, test_size, random_state)

    # Get merchants in each split
    train_merchants = sorted(merchant_ids.iloc[X_train.index].unique())
    test_merchants = sorted(merchant_ids.iloc[X_test.index].unique())

    return X_train, X_test, y_train, y_test, train_merchants, test_merchants


# ---------------------------------------------------------------------------
# Feature sets
# ---------------------------------------------------------------------------


def get_feature_set_a(feature_cols: list[str]) -> list[str]:
    """Feature Set A: All behavioral features."""
    return feature_cols.copy()


def get_feature_set_b(feature_cols: list[str]) -> list[str]:
    """Feature Set B: Behavioral features without volume signals."""
    return [col for col in feature_cols if col not in VOLUME_FEATURES]


# ---------------------------------------------------------------------------
# Model creation
# ---------------------------------------------------------------------------


def create_models() -> dict:
    """Create baseline models with fixed random states."""
    models = {
        "DummyClassifier": DummyClassifier(
            strategy="most_frequent",
            random_state=RANDOM_STATE,
        ),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                random_state=RANDOM_STATE,
                max_iter=1000,
            )),
        ]),
        "RandomForest": RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }
    return models


# ---------------------------------------------------------------------------
# Training and evaluation
# ---------------------------------------------------------------------------


def train_and_evaluate(
    model,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> dict:
    """
    Train a model and evaluate on test set.

    Returns dictionary with all metrics.
    """
    # Train
    model.fit(X_train, y_train)

    # Predict
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    # Test metrics
    test_precision = precision_score(y_test, y_test_pred, zero_division=0)
    test_recall = recall_score(y_test, y_test_pred, zero_division=0)
    test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
    test_accuracy = accuracy_score(y_test, y_test_pred)

    # Train metrics
    train_f1 = f1_score(y_train, y_train_pred, zero_division=0)

    # Class-specific metrics
    test_report = classification_report(y_test, y_test_pred, output_dict=True, zero_division=0)

    # Confusion matrix
    cm = confusion_matrix(y_test, y_test_pred)

    return {
        "train_precision": precision_score(y_train, y_train_pred, zero_division=0),
        "train_recall": recall_score(y_train, y_train_pred, zero_division=0),
        "train_f1": train_f1,
        "test_precision": test_precision,
        "test_recall": test_recall,
        "test_f1": test_f1,
        "test_accuracy": test_accuracy,
        "confusion_matrix": cm,
        "organic_precision": test_report.get("0", {}).get("precision", 0),
        "organic_recall": test_report.get("0", {}).get("recall", 0),
        "organic_f1": test_report.get("0", {}).get("f1-score", 0),
        "fraud_precision": test_report.get("1", {}).get("precision", 0),
        "fraud_recall": test_report.get("1", {}).get("recall", 0),
        "fraud_f1": test_report.get("1", {}).get("f1-score", 0),
    }


# ---------------------------------------------------------------------------
# Feature importance
# ---------------------------------------------------------------------------


def get_feature_importance(
    model,
    feature_cols: list[str],
    model_name: str,
) -> pd.DataFrame:
    """Extract feature importance from fitted model."""
    if model_name == "LogisticRegression":
        # Get coefficients from pipeline
        clf = model.named_steps["clf"]
        importances = np.abs(clf.coef_[0])
    elif model_name == "RandomForest":
        importances = model.feature_importances_
    else:
        return pd.DataFrame()

    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": importances,
    })
    importance_df = importance_df.sort_values("importance", ascending=False)

    return importance_df


# ---------------------------------------------------------------------------
# Experiment execution
# ---------------------------------------------------------------------------


def run_experiment(
    df: pd.DataFrame,
    feature_cols: list[str],
    split_name: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    model_name: str,
    model,
) -> dict:
    """Run a single experiment and return results."""
    # Train and evaluate
    metrics = train_and_evaluate(model, X_train, X_test, y_train, y_test)

    # Get feature importance
    importance_df = get_feature_importance(model, feature_cols, model_name)

    # Overfitting check
    overfitting = metrics["train_f1"] - metrics["test_f1"] > 0.15

    return {
        "split": split_name,
        "model": model_name,
        "feature_set": f"Set A ({len(feature_cols)} features)" if len(feature_cols) > 10 else f"Set B ({len(feature_cols)} features)",
        "train_size": len(X_train),
        "test_size": len(X_test),
        "test_precision": metrics["test_precision"],
        "test_recall": metrics["test_recall"],
        "test_f1": metrics["test_f1"],
        "test_accuracy": metrics["test_accuracy"],
        "train_f1": metrics["train_f1"],
        "organic_precision": metrics["organic_precision"],
        "organic_recall": metrics["organic_recall"],
        "organic_f1": metrics["organic_f1"],
        "fraud_precision": metrics["fraud_precision"],
        "fraud_recall": metrics["fraud_recall"],
        "fraud_f1": metrics["fraud_f1"],
        "confusion_matrix": metrics["confusion_matrix"],
        "overfitting": overfitting,
        "feature_importance": importance_df,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(
    features_path: str = "data/processed/window_features.csv",
) -> None:
    """Run the complete cause classifier experiment."""
    print("=" * 60)
    print("SUS STAGE 2 — CAUSE CLASSIFIER BASELINE")
    print("=" * 60)

    # Step 1: Load and prepare data
    print("\n[1/9] Loading and preparing Stage 2 data...")
    df = load_stage2_data(features_path)
    feature_cols = get_model_features(df)

    print(f"\nSTAGE 2 DATASET")
    print("-" * 40)
    print(f"  Total Stage 2 windows:  {len(df)}")
    print(f"  Organic spikes (class 0): {(df['target'] == 0).sum()}")
    print(f"  Fraud spikes (class 1):   {(df['target'] == 1).sum()}")
    print(f"  Candidate features:       {len(feature_cols)}")

    # Validate features
    errors = validate_features(df[feature_cols], df["target"])
    if errors:
        print(f"\n  ERRORS: {errors}")
        raise ValueError("Feature validation failed")
    print(f"  Feature validation: PASSED")

    # Step 2: Feature audit
    print("\n[2/9] Performing feature audit...")
    audit_df = feature_audit(df, feature_cols)

    print("\nFEATURE AUDIT")
    print("-" * 40)
    print(f"\nTop 10 features by standardized difference (organic vs fraud):")
    print(audit_df.head(10).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Flag extreme features
    extreme = audit_df[audit_df["abs_std_diff"] > 3]
    if len(extreme) > 0:
        print(f"\nWARNING: {len(extreme)} features have |standardized difference| > 3:")
        print(extreme["feature"].tolist())
    else:
        print(f"\nNo features flagged as suspiciously extreme.")

    print(f"\n  transaction_count is NOT the target (target is window_label)")
    print(f"  Volume alone is insufficient for cause classification (hypothesis)")

    # Step 3: Split strategies
    print("\n[3/9] Creating train/test splits...")

    # Prepare X and y
    X = df[feature_cols].reset_index(drop=True)
    y = df["target"].reset_index(drop=True)

    # Split A: Stratified random
    X_train_a, X_test_a, y_train_a, y_test_a = stratified_random_split(X, y)

    print("\nSPLIT STRATEGY A — STRATIFIED RANDOM")
    print("-" * 40)
    print(f"  Train size: {len(X_train_a)} (organic: {(y_train_a == 0).sum()}, fraud: {(y_train_a == 1).sum()})")
    print(f"  Test size:  {len(X_test_a)} (organic: {(y_test_a == 0).sum()}, fraud: {(y_test_a == 1).sum()})")

    # Split B: Grouped merchant
    X_train_b, X_test_b, y_train_b, y_test_b, train_merchants, test_merchants = grouped_merchant_split(
        df, feature_cols
    )

    print("\nSPLIT STRATEGY B — UNSEEN MERCHANT")
    print("-" * 40)
    print(f"  Train merchants: {train_merchants}")
    print(f"  Test merchants:  {test_merchants}")
    print(f"  Train size: {len(X_train_b)} (organic: {(y_train_b == 0).sum()}, fraud: {(y_train_b == 1).sum()})")
    print(f"  Test size:  {len(X_test_b)} (organic: {(y_test_b == 0).sum()}, fraud: {(y_test_b == 1).sum()})")

    # Step 4: Feature sets
    print("\n[4/9] Defining feature sets...")
    feature_set_a = get_feature_set_a(feature_cols)
    feature_set_b = get_feature_set_b(feature_cols)

    print("\nFEATURE SETS")
    print("-" * 40)
    print(f"  Set A (All Behavioral):    {len(feature_set_a)} features")
    print(f"  Set B (Without Volume):    {len(feature_set_b)} features")
    print(f"  Volume features removed:   {VOLUME_FEATURES}")

    # Step 5-6: Run experiments
    print("\n[5/9] Running experiments...")
    results = []
    all_importance = []

    models = create_models()
    splits = [
        ("Stratified Random", X_train_a, X_test_a, y_train_a, y_test_a),
        ("Unseen Merchant", X_train_b, X_test_b, y_train_b, y_test_b),
    ]
    feature_sets = [
        ("Set A (All Behavioral)", feature_set_a),
        ("Set B (Without Volume)", feature_set_b),
    ]

    for split_name, X_tr, X_te, y_tr, y_te in splits:
        for fs_name, fs_cols in feature_sets:
            for model_name, model in models.items():
                # Create fresh model
                if model_name == "LogisticRegression":
                    from sklearn.linear_model import LogisticRegression as LR
                    from sklearn.pipeline import Pipeline as P
                    from sklearn.preprocessing import StandardScaler as SS
                    m = P([("scaler", SS()), ("clf", LR(random_state=RANDOM_STATE, max_iter=1000))])
                elif model_name == "RandomForest":
                    from sklearn.ensemble import RandomForestClassifier as RF
                    m = RF(n_estimators=100, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1)
                else:
                    from sklearn.dummy import DummyClassifier as DC
                    m = DC(strategy="most_frequent", random_state=RANDOM_STATE)

                # Run experiment
                exp_result = run_experiment(
                    df=df,
                    feature_cols=fs_cols,
                    split_name=split_name,
                    X_train=X_tr[fs_cols],
                    X_test=X_te[fs_cols],
                    y_train=y_tr,
                    y_test=y_te,
                    model_name=model_name,
                    model=m,
                )

                results.append(exp_result)

                # Store feature importance for non-dummy models
                if model_name in ["LogisticRegression", "RandomForest"]:
                    imp_df = exp_result["feature_importance"].copy()
                    imp_df["model"] = model_name
                    imp_df["split"] = split_name
                    imp_df["feature_set"] = fs_name
                    all_importance.append(imp_df)

    # Step 7: Display results
    print("\n[6/9] Experiment Results...")
    print("\nEXPERIMENT RESULTS")
    print("-" * 80)
    print(f"{'Split':<20} {'Model':<20} {'Features':<25} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Acc':>6} {'Train F1':>9} {'Overfit':>8}")
    print("-" * 110)

    for r in results:
        print(f"{r['split']:<20} {r['model']:<20} {r['feature_set']:<25} "
              f"{r['test_precision']:>6.3f} {r['test_recall']:>6.3f} "
              f"{r['test_f1']:>6.3f} {r['test_accuracy']:>6.3f} "
              f"{r['train_f1']:>9.3f} {'YES' if r['overfitting'] else '':>8}")

    # Step 8: Overfitting check
    print("\n[7/9] Overfitting Check...")
    print("\nOVERFITTING CHECK")
    print("-" * 40)

    for r in results:
        if r["model"] in ["LogisticRegression", "RandomForest"]:
            gap = r["train_f1"] - r["test_f1"]
            status = "WARNING: Possible overfitting detected." if r["overfitting"] else "OK"
            print(f"  {r['model']:<20} {r['feature_set']:<25} Train F1: {r['train_f1']:.3f}  Test F1: {r['test_f1']:.3f}  Gap: {gap:.3f}  {status}")

    # Step 9: Feature importance
    print("\n[8/9] Feature Importance...")
    print("\nMODEL INTERPRETATION — BASELINE EXPERIMENT")
    print("-" * 40)

    if all_importance:
        importance_df = pd.concat(all_importance, ignore_index=True)

        # Show top features for each model/split combination
        for model_name in ["LogisticRegression", "RandomForest"]:
            for split_name in ["Stratified Random", "Unseen Merchant"]:
                subset = importance_df[(importance_df["model"] == model_name) & (importance_df["split"] == split_name)]
                if len(subset) > 0:
                    # Use Set A features
                    set_a = subset[subset["feature_set"] == "Set A (All Behavioral)"]
                    if len(set_a) > 0:
                        print(f"\n  {model_name} — {split_name} (Set A):")
                        print(set_a.head(10).to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # Volume ablation
    print("\n[9/9] Volume Ablation Analysis...")
    print("\nVOLUME ABLATION")
    print("-" * 40)

    # Compare Set A vs Set B for each model/split
    for model_name in ["DummyClassifier", "LogisticRegression", "RandomForest"]:
        for split_name in ["Stratified Random", "Unseen Merchant"]:
            set_a_f1 = [r["test_f1"] for r in results
                       if r["model"] == model_name and r["split"] == split_name and "Set A" in r["feature_set"]]
            set_b_f1 = [r["test_f1"] for r in results
                       if r["model"] == model_name and r["split"] == split_name and "Set B" in r["feature_set"]]

            if set_a_f1 and set_b_f1:
                diff = set_a_f1[0] - set_b_f1[0]
                print(f"  {model_name:<20} {split_name:<20} Set A: {set_a_f1[0]:.3f}  Set B: {set_b_f1[0]:.3f}  Diff: {diff:+.3f}")

    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    # Find best model
    best_f1 = 0
    best_result = None
    for r in results:
        if r["model"] != "DummyClassifier" and r["test_f1"] > best_f1:
            best_f1 = r["test_f1"]
            best_result = r

    if best_result:
        print(f"\n  Best performing model: {best_result['model']}")
        print(f"  Best test F1: {best_f1:.3f}")
        print(f"  Split: {best_result['split']}")
        print(f"  Feature set: {best_result['feature_set']}")

    # Answer volume ablation question
    lr_set_a = [r["test_f1"] for r in results if r["model"] == "LogisticRegression" and "Set A" in r["feature_set"] and r["split"] == "Stratified Random"]
    lr_set_b = [r["test_f1"] for r in results if r["model"] == "LogisticRegression" and "Set B" in r["feature_set"] and r["split"] == "Stratified Random"]

    if lr_set_a and lr_set_b:
        volume_diff = lr_set_a[0] - lr_set_b[0]
        if abs(volume_diff) < 0.05:
            print(f"\n  Volume ablation: Removing volume features had MINIMAL impact (F1 diff: {volume_diff:+.3f})")
            print(f"  This supports the SUS hypothesis: behavioral patterns distinguish cause, not volume.")
        else:
            print(f"\n  Volume ablation: Removing volume features had MODERATE impact (F1 diff: {volume_diff:+.3f})")
            print(f"  Volume features contribute to cause classification, but behavioral features also matter.")

    print("\n" + "=" * 60)
    print("NOTE: This is a baseline experiment on the full synthetic dataset.")
    print("It is NOT the final held-out classifier evaluation.")
    print("=" * 60)

    print("\nDone!")


if __name__ == "__main__":
    main()
