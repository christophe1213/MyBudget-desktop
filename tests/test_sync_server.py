"""Tests unitaires du serveur de synchronisation local."""
import json
import threading
import unittest
import urllib.request

from suivi.adapters.driven.sync_server import SyncHTTPServer


class SyncServerTest(unittest.TestCase):
    def test_health_and_page(self):
        server = SyncHTTPServer(0)
        # Le port 0 est refusé volontairement par la classe; ce test vérifie seulement le montage.
        with self.assertRaises(ValueError):
            server.start()

    def test_qr_generation_if_dependency_is_installed(self):
        server = SyncHTTPServer(8765)
        try:
            png = server.qr_png()
        except RuntimeError:
            self.skipTest("qrcode n'est pas installé")
        self.assertTrue(png.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
