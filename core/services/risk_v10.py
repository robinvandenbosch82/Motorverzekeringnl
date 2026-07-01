"""RISK API v10 body builders — Private Motor Insurance (particulier).

Kept SEPARATE from the v9 builders in core.services.risk so the whole flow rolls
back by setting RISK_API_VERSION back to "9.0". core.services.risk selects these
at runtime when RISK_API_VERSION starts with "10".

Only the acceptance section changes in v10 (the version note: "UniformAcceptance
Questions added, underwritingQuestions deleted"), so the standard calculate/offer
fields are reused verbatim from the v9 builders. The v9 flat acceptance fields
(Cancelled/Convicted/Damage/Fraud/Seizure/DisqualificationFromDriving), plus
DriverLicense / LicencePlateHolder / MotorSignCode / Agreement, are replaced by:

    underwritingQuestions      → driverLicensedToDrive, ClaimFreeYears, numberOfClaims
    uniformAcceptanceQuestions → the particuliere slotvragen incl. finalStatementReadAndAgreed
    objectOwner / registrationCertificateHolder (only when not the owner+holder)

Verified against the RISK acc environment. Note the particuliere attribute names
differ from the zakelijke set: finalStatementReadAndAgreed (not ...Authorized...),
bankruptcy... (no "company"), damageSufferedOrCausedPastFiveYears (no ...RequestedPolicy).
The meldcode field is CarSignCode in v10 (was MotorSignCode in v9).
"""

from __future__ import annotations

from . import risk as _v9

# Slot question -> (answer that needs an explanation, explanation attribute).
_UNIFORM_QUESTIONS = {
    "motorVehicleOwnerRegisteredOwner": ("N", "ownerRegisteredOwnerExplanation"),
    "drivingBanPastFiveYears": ("J", "drivingBanPastFiveYearsExplanation"),
    "motorVehicleCurrentlyDamaged": ("J", "motorVehicleDamageExplanation"),
    "criminalOffenceSuspectedPastEightYears": ("J", "criminalOffenceSuspectedExplanation"),
    "fraudDeceptionDetrimentPastEightYears": ("J", "fraudDeceptionDetrimentExplanation"),
    "statutoryDebtRestructuring": ("J", "debtRestructuringExplanation"),
    "insuranceCancelledOrRefusedPastFiveYears": ("J", "insuranceCancelledOrRefusedExplanation"),
    "bankruptcyGuardianshipAdministrationMoratoriumPastFiveYears":
        ("J", "bankruptcyGuardianshipAdministrationMoratoriumExplanation"),
    "damageSufferedOrCausedPastFiveYears": ("J", "damageSufferedOrCausedExplanation"),
}
_DEFAULT_YES = {"motorVehicleOwnerRegisteredOwner", "driverLicensedToDrive"}


def _jn(data, attr):
    val = str(data.get(attr) or "").strip().upper()
    if val in ("J", "N"):
        return val
    return "J" if attr in _DEFAULT_YES else "N"


def build_calculate_body(details: dict) -> dict:
    # Pricing is unchanged in v10.
    return _v9.build_calculate_body(details)


def build_offer_body(data: dict) -> dict:
    return _v9.build_offer_body(data)


def _acceptance_objects(data: dict) -> dict:
    licensed = _jn(data, "driverLicensedToDrive")
    damage_yes = _jn(data, "damageSufferedOrCausedPastFiveYears") == "J"

    underwriting = {
        "ClaimFreeYears": _v9._num(data.get("ClaimFreeYears"), 0),
        "driverLicensedToDrive": licensed,
    }
    if licensed == "N" and data.get("driverLicensedToExplanation"):
        underwriting["driverLicensedToExplanation"] = data["driverLicensedToExplanation"]
    if damage_yes:
        underwriting["numberOfClaims"] = _v9._num(data.get("numberOfClaims"), 0)

    uniform = {}
    for attr, (trigger, expl_attr) in _UNIFORM_QUESTIONS.items():
        answer = _jn(data, attr)
        uniform[attr] = answer
        if answer == trigger and data.get(expl_attr):
            uniform[expl_attr] = data[expl_attr]
    uniform["finalStatementReadAndAgreed"] = _jn(data, "finalStatementReadAndAgreed")
    return {"underwritingQuestions": underwriting, "uniformAcceptanceQuestions": uniform}


def _person_block(data: dict, prefix: str) -> dict | None:
    ref = str(data.get(f"{prefix}.refType") or "").strip()
    if not ref:
        return None
    block = {"refType": ref}
    for f in ("initials", "prefixes", "surname", "birthDate", "gender",
              "houseNumber", "houseNumberAddition", "postalCode"):
        val = data.get(f"{prefix}.{f}")
        if val:
            block[f] = _v9._num(val, 0) if f == "houseNumber" else val
    return block


def build_request_body(data: dict) -> dict:
    """v10 bind body: the v9 offer body + the binding fields (IBAN, meldcode) and
    the two nested question objects; owner/holder blocks only when not the owner."""
    body = _v9.build_offer_body(data)
    body.update({
        "CarSignCode": data.get("CarSignCode") or data.get("MotorSignCode") or "",
        "IBAN": (data.get("IBAN") or "").upper().replace(" ", ""),
        "collectionAccountInNameOf": data.get("collectionAccountInNameOf") or "",
        "IncludeDocuments": True,
    })
    body.update(_acceptance_objects(data))
    if _jn(data, "motorVehicleOwnerRegisteredOwner") == "N":
        owner = _person_block(data, "objectOwner")
        holder = _person_block(data, "registrationCertificateHolder")
        if owner:
            body["objectOwner"] = owner
        if holder:
            body["registrationCertificateHolder"] = holder
    return body
