"""
Transaction upload and validation endpoints for SUS.

Provides:
- POST /transactions/upload — upload a transaction CSV dataset
- POST /transactions/validate — validate a transaction CSV without storing
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.schemas.transactions import (
    TransactionUploadResponse,
    TransactionValidationResponse,
)
from src.services.dataset_manager import dataset_manager
from src.services.transaction_data_provider import CSVTransactionDataProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])

# Maximum upload size: 100 MB
MAX_UPLOAD_SIZE = 100 * 1024 * 1024


@router.post("/upload", response_model=TransactionUploadResponse)
async def upload_transaction_csv(
    file: UploadFile = File(..., description="Transaction CSV file"),
    window_labels_file: Optional[UploadFile] = File(
        None, description="Optional window labels CSV file"
    ),
) -> TransactionUploadResponse:
    """Upload a transaction CSV dataset for use in investigations.

    The uploaded file is stored in the configured upload directory with a
    unique dataset ID. Returns the dataset ID which can be used when running
    an investigation.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=422, detail="No filename provided")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="File must be a CSV (.csv extension required)",
        )

    # Read file content with size limit
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    # Read optional window labels
    wl_content = None
    wl_filename = None
    if window_labels_file is not None:
        wl_content = await window_labels_file.read()
        wl_filename = window_labels_file.filename
        if len(wl_content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Window labels file too large",
            )

    # Validate before storing
    try:
        # Write to a temp location for validation, then store
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="wb"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        provider = CSVTransactionDataProvider(
            transactions_path=tmp_path,
            source_name=f"upload:{file.filename}",
        )
        validation = provider.validate()

        # Clean up temp file
        os.unlink(tmp_path)

        if not validation.is_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Transaction CSV failed validation",
                    "validation": validation.to_dict(),
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Validation failed during upload")
        raise HTTPException(
            status_code=500,
            detail=f"Validation error: {e}",
        )

    # Store the dataset
    try:
        record = dataset_manager.store_dataset(
            transactions_content=content,
            original_filename=file.filename,
            window_labels_content=wl_content,
            window_labels_filename=wl_filename,
        )
    except Exception as e:
        logger.exception("Failed to store dataset")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store dataset: {e}",
        )

    logger.info(
        "Dataset uploaded: %s (%s)", record.dataset_id, file.filename
    )

    return TransactionUploadResponse(
        dataset_id=record.dataset_id,
        original_filename=record.original_filename,
        source_name=record.source_name,
        transactions_path=record.transactions_path,
        window_labels_path=record.window_labels_path,
    )


@router.post("/validate", response_model=TransactionValidationResponse)
async def validate_transaction_csv(
    file: UploadFile = File(..., description="Transaction CSV file to validate"),
) -> TransactionValidationResponse:
    """Validate a transaction CSV without storing it.

    Returns validation results including row counts, errors, warnings,
    and metadata (unique merchants, date range, amount stats).
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="File must be a CSV")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        )

    # Write to temp file for validation
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        provider = CSVTransactionDataProvider(
            transactions_path=tmp_path,
            source_name=f"validate:{file.filename}",
        )
        result = provider.validate()
    finally:
        os.unlink(tmp_path)

    return TransactionValidationResponse(
        is_valid=result.is_valid,
        total_rows=result.total_rows,
        valid_rows=result.valid_rows,
        error_count=len(result.errors),
        warning_count=len(result.warnings),
        errors=result.errors,
        warnings=result.warnings,
        unique_merchants=result.metadata.get("unique_merchants"),
        date_range_start=result.metadata.get("date_range_start"),
        date_range_end=result.metadata.get("date_range_end"),
        amount_min=result.metadata.get("amount_min"),
        amount_max=result.metadata.get("amount_max"),
    )
