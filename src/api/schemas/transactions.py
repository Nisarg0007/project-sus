"""
API schemas for transaction upload and validation endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TransactionUploadResponse(BaseModel):
    """Response after successfully uploading a transaction dataset."""

    dataset_id: str = Field(..., description="Unique dataset identifier")
    original_filename: str = Field(..., description="Original uploaded filename")
    source_name: str = Field(..., description="Provider source name")
    row_count: int | None = Field(None, description="Number of transaction rows")
    merchant_count: int | None = Field(None, description="Number of unique merchants")


class TransactionValidationResponse(BaseModel):
    """Response from transaction data validation."""

    is_valid: bool = Field(..., description="Whether the data passed validation")
    total_rows: int = Field(0, description="Total rows in the dataset")
    valid_rows: int = Field(0, description="Rows that passed validation")
    error_count: int = Field(0, description="Number of validation errors")
    warning_count: int = Field(0, description="Number of validation warnings")
    errors: list[str] = Field(default_factory=list, description="Validation error messages")
    warnings: list[str] = Field(default_factory=list, description="Validation warning messages")
    unique_merchants: int | None = Field(None, description="Number of unique merchants")
    date_range_start: str | None = Field(None, description="Earliest date in the dataset")
    date_range_end: str | None = Field(None, description="Latest date in the dataset")
    amount_min: float | None = Field(None, description="Minimum transaction amount")
    amount_max: float | None = Field(None, description="Maximum transaction amount")


class DatasetMetadataResponse(BaseModel):
    """Read-only metadata about a stored dataset."""

    dataset_id: str = Field(..., description="Unique dataset identifier")
    original_filename: str = Field(..., description="Original uploaded filename")
    data_source_type: str = Field(..., description="Type of data source")
    row_count: int | None = Field(None, description="Number of rows")
    merchant_count: int | None = Field(None, description="Number of unique merchants")
    min_transaction_date: str | None = Field(None, description="Earliest transaction date")
    max_transaction_date: str | None = Field(None, description="Latest transaction date")
    validation_status: str = Field(..., description="Validation status")
    created_at: str = Field(..., description="When the dataset was uploaded")


class DatasetListResponse(BaseModel):
    """Paginated list of datasets."""

    total: int = Field(..., description="Total number of datasets")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Current offset")
    items: list[DatasetMetadataResponse] = Field(
        default_factory=list, description="Dataset records"
    )


class RunInvestigationRequest(BaseModel):
    """Request to run an investigation with optional dataset override.

    When dataset_id is provided, the investigation uses uploaded transaction data.
    When omitted, the investigation uses the default dataset.
    All pipeline parameters are optional and default to application settings.
    """

    dataset_id: str | None = Field(
        None,
        description="Dataset ID from a previous upload. If null, uses the default dataset.",
    )
    transactions_path: str | None = Field(
        None,
        description="Direct path to transactions CSV. Overrides dataset_id if both provided.",
    )
    window_labels_path: str | None = Field(
        None,
        description="Path to window labels CSV. Used with transactions_path or dataset_id.",
    )
    model_path: str | None = Field(None, description="Custom model path")
    z_threshold: float | None = Field(None, ge=0.01, description="Z-score threshold for spike detection")
    min_history_days: int | None = Field(None, ge=1, description="Minimum historical days")
    merchant_filter: str | None = Field(None, description="Filter to specific merchant")
