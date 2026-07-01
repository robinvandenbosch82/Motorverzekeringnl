"""
Tests for the premie-tool: RISK body builders (pure) + the proxy views (RISK
mocked, so no credentials/network needed). Live RISK integration is a separate
manual check once the motor credentials are in .env. Product: particuliere
motorverzekering (RISK V9).
"""

import json
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.models import Berekening
from core.services import risk
from core.services.risk import RiskAPIError


class BodyBuilderTests(TestCase):
    @override_settings(RISK_BROKER_ID="TESTBROKER", RISK_MOTOR_PRODUCT_VERSION="MV1")
    def test_calculate_body_defaults(self):
        body = risk.build_calculate_body({"LicensePlate": "MG-XX-21"})
        self.assertEqual(body["BrokerID"], "TESTBROKER")   # injected from settings
        self.assertEqual(body["Version"], "MV1")
        self.assertEqual(body["Use"], "P")                 # particulier
        self.assertEqual(body["Coverage"], "1")
        self.assertEqual(body["KmPerYear"], "12000")
        self.assertEqual(body["TheftProtectionClass"], "B4")
        self.assertEqual(body["PaymentPeriod"], 1)
        self.assertIs(body["IncludeXml"], False)
        self.assertEqual(body["LicensePlate"], "MGXX21")   # normalised (no dashes)
        # business-only fields must NOT be present (this is a private product)
        self.assertNotIn("CascoDeductibles", body)
        self.assertNotIn("CompanyTradeRegisterNumber", body)
        self.assertNotIn("OwnerShip", body)                # only added in offer for casco

    def test_coverage_conditional_amounts(self):
        b2 = risk.build_calculate_body({"LicensePlate": "X", "Coverage": "2",
                                        "DayValue": "3000", "ValueAccessories": "1000"})
        self.assertEqual(b2["DayValue"], 3000)
        self.assertEqual(b2["ValueAccessories"], 1000)
        self.assertNotIn("HelmetClothingAmount", b2)       # casco-3 only
        b3 = risk.build_calculate_body({"LicensePlate": "X", "Coverage": "3",
                                        "HelmetClothingAmount": "500"})
        self.assertEqual(b3["HelmetClothingAmount"], 500)
        self.assertNotIn("DayValue", b3)                   # WA+ only

    def test_types_and_birthdate_normalised(self):
        body = risk.build_calculate_body({
            "LicensePlate": "X", "ClaimFreeYears": "10", "PaymentPeriod": "12",
            "DriverHouseNumber": "12", "DriverBirthdate": "01-02-1990"})
        self.assertEqual(body["ClaimFreeYears"], 10)       # coerced to int
        self.assertEqual(body["PaymentPeriod"], 12)
        self.assertEqual(body["DriverHouseNumber"], 12)
        self.assertEqual(body["DriverBirthdate"], "1990-02-01")  # DD-MM-YYYY → ISO

    def test_request_body_binding_fields(self):
        body = risk.build_request_body({"LicensePlate": "X", "Coverage": "1",
                                        "CarSignCode": "1234"})
        self.assertEqual(body["Agreement"], "J")           # default
        self.assertEqual(body["LicencePlateHolder"], "A")
        self.assertEqual(body["DriverLicense"], "J")
        self.assertIn("Cancelled", body)                   # acceptance questions present
        # RISK verwacht de meldcode in MotorSignCode (niet CarSignCode); de
        # frontend levert 'm onder CarSignCode en de builder mapt 'm om.
        self.assertEqual(body["MotorSignCode"], "1234")
        self.assertNotIn("CarSignCode", body)
        # Lege telefoonvelden worden weggelaten (RISK weigert een lege string).
        self.assertNotIn("PhoneNumber", body)
        # Straat/plaats-velden aanwezig (worden via GetAddressInformation gevuld).
        self.assertIn("Street", body)
        self.assertIn("Place", body)

    def test_phone_numbers_cleaned_and_optional(self):
        # Leeg mobiel/telefoon -> veld weggelaten (RISK weigert een lege string).
        b1 = risk.build_offer_body({"LicensePlate": "X", "Coverage": "1"})
        self.assertNotIn("MobileNumber", b1)
        self.assertNotIn("PhoneNumber", b1)
        # Gevuld -> opmaak (spaties/streepjes) gestript, leading + behouden.
        b2 = risk.build_offer_body({"LicensePlate": "X", "Coverage": "1",
                                    "MobileNumber": "06-19 90 00 01", "PhoneNumber": "+31 20 123 4567"})
        self.assertEqual(b2["MobileNumber"], "0619900001")
        self.assertEqual(b2["PhoneNumber"], "+31201234567")


class VehicleEndpointTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = reverse("premie_voertuig")

    def _post(self, payload):
        return self.c.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_short_plate_rejected(self):
        r = self._post({"licensePlate": "AB"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("geldig kenteken", r.json()["error"])

    @mock.patch("core.views_premie.risk.get_vehicle_info")
    def test_valid_lookup_logs_berekening(self, m):
        m.return_value = {"Brand": "Yamaha", "Model": "MT-07"}
        r = self._post({"licensePlate": "mg-xx-21"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["Brand"], "Yamaha")
        m.assert_called_once_with("MGXX21")                # stripped + uppercased
        obj = Berekening.objects.get()
        self.assertEqual(obj.license_plate, "MGXX21")
        self.assertEqual(obj.status, "vehicle-lookup")

    @mock.patch("core.views_premie.risk.get_vehicle_info")
    def test_upstream_down_returns_503(self, m):
        m.side_effect = RiskAPIError("down", upstream_down=True, status=503)
        r = self._post({"licensePlate": "MGXX21"})
        self.assertEqual(r.status_code, 503)
        self.assertTrue(r.json()["upstreamDown"])

    @mock.patch("core.views_premie.risk.get_vehicle_info")
    def test_not_found_returns_404(self, m):
        m.side_effect = RiskAPIError("nope", status=404)
        r = self._post({"licensePlate": "MGXX21"})
        self.assertEqual(r.status_code, 404)


class AddressEndpointTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = reverse("premie_adres")

    def _post(self, payload):
        return self.c.post(self.url, data=json.dumps(payload), content_type="application/json")

    @mock.patch("core.views_premie.risk.get_address_info")
    def test_resolves_street_and_place(self, m):
        m.return_value = {"Street": "Papendorpseweg", "Place": "Utrecht"}
        r = self._post({"DriverZipCode": "3528 BJ", "DriverHouseNumber": "99"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"Street": "Papendorpseweg", "Place": "Utrecht"})

    @mock.patch("core.views_premie.risk.get_address_info")
    def test_unknown_address_is_404(self, m):
        m.return_value = {}
        r = self._post({"DriverZipCode": "9999ZZ", "DriverHouseNumber": "1"})
        self.assertEqual(r.status_code, 404)
        self.assertIn("niet gevonden", r.json()["error"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AanvraagNotificationTests(TestCase):
    def _obj(self):
        return Berekening.objects.create(
            session_id="t", license_plate="36MLBH", coverage="3", policy_number="9999APP-1",
            selected_result={"CompanyName": "Nationale-Nederlanden"},
            request_data={"Name": "Bosch", "NameInfix": "van den", "Initials": "RG",
                          "Email": "klant@voorbeeld.nl", "MobileNumber": "0611"})

    def test_notifies_configured_address(self):
        from django.core import mail
        from core.models import SiteSettings
        from core.views_premie import _notify_aanvraag
        s = SiteSettings.load(); s.aanvraag_notify_email = "team@voorbeeld.nl"; s.save()
        _notify_aanvraag(self._obj())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["team@voorbeeld.nl"])
        self.assertIn("klant@voorbeeld.nl", mail.outbox[0].body)     # klant-e-mail in de body
        self.assertIn("9999APP-1", mail.outbox[0].body)              # polisnummer

    def test_no_notification_when_empty(self):
        from django.core import mail
        from core.models import SiteSettings
        from core.views_premie import _notify_aanvraag
        s = SiteSettings.load(); s.aanvraag_notify_email = ""; s.save()
        _notify_aanvraag(self._obj())
        self.assertEqual(len(mail.outbox), 0)


class CalculateEndpointTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = reverse("premie_bereken")

    def _post(self, payload):
        return self.c.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_missing_plate(self):
        self.assertEqual(self._post({"details": {}}).status_code, 400)

    def test_requires_driver_fields(self):
        r = self._post({"details": {"LicensePlate": "MGXX21"}})
        self.assertEqual(r.status_code, 400)
        self.assertIn("postcode", r.json()["error"])

    @mock.patch("core.views_premie.risk.calculate_premiums")
    def test_valid_calculate_logs(self, m):
        m.return_value = [{"Identifier": "X", "Premium": 12.0}]
        r = self._post({"details": {"LicensePlate": "MGXX21", "Coverage": "3",
                                    "DriverZipCode": "1011AB", "DriverHouseNumber": "1",
                                    "DriverBirthdate": "1990-01-01"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)
        obj = Berekening.objects.get()
        self.assertEqual(obj.coverage, "3")
        self.assertEqual(obj.status, "calculated")

    @mock.patch("core.views_premie.risk.calculate_premiums")
    def test_no_coverage_empty_list(self, m):
        m.return_value = []
        r = self._post({"details": {"LicensePlate": "MGXX21", "DriverZipCode": "1011AB",
                                    "DriverHouseNumber": "1", "DriverBirthdate": "1990-01-01"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])


class AanvraagEndpointTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = reverse("premie_aanvraag")

    def _post(self, payload):
        return self.c.post(self.url, data=json.dumps(payload), content_type="application/json")

    def _full_payload(self):
        return {"data": {"LicensePlate": "MGXX21", "Agreement": "J", "Name": "Jansen",
                         "Initials": "J", "Email": "a@b.nl", "MobileNumber": "0612345678",
                         "IBAN": "NL00BANK0123456789", "selectedIdentifier": "12345A001P001"}}

    def test_requires_agreement(self):
        p = self._full_payload(); p["data"]["Agreement"] = ""
        r = self._post(p)
        self.assertEqual(r.status_code, 400)
        self.assertIn("slotverklaring", r.json()["error"])

    def test_requires_fields(self):
        p = self._full_payload(); p["data"]["IBAN"] = ""
        self.assertEqual(self._post(p).status_code, 400)

    @mock.patch("core.views_premie.risk.request_insurance")
    def test_valid_request_stores_policy(self, m):
        m.return_value = {"PolicyNumber": "POL-123"}
        r = self._post(self._full_payload())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["PolicyNumber"], "POL-123")
        obj = Berekening.objects.get()
        self.assertEqual(obj.policy_number, "POL-123")
        self.assertEqual(obj.status, "requested")

    @mock.patch("core.views_premie.risk.request_insurance")
    def test_request_failure_marks_failed(self, m):
        m.side_effect = RiskAPIError("boom", status=502)
        r = self._post(self._full_payload())
        self.assertEqual(r.status_code, 502)
        self.assertEqual(Berekening.objects.get().status, "failed")


class ToolPageTests(TestCase):
    def test_page_renders_and_sets_csrf_cookie(self):
        r = Client().get(reverse("premie_tool"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("csrftoken", r.cookies)


class RiskV10Tests(TestCase):
    """API v10 builders (separate module, switched by RISK_API_VERSION). v10 is
    the active default; pinning 9.0 restores the flat v9 body."""

    FULL = {
        "LicensePlate": "MG001M", "Coverage": "3", "CarSignCode": "1234",
        "DriverName": "Jansen", "DriverInitials": "J", "DriverGender": "M",
        "Name": "Jansen", "Initials": "J", "Gender": "M", "ZipCode": "3528BJ",
        "HouseNumber": "99", "Street": "Papendorpseweg", "Place": "Utrecht",
        "Birthdate": "1985-05-05", "Email": "a@b.nl", "MobileNumber": "0687334512",
        "IBAN": "NL91ABNA0417164300", "selectedIdentifier": "11111A001B001",
        "driverLicensedToDrive": "J", "motorVehicleOwnerRegisteredOwner": "J",
        "finalStatementReadAndAgreed": "J",
    }

    def test_v10_is_the_active_default(self):
        body = risk._request_body(dict(self.FULL))
        self.assertIn("underwritingQuestions", body)
        self.assertIn("uniformAcceptanceQuestions", body)
        for gone in ("Cancelled", "Fraud", "MotorSignCode", "DriverLicense",
                     "LicencePlateHolder", "Agreement"):
            self.assertNotIn(gone, body)
        uq = body["uniformAcceptanceQuestions"]
        self.assertEqual(uq["finalStatementReadAndAgreed"], "J")
        self.assertEqual(body["underwritingQuestions"]["driverLicensedToDrive"], "J")
        self.assertTrue(body.get("CarSignCode") and body.get("IBAN"))

    @override_settings(RISK_API_VERSION="9.0")
    def test_v9_still_available_when_pinned(self):
        body = risk._request_body(dict(self.FULL))
        self.assertIn("Cancelled", body)
        self.assertNotIn("underwritingQuestions", body)

    def test_v10_explanation_only_when_risk_answer_given(self):
        no = risk._request_body(dict(self.FULL, fraudDeceptionDetrimentPastEightYears="N"))
        yes = risk._request_body(dict(self.FULL, fraudDeceptionDetrimentPastEightYears="J",
                                      fraudDeceptionDetrimentExplanation="toelichting"))
        self.assertNotIn("fraudDeceptionDetrimentExplanation", no["uniformAcceptanceQuestions"])
        self.assertEqual(yes["uniformAcceptanceQuestions"]["fraudDeceptionDetrimentExplanation"],
                         "toelichting")


class HouseNumberTests(TestCase):
    """A house number typed with its addition in one field ('152c') must not
    collapse to 0 — RISK rejects DriverHouseNumber < 1, which blocked calculate."""

    def test_split_helper(self):
        self.assertEqual(risk._house_split("152c"), ("152", "c"))
        self.assertEqual(risk._house_split("152 c"), ("152", "c"))
        self.assertEqual(risk._house_split("152"), ("152", ""))
        self.assertEqual(risk._house_split(""), ("", ""))

    def test_calculate_body_extracts_number_and_addition(self):
        body = risk.build_calculate_body({"LicensePlate": "MG001M", "DriverHouseNumber": "152c"})
        self.assertEqual(body["DriverHouseNumber"], 152)
        self.assertEqual(body["DriverHouseNumberAddition"], "c")
