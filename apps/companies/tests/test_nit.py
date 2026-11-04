from django.test import SimpleTestCase

from apps.companies.nit import InvalidNit, Nit, check_digit


class CheckDigitTests(SimpleTestCase):
    def test_known_values(self):
        # Calculados a mano con los pesos de la DIAN.
        self.assertEqual(check_digit("900123456"), 8)
        self.assertEqual(check_digit("800197268"), 4)  # NIT publico de la DIAN


class ParseTests(SimpleTestCase):
    def test_all_formats_of_the_same_nit_are_equal(self):
        expected = Nit("900123456")
        for raw in ("900.123.456-8", "900123456-8", "900123456", " 900 123 456-8 "):
            self.assertEqual(Nit.parse(raw), expected, raw)

    def test_wrong_check_digit_is_rejected(self):
        with self.assertRaisesMessage(InvalidNit, "dígito de verificación"):
            Nit.parse("900.123.456-7")

    def test_glued_check_digit_is_rejected_to_avoid_duplicates(self):
        with self.assertRaisesMessage(InvalidNit, "guion"):
            Nit.parse("9001234568")

    def test_ten_digit_number_without_glued_check_digit_is_valid(self):
        self.assertEqual(Nit.parse("9001234567").number, "9001234567")

    def test_invalid_values(self):
        for raw in ("", "   ", "abc", "12345", "12345678901", "090012345", "900123456-", "900-123", None):
            with self.assertRaises(InvalidNit, msg=raw):
                Nit.parse(raw)

    def test_display_format(self):
        self.assertEqual(str(Nit("900123456")), "900.123.456-8")
