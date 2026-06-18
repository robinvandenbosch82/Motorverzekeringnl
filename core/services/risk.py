"""
RISK Insurance API client — the heart of the premie-vergelijker/afsluit-tool.

Faithful Python port of the Supabase edge proxy from the Lovable hand-over
(`supabase/functions/risk-api/index.ts`). The tool itself computes NOTHING:
every premium, coverage amount and tax figure comes 1-on-1 from RISK. This
module's job is to authenticate (HTTP Basic Auth) and shape the request bodies
exactly as RISK expects, per the official v9.0 field specs.

Credentials are read from Django settings (env-driven) and never leave the
server. The browser talks only to our own proxy views (core.views_premie),
which call into the functions here.

Operations (RISK v9.0):
  get_vehicle_info(plate)                      -> dict (+ isVan)
  calculate_premiums(details, is_van)          -> list[InsuranceResult]
  calculate_additional_coverages(d, id, isVan) -> list[AdditionalCoverage]
  offer_insurance(data, is_van)                -> dict (OfferNumber, ...)
  request_insurance(data, is_van)              -> dict (PolicyNumber, ...)
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger("core.risk")


class RiskAPIError(Exception):
    """Raised when a RISK call fails. `upstream_down` marks a 5xx/transport
    failure (RISK unreachable) vs. a normal not-found/validation failure."""

    def __init__(self, message: str, *, upstream_down: bool = False, status: int | None = None):
        super().__init__(message)
        self.message = message
        self.upstream_down = upstream_down
        self.status = status


# ── helpers ─────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _auth_headers() -> dict:
    user = settings.RISK_API_USERNAME
    pw = settings.RISK_API_PASSWORD
    if not user or not pw:
        raise RiskAPIError("RISK API credentials niet geconfigureerd (.env).")
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def _base() -> str:
    return settings.RISK_API_BASE.rstrip("/")


def _broker() -> str:
    return settings.RISK_BROKER_ID


def _num(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


# ── request-body builders (ported verbatim from buildCalculateBody etc.) ─────
def build_calculate_body(details: dict) -> dict:
    """Body for Calculate*Premiums and *AdditionalCoverages. Mirrors the proxy's
    buildCalculateBody — every default is intentional and matches RISK v9.0."""
    return {
        "CommencingDate": details.get("CommencingDate") or _now_iso(),
        "LicensePlate": details.get("LicensePlate"),
        "OwnerShip": details.get("OwnerShip") or "E",
        "FreeChoiceRepairAdditionallyInsured": (
            details.get("freeChoiceRepairAdditionallyInsured")
            or details.get("FreeChoiceRepairAdditionallyInsured") or "N"),
        "DealerExtrasValue": _num(details.get("DealerExtrasValue"), 0),
        "TheftProtectionClass": details.get("TheftProtectionClass") or "1",
        "Bearlock": details.get("Bearlock") or "N",
        "DriverOne": details.get("DriverOne") or "J",
        "DriverZipCode": str(details.get("DriverZipCode") or ""),
        "DriverHouseNumber": _num(details.get("DriverHouseNumber"), 0),
        "DriverHouseNumberAddition": details.get("DriverHouseNumberAddition") or "",
        "DriverBirthDate": details.get("DriverBirthdate") or details.get("DriverBirthDate") or "",
        "ClaimFreeYears": _num(details.get("ClaimFreeYears"), 0),
        "CompanyTradeRegisterNumber": details.get("CompanyTradeRegisterNumber") or "",
        "VatDeductible": details.get("VatDeductible") or "N",
        "CarVehicleUse": details.get("CarVehicleUse") or "X",
        "KmPerYear": str(details.get("KmPerYear") or "20000"),
        "Coverage": details.get("Coverage") or "1",
        "CascoDeductibles": _num(details.get("CascoDeductibles"), 250),
        "ReturnProvision": details.get("ReturnProvision") or "0,00",
        "PaymentPeriod": _num(details.get("PaymentPeriod"), 1),
        "Identifier": details.get("Identifier") or "",
        "IncludeXml": False,
        "BrokerID": _broker(),
    }


def build_offer_body(data: dict) -> dict:
    """Body for Offer*BusinessInsurance (and the base of Request*)."""
    return {
        "CommencingDate": data.get("CommencingDate") or _now_iso(),
        "LicensePlate": data.get("LicensePlate"),
        "OwnerShip": data.get("OwnerShip") or "E",
        "FreeChoiceRepairAdditionallyInsured": (
            data.get("freeChoiceRepairAdditionallyInsured")
            or data.get("FreeChoiceRepairAdditionallyInsured") or "N"),
        "DealerExtrasValue": _num(data.get("DealerExtrasValue"), 0),
        "TheftProtectionClass": data.get("TheftProtectionClass") or "1",
        "Bearlock": data.get("Bearlock") or "N",
        "DriverOne": data.get("DriverOne") or "J",
        "DriverNameInfix": data.get("DriverNameInfix") or "",
        "DriverGender": data.get("DriverGender") or "",
        "DriverZipCode": str(data.get("DriverZipCode") or ""),
        "DriverHouseNumber": _num(data.get("DriverHouseNumber"), 0),
        "DriverHouseNumberAddition": data.get("DriverHouseNumberAddition") or "",
        "DriverBirthDate": data.get("DriverBirthdate") or data.get("DriverBirthDate") or "",
        "ClaimFreeYears": _num(data.get("ClaimFreeYears"), 0),
        "CarVehicleUse": data.get("CarVehicleUse") or "X",
        "KmPerYear": str(data.get("KmPerYear") or "20000"),
        "Coverage": data.get("Coverage") or "1",
        "CascoDeductibles": _num(data.get("CascoDeductibles"), 250),
        "AdditionalCoverages": data.get("additionalCoverages") or data.get("AdditionalCoverages") or [],
        "IncludeDocuments": True,
        "Identifier": data.get("selectedIdentifier") or data.get("Identifier") or "",
        "CompanyName": data.get("CompanyName") or "",
        "CompanyNameSecond": data.get("CompanyNameSecond") or "",
        "LegalFormBusiness": data.get("LegalFormBusiness") or "",
        "CompanyTradeRegisterNumber": data.get("CompanyTradeRegisterNumber") or "",
        "VatDeductible": data.get("VatDeductible") or "N",
        "CompanyPhoneNumber": data.get("CompanyPhoneNumber") or "",
        "CompanyEmail": data.get("CompanyEmail") or "",
        "ContactSurname": data.get("ContactSurname") or "",
        "ContactInitials": data.get("ContactInitials") or "",
        "ContactPrefixes": data.get("ContactPrefixes") or "",
        "ContactGender": data.get("ContactGender") or "",
        "ContactPhoneNumber": data.get("ContactPhonenumber") or data.get("ContactPhoneNumber") or "",
        "ContactMobileNumber": data.get("ContactMobilenumber") or data.get("ContactMobileNumber") or "",
        "ReturnProvision": data.get("ReturnProvision") or "0,00",
        "PaymentPeriod": _num(data.get("PaymentPeriod"), 1),
        "IBAN": data.get("IBAN") or "",
        "CollectionAccountInNameOf": data.get("collectionAccountInNameOf") or data.get("CollectionAccountInNameOf") or "",
        "IncludeXml": False,
        "BrokerID": _broker(),
    }


def build_request_body(data: dict) -> dict:
    """Body for Request*BusinessInsurance — offer body + binding/acceptance fields."""
    body = build_offer_body(data)
    body.update({
        "CarSignCode": data.get("CarSignCode") or "",
        "LicencePlateHolder": data.get("LicencePlateHolder") or "3",
        "DriverName": data.get("DriverName") or "",
        "DriverInitials": data.get("DriverInitials") or "",
        "DisqualificationFromDriving": data.get("DisqualificationFromDriving") or "",
        "DriverLicensedToDrive": data.get("DriverLicensedToDrive") or "J",
        "IBAN": data.get("IBAN") or "",
        "Cancelled": data.get("Cancelled") or "",
        "Convicted": data.get("Convicted") or "",
        "Damage": data.get("Damage") or "",
        "NumberOfDamages": _num(data.get("NumberOfDamages"), 0),
        "FinancialProblems": data.get("FinancialProblems") or "",
        "Fraud": data.get("Fraud") or "",
        "Seizure": data.get("Seizure") or "",
        "Agreement": data.get("Agreement") or "J",
    })
    return body


# ── HTTP plumbing ────────────────────────────────────────────────────────────
def _post(url: str, body: dict, *, api_version: str | None = None) -> requests.Response:
    headers = _auth_headers()
    headers["api-version"] = api_version or settings.RISK_API_VERSION
    try:
        return requests.post(url, json=body, headers=headers, timeout=settings.RISK_API_TIMEOUT)
    except requests.RequestException as exc:
        # Transport failure (DNS/connect/timeout) → clean 503, not a 500.
        raise RiskAPIError(f"RISK niet bereikbaar: {exc}", upstream_down=True, status=503)


def _get(url: str, *, api_version: str) -> requests.Response:
    headers = _auth_headers()
    headers["api-version"] = api_version
    try:
        return requests.get(url, headers=headers, timeout=settings.RISK_API_TIMEOUT)
    except requests.RequestException as exc:
        raise RiskAPIError(f"RISK niet bereikbaar: {exc}", upstream_down=True, status=503)


# ── vehicle lookup ───────────────────────────────────────────────────────────
def _lookup_attempts(plate: str, vehicle_type: str) -> list[dict]:
    """Build the ordered list of lookup attempts (paths × versions × methods),
    mirroring buildVehicleLookupAttempts."""
    if vehicle_type == "van":
        paths = ["Data/GetVanBusinessInfo", "Car/GetVanBusinessInfo", "CarBusiness/GetVanBusinessInfo"]
    else:
        paths = ["Data/GetCarBusinessInfo", "Car/GetCarBusinessInfo", "CarBusiness/GetCarBusinessInfo"]

    attempts: list[dict] = []
    for path in paths:
        base = f"{_base()}/{path}"
        versions = ["9.0", "9", "5"] if path.startswith("CarBusiness/") else ["5", "9.0"]
        for ver in versions:
            attempts.append({
                "label": f"{vehicle_type} GET {path} (v{ver})",
                "method": "GET", "api_version": ver,
                "url": f"{base}?LicensePlate={plate}&BrokerID={_broker()}&Version=9.0&api-version={ver}",
            })
            attempts.append({
                "label": f"{vehicle_type} POST {path} (v{ver})",
                "method": "POST", "api_version": ver,
                "url": f"{base}?api-version={ver}",
                "body": {"LicensePlate": plate, "BrokerID": _broker(), "Version": "9.0"},
            })
    return attempts


def _try_lookup(attempts: list[dict]):
    """Walk attempts; return parsed JSON of the first 2xx. Raises RiskAPIError
    with upstream_down=True only if every attempt was a 5xx/transport error."""
    errors: list[str] = []
    all_upstream_down = True
    for a in attempts:
        try:
            if a["method"] == "GET":
                res = _get(a["url"], api_version=a["api_version"])
            else:
                res = _post(a["url"], a.get("body", {}), api_version=a["api_version"])
        except RiskAPIError as exc:
            # Transport failure on this attempt (_get/_post wrap it); try the next.
            errors.append(f"{a['label']}: transport {exc.message}")
            continue
        raw = res.text or ""
        logger.debug("[%s] %s %s", a["label"], res.status_code, raw[:200])
        if res.ok:
            return res.json() if raw.strip() else {}
        if res.status_code < 500 or res.status_code == 501:
            all_upstream_down = False
        errors.append(f"{a['label']}: {res.status_code} {raw[:150]}")
    raise RiskAPIError(" | ".join(errors) or "no attempts", upstream_down=all_upstream_down)


def get_vehicle_info(license_plate: str) -> dict:
    """Look up a plate, trying van first then car. Returns the vehicle dict with
    an injected `isVan` flag. Raises RiskAPIError (upstream_down set when RISK
    itself is unreachable, vs. a genuine not-found)."""
    plate = "".join(ch for ch in str(license_plate).upper() if ch not in "- ")
    upstream_down = True
    for vehicle_type in ("van", "car"):
        try:
            data = _try_lookup(_lookup_attempts(plate, vehicle_type))
            return {**data, "isVan": vehicle_type == "van"}
        except RiskAPIError as exc:
            if not exc.upstream_down:
                upstream_down = False
            logger.info("%s lookup failed: %s", vehicle_type, exc.message[:200])
    if upstream_down:
        raise RiskAPIError(
            "De kentekenservice is tijdelijk niet bereikbaar. Probeer het over enkele minuten opnieuw.",
            upstream_down=True, status=503)
    raise RiskAPIError("Kenteken niet gevonden. Controleer het kenteken en probeer opnieuw.", status=404)


# ── premiums ─────────────────────────────────────────────────────────────────
def _calc_endpoint(is_van: bool, what: str) -> str:
    seg = "Van" if is_van else ""
    names = {
        "premiums": f"Calculate{seg}BusinessPremiums",
        "additional": f"Calculate{seg}BusinessAdditionalCoverages",
        "offer": f"Offer{seg or ''}BusinessInsurance" if not is_van else "OfferVanBusinessInsurance",
        "request": f"Request{seg}BusinessInsurance",
    }
    return f"{_base()}/CarBusiness/{names[what]}?api-version={settings.RISK_API_VERSION}"


def calculate_premiums(details: dict, is_van: bool) -> list:
    """Return the list of insurer premiums for these details. Empty list when
    RISK signals 'no coverage available' (HTTP 204/406)."""
    res = _post(_calc_endpoint(is_van, "premiums"), build_calculate_body(details))
    if res.status_code in (204, 406):
        return []
    if not res.ok:
        raise RiskAPIError(f"Calculate failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code)
    parsed = res.json()
    return parsed.get("CalculatedPremiums", parsed) if isinstance(parsed, dict) else parsed


def calculate_additional_coverages(details: dict, identifier: str, is_van: bool) -> list:
    """Additional coverages for the chosen insurer (Identifier)."""
    body = {**build_calculate_body(details), "Identifier": identifier}
    res = _post(_calc_endpoint(is_van, "additional"), body)
    if res.status_code == 204:
        return []
    if not res.ok:
        raise RiskAPIError(f"Additional coverages failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code)
    parsed = res.json()
    premiums = parsed.get("CalculatedPremiums", []) if isinstance(parsed, dict) else []
    return (premiums[0].get("AdditionalCoverages", []) if premiums else [])


def offer_insurance(data: dict, is_van: bool) -> dict:
    """Create an offer (OfferNumber). Present in the proxy; optional in the flow."""
    res = _post(_calc_endpoint(is_van, "offer"), build_offer_body(data))
    if not res.ok:
        raise RiskAPIError(f"Offer failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code)
    return res.json()


def request_insurance(data: dict, is_van: bool) -> dict:
    """Bind the policy — RISK returns a PolicyNumber. This creates a REAL
    insurance application; only call after explicit user agreement."""
    res = _post(_calc_endpoint(is_van, "request"), build_request_body(data))
    if not res.ok:
        raise RiskAPIError(f"Request failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code)
    return res.json()
