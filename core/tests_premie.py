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
        body = risk.build_request_body({"LicensePlate": "X", "Coverage": "1"})
        self.assertEqual(body["Agreement"], "J")           # default
        self.assertEqual(body["LicencePlateHolder"], "A")
        self.assertEqual(body["DriverLicense"], "J")
        self.assertIn("Cancelled", body)                   # acceptance questions present
        self.assertIn("CarSignCode", body)                 # meldcode field present


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
