"""
RISK Insurance API client — particuliere MOTORVERZEKERING (spec V9).

The tool computes NOTHING itself: every premium, coverage amount and tax figure
comes 1-on-1 from RISK. This module authenticates (HTTP Basic Auth) and shapes
the request bodies exactly as RISK expects per the official "Motor Insurance V9"
field spec. Credentials are read from Django settings (env-driven) and never
leave the server; the browser talks only to our proxy views (core.views_premie).

Endpoints (base settings.RISK_API_BASE):
  GET  /Data/GetPrivateMotorInfo?LicensePlate={plate}     vehicle lookup
  POST /Motor/CalculatePrivatePremiums                    compare premiums
  POST /Motor/CalculatePrivateAdditionalCoverages         additional coverages
  POST /Motor/OfferPrivateInsurance                       offer
  POST /Motor/RequestPrivateInsurance                     bind (real policy)

Operations:
  get_vehicle_info(plate)                 -> dict (motor properties)
  validate_sign_code(plate, code)         -> bool  (kenteken + meldcode)
  calculate_premiums(details)             -> list  (insurer premiums)
  calculate_additional_coverages(d, id)   -> list  (additional coverages)
  offer_insurance(data)                   -> dict  (OfferNumber, ...)
  request_insurance(data)                 -> dict  (PolicyNumber, ...)
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger("core.risk")


class RiskAPIError(Exception):
    """Raised when a RISK call fails. `upstream_down` marks a 5xx/transport
    failure (RISK unreachable) vs. a normal not-found/validation failure."""

    def __init__(self, message: str, *, upstream_down: bool = False,
                 status: int | None = None, reason: str = ""):
        super().__init__(message)
        self.message = message            # technisch (voor logs)
        self.upstream_down = upstream_down
        self.status = status
        self.reason = reason              # leesbare reden uit RISK (voor de gebruiker)


# ── helpers ─────────────────────────────────────────────────────────────────
def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


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


def _house_split(value):
    """Split a house number the user may have typed with its addition in one
    field, e.g. '152c' → ('152', 'c'), '152 c' → ('152', 'c'), '152' → ('152', '').
    RISK needs a numeric HouseNumber >= 1, so the letter must move to the
    addition instead of collapsing the whole thing to 0."""
    s = str(value or "").strip()
    m = re.match(r"(\d+)\s*(.*)$", s)
    if not m:
        return "", s
    return m.group(1), m.group(2).strip()


def _plate(value) -> str:
    """Normalise a license plate: uppercase, strip dashes/spaces."""
    return "".join(ch for ch in str(value or "").upper() if ch not in "- ")


def _phone(value) -> str:
    """Normalise a phone number for RISK: keep digits and a leading '+', strip
    spaces/dashes/parens. RISK weigert een lege string én tussenliggende
    opmaak (mobiel moet matchen op ^((\\+31|0|0031)6)[1-9]…), dus we leveren
    een schoon nummer of '' (= weglaten)."""
    s = str(value or "").strip()
    if not s:
        return ""
    lead = "+" if s[:1] == "+" else ""
    return lead + "".join(ch for ch in s if ch.isdigit())


def _iso_date(value) -> str:
    """Normalise a birthdate/date to ISO (YYYY-MM-DD). Accepts 'DD-MM-YYYY',
    'DD/MM/YYYY' or an already-ISO string; returns '' when unparseable."""
    s = str(value or "").strip()
    if not s:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", s)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return s


# ── API version switch (v9 ⇄ v10) ────────────────────────────────────────────
def _use_v10() -> bool:
    """v10 is active when RISK_API_VERSION starts with "10". Setting the env var
    back to "9.0" restores the v9 flow end-to-end (bodies + header + frontend)."""
    return str(settings.RISK_API_VERSION).startswith("10")


def _calc_body(details: dict) -> dict:
    if _use_v10():
        from . import risk_v10
        return risk_v10.build_calculate_body(details)
    return build_calculate_body(details)


def _offer_body(data: dict) -> dict:
    if _use_v10():
        from . import risk_v10
        return risk_v10.build_offer_body(data)
    return build_offer_body(data)


def _request_body(data: dict) -> dict:
    if _use_v10():
        from . import risk_v10
        return risk_v10.build_request_body(data)
    return build_request_body(data)


# ── request-body builders (per Motor Insurance V9 — "Input" sheet) ───────────
def build_calculate_body(details: dict) -> dict:
    """Body for CalculatePrivatePremiums + CalculatePrivateAdditionalCoverages.
    Every default is intentional and matches the V9 valid-values."""
    cov = str(details.get("Coverage") or "1")
    body = {
        "Use": "P",  # Particulier
        "CommencingDate": _iso_date(details.get("CommencingDate")) or _today_iso(),
        "LicensePlate": _plate(details.get("LicensePlate")),
        "DriverZipCode": str(details.get("DriverZipCode") or "").upper().replace(" ", ""),
        "DriverHouseNumber": _num(_house_split(details.get("DriverHouseNumber"))[0], 0),
        "DriverHouseNumberAddition": (details.get("DriverHouseNumberAddition")
                                      or _house_split(details.get("DriverHouseNumber"))[1]),
        "DriverBirthdate": _iso_date(details.get("DriverBirthdate") or details.get("DriverBirthDate")),
        "ClaimFreeYears": _num(details.get("ClaimFreeYears"), 0),
        "AdditionalDrivingAbility": details.get("AdditionalDrivingAbility") or "N",
        "Coverage": cov,
        "WinterStop": details.get("WinterStop") or "N",
        "Storage": details.get("Storage") or "N",
        "TheftProtectionClass": details.get("TheftProtectionClass") or "B4",
        "KmPerYear": str(details.get("KmPerYear") or "12000"),
        "PaymentPeriod": _num(details.get("PaymentPeriod"), 1),
        "ReturnProvision": details.get("ReturnProvision") or "0,00",
        "Version": settings.RISK_MOTOR_PRODUCT_VERSION,
        "BrokerID": _broker(),
        "IncludeXml": False,
    }
    # Conditional amounts (RISK drops them when not applicable to the coverage).
    if cov == "2":
        body["DayValue"] = _num(details.get("DayValue"), 0)
    if cov in ("2", "3"):
        body["ValueAccessories"] = _num(details.get("ValueAccessories"), 0)
    if cov == "3":
        body["HelmetClothingAmount"] = _num(details.get("HelmetClothingAmount"), 0)
    if details.get("Identifier"):
        body["Identifier"] = details["Identifier"]
    return body


def build_offer_body(data: dict) -> dict:
    """Body for OfferPrivateInsurance (and the base of Request). Adds the chosen
    insurer (Identifier/PP_ENTREF), driver + policyholder details, ownership and
    the selected additional-coverage identifiers."""
    body = build_calculate_body(data)
    cov = body["Coverage"]
    body.update({
        "Identifier": data.get("selectedIdentifier") or data.get("Identifier") or "",
        # Regelmatige bestuurder
        "DriverRelation": data.get("DriverRelation") or "A",
        "DriverName": data.get("DriverName") or "",
        "DriverInitials": data.get("DriverInitials") or "",
        "DriverNameInfix": data.get("DriverNameInfix") or "",
        "DriverGender": data.get("DriverGender") or "",
        # Aanvullende dekkingen (lijst van {Identifier, Type} of identifiers)
        "AdditionalCoverages": data.get("additionalCoverages") or data.get("AdditionalCoverages") or [],
        # Verzekeringnemer (VP_*)
        "Name": data.get("Name") or data.get("DriverName") or "",
        "Initials": data.get("Initials") or data.get("DriverInitials") or "",
        "NameInfix": data.get("NameInfix") or "",
        "Gender": data.get("Gender") or data.get("DriverGender") or "",
        "ZipCode": str(data.get("ZipCode") or data.get("DriverZipCode") or "").upper().replace(" ", ""),
        "HouseNumber": _house_split(data.get("HouseNumber") or data.get("DriverHouseNumber"))[0],
        "HouseNumberAddition": (data.get("HouseNumberAddition") or data.get("DriverHouseNumberAddition")
                                or _house_split(data.get("HouseNumber") or data.get("DriverHouseNumber"))[1]),
        # Straat + plaats zijn verplicht bij offerte/aanvraag; resolven via
        # GetAddressInformation (zie _ensure_address) als ze ontbreken.
        "Street": data.get("Street") or "",
        "Place": data.get("Place") or data.get("City") or "",
        "Birthdate": _iso_date(data.get("Birthdate") or data.get("DriverBirthdate")),
        "Email": data.get("Email") or "",
        "IncludeDocuments": True,
        "IncludeXml": False,
    })
    # Telefoonnummers: RISK valideert het formaat én weigert een lege string
    # ("is not a valid phone number"). Daarom alleen meesturen als ze gevuld zijn,
    # en eerst opschonen (spaties/streepjes/haakjes eruit).
    mobile = _phone(data.get("MobileNumber"))
    if mobile:
        body["MobileNumber"] = mobile
    phone = _phone(data.get("PhoneNumber"))
    if phone:
        body["PhoneNumber"] = phone
    if cov in ("2", "3"):
        body["OwnerShip"] = data.get("OwnerShip") or "E"
        # Financierings-/leasemaatschappij (alleen bij L/F)
        if body["OwnerShip"] in ("L", "F"):
            body.update({
                "NameFinLease": data.get("NameFinLease") or "",
                "ZipCodeFinLease": data.get("ZipCodeFinLease") or "",
                "HouseNumberFinLease": data.get("HouseNumberFinLease") or "",
            })
    return body


def build_request_body(data: dict) -> dict:
    """Body for RequestPrivateInsurance — offer body + binding/acceptance fields.
    Creates a REAL application; only call after explicit user agreement."""
    body = build_offer_body(data)
    body.update({
        # RISK verwacht de meldcode in het veld MotorSignCode (de frontend levert
        # 'm aan onder CarSignCode); een verkeerde veldnaam gaf eerder
        # "The MotorSignCode field is required".
        "MotorSignCode": data.get("MotorSignCode") or data.get("CarSignCode") or "",
        "LicencePlateHolder": data.get("LicencePlateHolder") or "A",
        "DriverLicense": data.get("DriverLicense") or "J",
        "Birthdate": _iso_date(data.get("Birthdate") or data.get("DriverBirthdate")),
        "IBAN": (data.get("IBAN") or "").upper().replace(" ", ""),
        "collectionAccountInNameOf": data.get("collectionAccountInNameOf") or "",
        # Acceptatievragen (RI_*) — leeg = 'nee'.
        "Cancelled": data.get("Cancelled") or "",
        "Convicted": data.get("Convicted") or "",
        "Damage": data.get("Damage") or "",
        "NumberOfDamages": _num(data.get("NumberOfDamages"), 0),
        "FinancialProblems": data.get("FinancialProblems") or "",
        "Fraud": data.get("Fraud") or "",
        "Seizure": data.get("Seizure") or "",
        "DisqualificationFromDriving": data.get("DisqualificationFromDriving") or "",
        "Agreement": data.get("Agreement") or "J",
        "IncludeDocuments": True,
    })
    return body


# ── HTTP plumbing ────────────────────────────────────────────────────────────
def _headers(api_version: str | None = None) -> dict:
    h = _auth_headers()
    h["api-version"] = api_version or settings.RISK_API_VERSION
    return h


def _risk_reason(res) -> str:
    """Haal een leesbare reden uit een RISK-foutrespons (MessageDetail of
    Message, soms Error.Message), opgeschoond van regeleindes. Lege string als
    er niets bruikbaars is (bv. een transportfout zonder JSON)."""
    try:
        d = res.json()
    except (ValueError, AttributeError):
        return ""
    if not isinstance(d, dict):
        return ""
    msg = d.get("MessageDetail") or d.get("Message") or ""
    if not msg and isinstance(d.get("Error"), dict):
        msg = d["Error"].get("Message") or ""
    msg = re.sub(r"\s*\r?\n\s*", " ", str(msg)).strip()
    return msg


def _post(url: str, body: dict, *, api_version: str | None = None) -> requests.Response:
    try:
        return requests.post(url, json=body, headers=_headers(api_version),
                             timeout=settings.RISK_API_TIMEOUT)
    except requests.RequestException as exc:
        raise RiskAPIError(f"RISK niet bereikbaar: {exc}", upstream_down=True, status=503)


def _get(url: str, *, api_version: str | None = None) -> requests.Response:
    try:
        return requests.get(url, headers=_headers(api_version), timeout=settings.RISK_API_TIMEOUT)
    except requests.RequestException as exc:
        raise RiskAPIError(f"RISK niet bereikbaar: {exc}", upstream_down=True, status=503)


def _motor(endpoint: str) -> str:
    return f"{_base()}/Motor/{endpoint}?api-version={settings.RISK_API_VERSION}"


# ── vehicle lookup ───────────────────────────────────────────────────────────
def get_vehicle_info(license_plate: str) -> dict:
    """GET /Data/GetPrivateMotorInfo. Returns the motor properties dict (Brand,
    Model, Type, ManufacturingYear, CylinderCapacity, DayValue, MotorSignCode,
    advised Coverage, …). Tries a couple of api-versions for robustness."""
    plate = _plate(license_plate)
    if not plate:
        raise RiskAPIError("Geen kenteken opgegeven.", status=400)
    base = f"{_base()}/Data/GetPrivateMotorInfo?LicensePlate={plate}"
    errors: list[str] = []
    all_upstream_down = True
    for ver in (settings.RISK_API_VERSION, "10.0", "9.0", "9"):
        url = f"{base}&BrokerID={_broker()}&api-version={ver}"
        try:
            res = _get(url, api_version=ver)
        except RiskAPIError as exc:
            errors.append(f"v{ver}: transport {exc.message}")
            continue
        raw = res.text or ""
        logger.debug("[motor lookup v%s] %s %s", ver, res.status_code, raw[:200])
        if res.ok:
            return res.json() if raw.strip() else {}
        if res.status_code < 500 or res.status_code == 501:
            all_upstream_down = False
        errors.append(f"v{ver}: {res.status_code} {raw[:150]}")
    if all_upstream_down:
        raise RiskAPIError(
            "De kentekenservice is tijdelijk niet bereikbaar. Probeer het over enkele minuten opnieuw.",
            upstream_down=True, status=503)
    raise RiskAPIError("Kenteken niet gevonden. Controleer het kenteken en probeer opnieuw.", status=404)


def get_address_info(zipcode, housenumber, addition="") -> dict:
    """POST /Data/GetAddressInformation → {'Street', 'Place'} voor een postcode +
    huisnummer. Geeft {} terug bij een onbekend adres (404) of fout, zodat de
    aanroeper kan doorgaan zonder te crashen."""
    zc = str(zipcode or "").upper().replace(" ", "")
    num, extra = _house_split(housenumber)
    hn = _num(num, 0)
    if not zc or not hn:
        return {}
    url = f"{_base()}/Data/GetAddressInformation?api-version={settings.RISK_API_VERSION}"
    body = {"ZipCode": zc, "HouseNumber": hn,
            "HouseNumberAddition": addition or extra or "", "BrokerID": _broker()}
    try:
        res = _post(url, body)
    except RiskAPIError:
        return {}
    if not res.ok:
        return {}
    try:
        d = res.json()
    except ValueError:
        return {}
    return {"Street": d.get("Street") or "", "Place": d.get("Place") or ""}


def _ensure_address(data: dict) -> None:
    """Vul Street/Place van de verzekeringnemer aan via GetAddressInformation als
    ze ontbreken. Offerte/aanvraag vereisen straat + plaats; de bestuurder leidt
    RISK zelf af uit DriverZipCode + DriverHouseNumber (zelfde adres in onze flow).
    Faalt stil: bij een onbekend adres laten we RISK de nette validatiefout geven."""
    if data.get("Street") and data.get("Place"):
        return
    info = get_address_info(
        data.get("ZipCode") or data.get("DriverZipCode"),
        data.get("HouseNumber") or data.get("DriverHouseNumber"),
        data.get("HouseNumberAddition") or data.get("DriverHouseNumberAddition") or "")
    if info.get("Street"):
        data["Street"] = info["Street"]
    if info.get("Place"):
        data["Place"] = info["Place"]


def validate_sign_code(license_plate: str, sign_code: str) -> bool:
    """Validate a license plate + meldcode (MotorSignCode) combination via the
    Data lookup. Returns True/False; raises only on transport failure."""
    plate = _plate(license_plate)
    url = (f"{_base()}/Data/GetPrivateMotorSignCodeInfo"
           f"?LicensePlate={plate}&MotorSignCode={sign_code}&BrokerID={_broker()}")
    res = _get(url)
    if not res.ok:
        return False
    try:
        data = res.json()
    except ValueError:
        return False
    val = (data.get("LicensePlateMotorSignCode") or data.get("Result") or "")
    return str(val).lower() in ("correct", "true", "1")


# ── premiums ─────────────────────────────────────────────────────────────────
def _premium_list(parsed):
    if isinstance(parsed, dict):
        return parsed.get("CalculatedPremiums", parsed)
    return parsed


def _no_coverage(res, context: str) -> bool:
    """True when RISK returns no premiums for this request. 204 = geen dekking
    beschikbaar. 406 = afgewezen invoer (bv. ValueAccessories moet 0/1000/2500/
    5000 zijn): de wizard beperkt die velden al, dus 406 hoort niet voor te komen
    — we loggen de RISK-MessageDetail zodat een gemaskeerde fout zichtbaar blijft
    i.p.v. stil als 'geen dekking' te verdwijnen."""
    if res.status_code == 204:
        return True
    if res.status_code == 406:
        try:
            data = res.json()
            detail = data.get("MessageDetail") or data.get("Message")
        except Exception:
            detail = res.text[:200]
        logger.warning("RISK %s afgewezen (406): %s", context, detail)
        return True
    return False


def calculate_premiums(details: dict) -> list:
    """Return the list of insurer premiums. Empty list when RISK signals
    'no coverage available' (HTTP 204) or rejects the input (406, logged)."""
    res = _post(_motor("CalculatePrivatePremiums"), _calc_body(details))
    if _no_coverage(res, "CalculatePrivatePremiums"):
        return []
    if not res.ok:
        raise RiskAPIError(f"Calculate failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code)
    return _premium_list(res.json())


def calculate_additional_coverages(details: dict, identifier: str) -> list:
    """Additional coverages for the chosen insurer (Identifier/PP_ENTREF)."""
    body = {**_calc_body(details), "Identifier": identifier}
    res = _post(_motor("CalculatePrivateAdditionalCoverages"), body)
    if _no_coverage(res, "CalculatePrivateAdditionalCoverages"):
        return []
    if not res.ok:
        raise RiskAPIError(f"Additional coverages failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code)
    parsed = res.json()
    premiums = parsed.get("CalculatedPremiums", []) if isinstance(parsed, dict) else []
    return (premiums[0].get("AdditionalCoverages", []) if premiums else [])


def offer_insurance(data: dict) -> dict:
    """Create an offer (OfferNumber)."""
    _ensure_address(data)
    res = _post(_motor("OfferPrivateInsurance"), _offer_body(data))
    if not res.ok:
        raise RiskAPIError(f"Offer failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code, reason=_risk_reason(res))
    return res.json()


def request_insurance(data: dict) -> dict:
    """Bind the policy — RISK returns a PolicyNumber. REAL application; only call
    after explicit user agreement (Agreement=J)."""
    _ensure_address(data)
    res = _post(_motor("RequestPrivateInsurance"), _request_body(data))
    if not res.ok:
        raise RiskAPIError(f"Request failed: {res.status_code} - {res.text[:200]}",
                           status=res.status_code, reason=_risk_reason(res))
    return res.json()
