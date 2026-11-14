
from django.test import SimpleTestCase

from apps.dashboard.panels import greeting


class GreetingTests(SimpleTestCase):
    def test_changes_with_the_hour(self):
        self.assertEqual(greeting(8), "Buenos días")
        self.assertEqual(greeting(15), "Buenas tardes")
        self.assertEqual(greeting(21), "Buenas noches")


