"""
Premie-tool proxy views — particuliere motorverzekering (RISK V9).

The browser's wizard talks ONLY to these endpoints; they hold the RISK
credentials (via core.services.risk), validate input, call RISK, and log every
step to the Berekening model.

Endpoints (all POST, JSON in/out, same-origin + CSRF protected):
    /premie/api/voertuig      → vehicle lookup (GetPrivateMotorInfo)
    /premie/api/bereken       → calculate premiums
    /premie/api/aanvullend    → additional coverages
    /premie/api/aanvraag      → bind policy (RequestPrivateInsurance, REAL)

The wizard page itself:
    /motorverzekering-berekenen/  → SSR shell + JS island
"""

from __future__ import annotations

import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import Berekening
from .services import risk
from .services.risk import RiskAPIError

logger = logging.getLogger("core.premie")


# ── helpers ──────────────────────────────────────────────────────────────────
def _body(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except (ValueError, TypeError):
        return {}


def _err(message: str, status: int = 400, **extra) -> JsonResponse:
    return JsonResponse({"error": message, **extra}, status=status)


def _notify_aanvraag(obj) -> None:
    """Mail een samenvatting van een nieuwe polisaanvraag naar het in de admin
    ingestelde adres (SiteSettings.aanvraag_notify_email). Faalt stil: een
    mailprobleem mag de (al gebonden) aanvraag nooit blokkeren."""
    from django.conf import settings
    from django.core.mail import send_mail
    from .models import SiteSettings

    to = (SiteSettings.load().aanvraag_notify_email or "").strip()
    if not to:
        return
    d = obj.request_data or {}
    sel = obj.selected_result or {}
    naam = " ".join(p for p in (d.get("Initials"), d.get("NameInfix"), d.get("Name")) if p) or "—"
    cov = {"1": "WA", "2": "WA + Casco", "3": "Allrisk"}.get(str(obj.coverage), obj.coverage or "—")
    verzekeraar = sel.get("CompanyName") or sel.get("InsurerName") or sel.get("Name") or "—"
    lines = [
        "Er is een nieuwe motorverzekering-aanvraag binnengekomen.",
        "",
        f"Polisnummer:  {obj.policy_number or '—'}",
        f"Naam:         {naam}",
        f"E-mail:       {d.get('Email') or '—'}",
        f"Telefoon:     {d.get('MobileNumber') or '—'}",
        f"Kenteken:     {obj.license_plate or '—'}",
        f"Dekking:      {cov}",
        f"Verzekeraar:  {verzekeraar}",
        "",
        "Bekijk de volledige aanvraag in de admin onder Berekeningen.",
    ]
    try:
        send_mail(
            subject=f"Nieuwe aanvraag — {obj.license_plate or ''} — polis {obj.policy_number or ''}".strip(" —"),
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Aanvraag-notificatie mailen mislukt (to=%s)", to)


def _client_ip(request) -> str:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", "")) or "?"


def _rate_ok(request, bucket: str, limit: int, window: int = 300) -> bool:
    """Soft per-IP rate limit. Fails open if the cache misbehaves."""
    key = f"premie:{bucket}:{_client_ip(request)}"
    try:
        count = cache.get_or_set(key, 0, window)
        if count is None:
            count = 0
        if count >= limit:
            return False
        cache.incr(key)
    except Exception:
        return True
    return True


def _berekening(request, create: bool = False) -> Berekening | None:
    """Fetch (or create) the Berekening row bound to this session (id lives in
    the server-side session, so the client can't tamper with which row it writes)."""
    bid = request.session.get("berekening_id")
    if bid:
        obj = Berekening.objects.filter(pk=bid).first()
        if obj:
            return obj
    if not create:
        return None
    if not request.session.session_key:
        request.session.save()
    obj = Berekening.objects.create(session_id=request.session.session_key or "")
    request.session["berekening_id"] = obj.pk
    return obj


# ── vehicle lookup ───────────────────────────────────────────────────────────
@require_POST
def vehicle(request):
    if not _rate_ok(request, "voertuig", limit=40):
        return _err("Te veel verzoeken. Probeer het zo opnieuw.", status=429)
    plate_raw = str(_body(request).get("licensePlate", ""))
    plate = "".join(ch for ch in plate_raw.upper() if ch not in "- ")
    if len(plate) < 4:
        return _err("Voer een geldig kenteken in.")
    try:
        info = risk.get_vehicle_info(plate)
    except RiskAPIError as exc:
        status = 503 if exc.upstream_down else 404
        return _err(exc.message, status=status, upstreamDown=exc.upstream_down)

    obj = _berekening(request, create=True)
    obj.license_plate = plate
    obj.vehicle_info = info
    obj.status = "vehicle-lookup"
    obj.current_step = "driver-details"
    obj.save(update_fields=["license_plate", "vehicle_info",
                            "status", "current_step", "updated_at"])
    return JsonResponse(info)


@require_POST
def adres(request):
    """Resolve straat + plaats uit postcode + huisnummer (GetAddressInformation),
    zodat de wizard het adres live kan tonen en bevestigen."""
    if not _rate_ok(request, "adres", limit=60):
        return _err("Te veel verzoeken. Probeer het zo opnieuw.", status=429)
    payload = _body(request)
    info = risk.get_address_info(
        payload.get("DriverZipCode") or payload.get("ZipCode") or "",
        payload.get("DriverHouseNumber") or payload.get("HouseNumber") or "",
        payload.get("DriverHouseNumberAddition") or payload.get("HouseNumberAddition") or "")
    if not info.get("Street"):
        return _err("Adres niet gevonden. Controleer postcode en huisnummer.", status=404)
    return JsonResponse(info)


# ── calculate premiums ───────────────────────────────────────────────────────
@require_POST
def calculate(request):
    if not _rate_ok(request, "bereken", limit=120):
        return _err("Te veel verzoeken. Probeer het zo opnieuw.", status=429)
    details = _body(request).get("details") or {}

    if not details.get("LicensePlate"):
        return _err("Kenteken ontbreekt. Begin opnieuw bij stap 1.")
    missing = [f for f in ("DriverZipCode", "DriverHouseNumber", "DriverBirthdate")
               if not details.get(f) and not details.get(f.replace("Birthdate", "BirthDate"))]
    if missing:
        return _err("Vul je postcode, huisnummer en geboortedatum in.")

    try:
        results = risk.calculate_premiums(details)
    except RiskAPIError as exc:
        status = 503 if exc.upstream_down else 502
        logger.warning("calculate RISK-fout: %s", exc.message)
        return _err(exc.message, status=status, upstreamDown=exc.upstream_down)

    obj = _berekening(request, create=True)
    obj.business_details = details
    obj.coverage = str(details.get("Coverage") or "")
    obj.results = results
    if obj.status in ("started", "vehicle-lookup"):
        obj.status = "calculated"
    obj.current_step = "comparison"
    obj.save(update_fields=["business_details", "coverage", "results",
                            "status", "current_step", "updated_at"])
    return JsonResponse({"results": results})


# ── additional coverages ─────────────────────────────────────────────────────
@require_POST
def additional(request):
    if not _rate_ok(request, "aanvullend", limit=120):
        return _err("Te veel verzoeken. Probeer het zo opnieuw.", status=429)
    data = _body(request)
    details = data.get("details") or {}
    identifier = data.get("identifier") or ""
    if not identifier:
        return _err("Geen verzekeraar geselecteerd.")
    try:
        coverages = risk.calculate_additional_coverages(details, identifier)
    except RiskAPIError as exc:
        status = 503 if exc.upstream_down else 502
        return _err(exc.message, status=status, upstreamDown=exc.upstream_down)

    obj = _berekening(request, create=True)
    obj.selected_result = {"Identifier": identifier}
    obj.additional_coverages = coverages
    obj.status = "additional"
    obj.current_step = "additional"
    obj.save(update_fields=["selected_result", "additional_coverages",
                            "status", "current_step", "updated_at"])
    return JsonResponse({"coverages": coverages})


# ── bind policy (REAL application) ───────────────────────────────────────────
@require_POST
def aanvraag(request):
    if not _rate_ok(request, "aanvraag", limit=15):
        return _err("Te veel verzoeken. Probeer het zo opnieuw.", status=429)
    payload = _body(request).get("data") or {}

    if str(payload.get("Agreement") or "").upper() not in ("J", "TRUE", "1"):
        return _err("Je moet akkoord gaan met de slotverklaring.")
    name = payload.get("Name") or payload.get("DriverName")
    required = {"Naam": name, "E-mail": payload.get("Email"),
                "Mobiel nummer": payload.get("MobileNumber"), "IBAN": payload.get("IBAN")}
    if not payload.get("selectedIdentifier") or any(not v for v in required.values()):
        return _err("Vul alle verplichte velden in (naam, e-mail, mobiel nummer en IBAN).")
    payload["Agreement"] = "J"

    try:
        result = risk.request_insurance(payload)
    except RiskAPIError as exc:
        obj = _berekening(request, create=True)
        obj.status = "failed"
        obj.request_data = payload
        obj.save(update_fields=["status", "request_data", "updated_at"])
        status = 503 if exc.upstream_down else 502
        msg = "Het afsluiten is niet gelukt. Probeer het opnieuw of neem contact op."
        # Toon RISK's leesbare reden mee (bv. "De straat is niet ingevuld."),
        # zodat de bezoeker weet wat hij moet aanpassen. Geen reden = generiek.
        return _err(msg, status=status, detail=(exc.reason or ""))

    obj = _berekening(request, create=True)
    obj.request_data = payload
    obj.policy_number = str(result.get("PolicyNumber") or "")
    obj.status = "requested"
    obj.current_step = "done"
    obj.save(update_fields=["request_data", "policy_number",
                            "status", "current_step", "updated_at"])
    _notify_aanvraag(obj)
    return JsonResponse(result)


def _verzekeraar_enrichment() -> dict:
    """Editable per-insurer data (score + kenmerken) from our CMS, keyed by a
    normalised name so the wizard can enrich the RISK comparison results."""
    import re

    from .models import Verzekeraar

    def norm(name):
        return re.sub(r"[^a-z0-9]", "", (name or "").lower())

    data = {}
    for v in Verzekeraar.objects.filter(active=True):
        data[norm(v.naam)] = {
            "naam": v.naam, "score": v.score, "tags": v.tags_list,
            "omschrijving": v.omschrijving, "reviewCount": v.review_count,
            "beoordeling": v.beoordeling_list, "kenmerken": v.kenmerken_list,
        }
    return data


# ── wizard page (SSR shell) ──────────────────────────────────────────────────
@ensure_csrf_cookie
def tool_page(request):
    """Render the wizard shell. ensure_csrf_cookie so the JS island can read the
    CSRF token for its POSTs to the endpoints above."""
    from . import content
    return render(request, "pages/premie_tool.html", {
        "seo_title": "Motorverzekering berekenen & direct afsluiten | Motorverzekering.nl",
        "seo_description": "Bereken in ongeveer 1 minuut je premie, vergelijk verzekeraars en "
                           "sluit je motorverzekering direct online af.",
        "active_page": "premie_tool",
        "verzekeraar_data": _verzekeraar_enrichment(),
        "secties": content.secties("premie_tool"),
        "risk_v10": risk._use_v10(),
    })
