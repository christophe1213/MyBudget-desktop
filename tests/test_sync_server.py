"""Tests unitaires du serveur de synchronisation local."""
import json
import socket
import unittest
import urllib.error
import urllib.request

from suivi.adapters.driving.sync_server import SyncHTTPServer


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class SyncServerTest(unittest.TestCase):
    def test_port_invalide_refuse(self):
        for port in (0, -1, 65536):
            with self.subTest(port=port), self.assertRaises(ValueError):
                SyncHTTPServer(port)

    def test_health_et_page(self):
        server = SyncHTTPServer(free_port())
        self.assertFalse(server.running)
        server.start()
        self.addCleanup(server.stop)
        self.assertTrue(server.running)
        base = f"http://127.0.0.1:{server.port}"

        with urllib.request.urlopen(f"{base}/health", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response), {"status": "ok", "service": "repere-sync"})
        with urllib.request.urlopen(f"{base}/", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.headers["Content-Type"])

        server.stop()
        self.assertFalse(server.running)

    def test_demarrer_deux_fois_ne_relance_pas(self):
        server = SyncHTTPServer(free_port())
        self.addCleanup(server.stop)
        self.assertEqual(server.start(), server.start())

    def test_qr_generation_if_dependency_is_installed(self):
        server = SyncHTTPServer(8765)
        try:
            png = server.qr_png()
        except RuntimeError:
            self.skipTest("qrcode n'est pas installé")
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_qr_png_sans_dependance_repond_501(self):
        server = SyncHTTPServer(free_port())
        server.qr_png = lambda: (_ for _ in ()).throw(RuntimeError("qrcode absent"))   # simule l'absence de qrcode
        server.start()
        self.addCleanup(server.stop)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"http://127.0.0.1:{server.port}/qr.png", timeout=3)
        self.assertEqual(caught.exception.code, 501)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
