"""Validation and identity helpers for the SAP-owned portion of the #18 fixture."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.volume_fixture import ValidationError as FixtureValidationError
from scripts.volume_fixture import validate_dataset


SAP_FILES = (
    "sap_plan_b/business_partner.jsonl",
    "sap_plan_b/supplier.jsonl",
    "sap_plan_b/cost_center.jsonl",
    "sap_plan_b/sap_document.jsonl",
    "sap_plan_b/sap_document_line.jsonl",
    "sap_plan_b/document_link.jsonl",
    "sap_plan_b/supplier_cost.jsonl",
    "sap_plan_b/sap_cost_allocation.jsonl",
)


class PackageValidationError(RuntimeError):
    """Raised when a local SAP Plan B package fails validation."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    if pretty:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _identity(row: dict[str, Any]) -> tuple[str, str, str, str]:
    fields = ("sourceSystem", "sourceTenant", "sourceEntity", "sourceKey")
    for field in fields:
        if not isinstance(row.get(field), str) or not row[field]:
            raise PackageValidationError("Every SAP row must have a complete source identity.")
    return (row["sourceSystem"], row["sourceTenant"], row["sourceEntity"], row["sourceKey"])


def _load_fixture(fixture_path: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    try:
        validate_dataset(fixture_path)
        manifest = json.loads((fixture_path / "manifest.json").read_text(encoding="utf-8"))
        records = {
            path: [json.loads(line) for line in (fixture_path / path).read_text(encoding="utf-8").splitlines()
                   if line.strip()]
            for path in SAP_FILES
        }
    except (FixtureValidationError, OSError, ValueError) as exc:
        raise PackageValidationError(f"Source fixture is invalid: {exc}") from exc
    return manifest, records


def _index_rows(
    rows_by_file: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[tuple[str, str, str, str], dict[str, Any]]]:
    indexed = {}
    for path in SAP_FILES:
        rows = {}
        for row in rows_by_file[path]:
            identity = _identity(row)
            if identity in rows:
                raise PackageValidationError(f"Duplicate source identity in {path}: {identity}.")
            rows[identity] = row
        indexed[path] = rows
    return indexed


def _verify_existing_noop(output_path: Path, expected_files: dict[str, bytes]) -> None:
    if output_path.is_symlink():
        raise PackageValidationError("Package must not be a symlink.")
    actual_paths = set()
    for path in output_path.rglob("*"):
        if path.is_symlink():
            raise PackageValidationError("Package must not contain symlinks.")
        if path.is_file():
            actual_paths.add(path.relative_to(output_path).as_posix())
    if actual_paths != set(expected_files):
        raise FileExistsError(
            "Package does not match the deterministic fixture. "
            f"missing={sorted(set(expected_files) - actual_paths)}, "
            f"unexpected={sorted(actual_paths - set(expected_files))}"
        )
    mismatched = [
        path for path, expected in expected_files.items()
        if (output_path / path).read_bytes() != expected
    ]
    if mismatched:
        raise FileExistsError(f"Package differs from expected bytes: {sorted(mismatched)}")


def _paths_overlap(left: Path, right: Path) -> bool:
    left, right = left.resolve(), right.resolve()
    return left == right or left in right.parents or right in left.parents


def _validate_relationships(
    indexed: dict[str, dict[tuple[str, str, str, str], dict[str, Any]]],
    reconciliation: dict[str, Any],
) -> None:
    rows = {Path(path).name: list(indexed[path].values()) for path in SAP_FILES}

    def unique_index(filename: str, key: str) -> dict[str, dict[str, Any]]:
        result = {}
        for row in rows[filename]:
            value = row.get(key)
            if not isinstance(value, str) or not value or value in result:
                raise PackageValidationError(f"Missing or duplicate {key} in {filename}.")
            result[value] = row
        return result

    partners = unique_index("business_partner.jsonl", "sourceKey")
    suppliers = unique_index("supplier.jsonl", "sourceKey")
    cost_centers = unique_index("cost_center.jsonl", "sourceKey")
    documents = unique_index("sap_document.jsonl", "erpDocumentKey")
    lines = unique_index("sap_document_line.jsonl", "erpDocumentLineKey")
    links = unique_index("document_link.jsonl", "documentLinkKey")
    costs = unique_index("supplier_cost.jsonl", "supplierCostKey")
    for supplier in suppliers.values():
        partner = partners.get(supplier.get("bpSourceKey"))
        if partner is None or partner.get("bpRole") != "Supplier":
            raise PackageValidationError("Supplier does not resolve to its Supplier business partner.")

    for document in documents.values():
        line = lines.get(document.get("erpDocumentLineKey"))
        link = links.get(document.get("documentLinkKey"))
        partner = partners.get(document.get("partnerSourceKey"))
        if line is None or link is None or partner is None:
            raise PackageValidationError("ERP document has a missing line, link, or business partner.")
        if (
            line.get("erpDocumentKey") != document["erpDocumentKey"]
            or link.get("erpDocumentKey") != document["erpDocumentKey"]
            or line.get("documentSourceKey") != document["sourceKey"]
            or link.get("erpDocumentLineKey") != line["erpDocumentLineKey"]
        ):
            raise PackageValidationError("ERP document, line, and link relationships do not reconcile.")
        amount = document.get("amountMinor")
        if (
            type(amount) is not int or amount < 0 or document.get("currency") != "USD"
            or line.get("currency") != document["currency"]
            or type(line.get("lineQuantity")) is not int or line["lineQuantity"] <= 0
            or type(line.get("unitPriceMinor")) is not int
            or any(type(line.get(field)) is not int for field in ("lineNetMinor", "lineTaxMinor", "lineGrossMinor"))
            or line["lineQuantity"] * line["unitPriceMinor"] != line["lineNetMinor"]
            or line["lineTaxMinor"] != 0 or line["lineGrossMinor"] != line["lineNetMinor"]
            or line["lineGrossMinor"] != amount
        ):
            raise PackageValidationError("ERP document line financial values do not reconcile in USD minor units.")
        document_type = document.get("documentType")
        if document_type not in {"customer_invoice", "customer_credit_memo", "supplier_invoice"}:
            raise PackageValidationError("ERP document has an unsupported document type.")
        if document_type in {"customer_invoice", "customer_credit_memo"}:
            if partner.get("bpRole") != "Customer" or partner.get("partyKey") != document.get("partyKey"):
                raise PackageValidationError("Customer document does not resolve to its Customer business partner.")
            if document_type == "customer_credit_memo" and (
                document.get("scenarioCreditKey") != link.get("scenarioCreditKey")
                or document.get("orderKey") != link.get("orderKey")
                or link.get("linkType") != "credit-to-document"
            ):
                raise PackageValidationError("Credit memo link must remain explicit and typed.")
        else:
            supplier = suppliers.get(document.get("supplierSourceKey"))
            if (
                partner.get("bpRole") != "Supplier" or supplier is None
                or supplier.get("bpSourceKey") != partner["sourceKey"]
            ):
                raise PackageValidationError("Supplier invoice does not resolve to its Supplier business partner.")

    source_docs = {row["sourceKey"]: row for row in documents.values()}
    source_lines = {row["sourceKey"]: row for row in lines.values()}
    for cost in costs.values():
        document = source_docs.get(cost.get("documentSourceKey"))
        line = source_lines.get(cost.get("documentLineSourceKey"))
        if (
            document is None or line is None
            or cost.get("supplierSourceKey") not in suppliers
            or cost.get("costCenterSourceKey") not in cost_centers
            or document.get("documentType") != "supplier_invoice"
            or document.get("supplierSourceKey") != cost.get("supplierSourceKey")
            or line.get("erpDocumentKey") != document["erpDocumentKey"]
            or type(cost.get("amountMinor")) is not int
            or cost["amountMinor"] != document["amountMinor"] or cost.get("currency") != document["currency"]
        ):
            raise PackageValidationError("Supplier cost does not reconcile to its source document/master data.")
    allocated = {}
    for allocation in rows["sap_cost_allocation.jsonl"]:
        key = allocation.get("supplierCostKey")
        cost = costs.get(key)
        amount = allocation.get("amountMinor")
        if (
            cost is None or type(amount) is not int or amount < 0
            or allocation.get("currency") != cost["currency"]
            or any(allocation.get(field) != cost.get(field)
                   for field in ("eventKey", "supplierSourceKey", "costCenterSourceKey"))
        ):
            raise PackageValidationError("Cost allocation has an invalid supplier-cost reference or amount.")
        allocated[key] = allocated.get(key, 0) + amount
    if allocated != {key: row["amountMinor"] for key, row in costs.items()}:
        raise PackageValidationError("Per-cost allocation totals do not equal supplier costs.")
    totals = {
        "postedCustomerInvoiceMinor": sum(row["amountMinor"] for row in documents.values()
                                         if row["documentType"] == "customer_invoice"),
        "postedCustomerCreditMemoMinor": sum(row["amountMinor"] for row in documents.values()
                                            if row["documentType"] == "customer_credit_memo"),
        "supplierCostMinor": sum(row["amountMinor"] for row in costs.values()),
        "allocatedCostMinor": sum(allocated.values()),
    }
    if any(reconciliation.get(field) != amount for field, amount in totals.items()):
        raise PackageValidationError("SAP package financial totals differ from source reconciliation.")
