import os
import pandas as pd
from datetime import date
from typing import List, Tuple

from models.import_result import ImportResult, ImportStatus
from models.voucher import Voucher, VoucherStatus
from models.account_head import VoucherType


class PayrollImportService:

    REQUIRED_COLUMNS = {
        "Business Segment",
        "Product Code",
        "Salary Payable"
    }

    OPTIONAL_COLUMNS = {
        "Employee Share of PF Payable",
        "Employer Share of PF Payable",
        "Employee Share of ESIC Payable",
        "Employer Share of ESIC Payable",
        "Professional Tax Payable",
        "TDS on Salary Payable"
    }

    def import_excel(self, filepath: str, voucher_date: date) -> Tuple[List[Voucher], ImportResult]:
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type="Payroll",
            status=ImportStatus.IN_PROGRESS
        )

        # Store voucher date for downstream use
        result.context = {"voucher_date": voucher_date}

        df = self._read_excel(filepath)
        self._validate_columns(df)

        vouchers = self._build_vouchers(df, result)
        self._build_preview(df, result)

        result.complete()
        return vouchers, result

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _read_excel(self, filepath: str) -> pd.DataFrame:
        """
        Reads Excel where headers are not in the first row.
        Promotes first non-empty row as header.
        """
        df = pd.read_excel(filepath, header=None)
        df = df.dropna(how="all")
        df.columns = df.iloc[0]
        return df.iloc[1:].reset_index(drop=True)

    def _validate_columns(self, df: pd.DataFrame):
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(missing)}"
            )

    def _build_vouchers(self, df: pd.DataFrame, result: ImportResult) -> List[Voucher]:
        vouchers: List[Voucher] = []
        voucher_date = result.context.get("voucher_date")

        for _, row in df.iterrows():

            salary = row.get("Salary Payable")
            if salary is None or float(salary) <= 0:
                continue

            # Build narration with full payroll breakup
            narration = (
                f"Payroll | "
                f"PF(Emp): {row.get('Employee Share of PF Payable', 0)} | "
                f"PF(Empr): {row.get('Employer Share of PF Payable', 0)} | "
                f"ESIC(Emp): {row.get('Employee Share of ESIC Payable', 0)} | "
                f"ESIC(Empr): {row.get('Employer Share of ESIC Payable', 0)} | "
                f"PT: {row.get('Professional Tax Payable', 0)} | "
                f"TDS: {row.get('TDS on Salary Payable', 0)}"
            )

            voucher = Voucher(
                date=voucher_date,
                voucher_type=VoucherType.DEBIT,
                account_code="PAYROLL",
                account_name="Payroll Cost",
                amount=float(salary),
                segment=row.get("Business Segment", ""),
                narration=narration,
                status=VoucherStatus.PENDING_REVIEW,
                source="Payroll Bulk Import"
            )

            vouchers.append(voucher)
            result.add_voucher(voucher)

        result.total_rows = len(df)
        result.successful_rows = len(vouchers)
        return vouchers

    def _build_preview(self, df: pd.DataFrame, result: ImportResult):
        """
        Builds lightweight preview rows for UI (first 15 rows only).
        """
        result.preview_data = [
            {
                "Product Code": row.get("Product Code", ""),
                "Business Segment": row.get("Business Segment", ""),
                "Location": row.get("Location", ""),
                "Salary Payable": row.get("Salary Payable", 0),
                "Amount": row.get("Amount", 0), 
                # ... breakup fields ...                                
                "Employee Share of PF Payable": row.get("Employee Share of PF Payable", 0),
                "Employer Share of PF Payable": row.get("Employer Share of PF Payable", 0),
                "Employee Share of ESIC Payable": row.get("Employee Share of ESIC Payable", 0),
                "Employer Share of ESIC Payable": row.get("Employer Share of ESIC Payable", 0),
                "Professional Tax Payable": row.get("Professional Tax Payable", 0),
                "TDS on Salary Payable - FY 2026-27": row.get("TDS on Salary Payable - FY 2026-27", 0)
            }
            for _, row in df.head(15).iterrows()
        ]
