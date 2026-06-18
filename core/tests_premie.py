"""
Tests for the premie-tool: RISK body builders (pure) + the proxy views (with
RISK mocked, so no credentials/network needed). Live RISK integration is a
separate manual check once credentials are in .env.
"""

import json
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.models import Berekening
from core.services import risk
from core.services.risk import RiskAPIError


class BodyBuilderTests(TestCase):
    @override_settings(RISK_BROKER_ID="TESTBROKER")
    def test_calculate_body_defaults(self):
        body = risk.build_calculate_body({"LicensePlate": "VNT88K"})
        self.assertEqual(body["BrokerID"], "TESTBROKER")  # injected from settings
        self.assertEqual(body["KmPerYear"], "20000")
        self.assertEqual(body["CascoDeductibles"], 250)
        self.assertEqual(body["Coverage"], "1")
        self.assertEqual(body["OwnerShip"], "E")
        self.assertEqual(body["PaymentPeriod"], 1)
        self.assertIs(body["IncludeXml"], False)

    def test_calculate_body_passthrough_and_types(self):
        body = risk.build_calculate_body({
            "LicensePlate": "VNT88K", "Coverage": "3", "ClaimFreeYears": "10",
            "PaymentPeriod": "12", "DriverHouseNumber": "12", "CascoDeductibles": "500",
        })
        self.assertEqual(body["Coverage"], "3")
        self.assertEqual(body["ClaimFreeYears"], 10)        # coerced to int
        self.assertEqual(body["PaymentPeriod"], 12)
        self.assertEqual(body["DriverHouseNumber"], 12)
        self.assertEqual(body["CascoDeductibles"], 500)

    def test_birthdate_alias(self):
        self.assertEqual(risk.build_calculate_body({"DriverBirthdate": "1980-01-01"})["DriverBirthDate"],
                         "1980-01-01")

    def test_request_body_binding_fields(self):
        body = risk.build_request_body({"LicensePlate": "VNT88K"})
        self.assertEqual(body["Agreement"], "J")            # default
        self.assertEqual(body["LicencePlateHolder"], "3")
        self.assertEqual(body["DriverLicensedToDrive"], "J")
        self.assertIn("Cancelled", body)                    # acceptance questions present


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
        m.return_value = {"Brand": "Ford", "Model": "Transit", "isVan": True}
        r = self._post({"licensePlate": "vn-t88-k"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["Brand"], "Ford")
        m.assert_called_once_with("VNT88K")              # stripped + uppercased
        obj = Berekening.objects.get()
        self.assertEqual(obj.license_plate, "VNT88K")
        self.assertTrue(obj.is_van)
        self.assertEqual(obj.status, "vehicle-lookup")

    @mock.patch("core.views_premie.risk.get_vehicle_info")
    def test_upstream_down_returns_503(self, m):
        m.side_effect = RiskAPIError("down", upstream_down=True, status=503)
        r = self._post({"licensePlate": "VNT88K"})
        self.assertEqual(r.status_code, 503)
        self.assertTrue(r.json()["upstreamDown"])

    @mock.patch("core.views_premie.risk.get_vehicle_info")
    def test_not_found_returns_404(self, m):
        m.side_effect = RiskAPIError("nope", status=404)
        r = self._post({"licensePlate": "VNT88K"})
        self.assertEqual(r.status_code, 404)


class CalculateEndpointTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = reverse("premie_bereken")

    def _post(self, payload):
        return self.c.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_missing_plate(self):
        self.assertEqual(self._post({"details": {}, "isVan": True}).status_code, 400)

    def test_bad_kvk(self):
        r = self._post({"details": {"LicensePlate": "VNT88K", "CompanyTradeRegisterNumber": "123"},
                        "isVan": True})
        self.assertEqual(r.status_code, 400)
        self.assertIn("KvK", r.json()["error"])

    def test_driver_one_requires_fields(self):
        r = self._post({"details": {"LicensePlate": "VNT88K", "DriverOne": "J"}, "isVan": True})
        self.assertEqual(r.status_code, 400)

    @mock.patch("core.views_premie.risk.calculate_premiums")
    def test_valid_calculate_logs(self, m):
        m.return_value = [{"Identifier": "X", "Premium": 41.0}]
        r = self._post({"details": {"LicensePlate": "VNT88K", "Coverage": "3",
                                    "DriverOne": "N"}, "isVan": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)
        obj = Berekening.objects.get()
        self.assertEqual(obj.coverage, "3")
        self.assertEqual(obj.status, "calculated")

    @mock.patch("core.views_premie.risk.calculate_premiums")
    def test_no_coverage_empty_list(self, m):
        m.return_value = []
        r = self._post({"details": {"LicensePlate": "VNT88K", "DriverOne": "N"}, "isVan": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])


class AanvraagEndpointTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = reverse("premie_aanvraag")

    def _post(self, payload):
        return self.c.post(self.url, data=json.dumps(payload), content_type="application/json")

    def _full_payload(self):
        return {"data": {"LicensePlate": "VNT88K", "Agreement": "J", "CompanyName": "Test BV",
                         "CompanyEmail": "a@b.nl", "CompanyPhoneNumber": "0612345678",
                         "IBAN": "NL00BANK0123456789", "selectedIdentifier": "12345A001B001"},
                "isVan": True}

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
