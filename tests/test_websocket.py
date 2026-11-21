"""Tests du WebSocket minimal et de son intégration dans le serveur de synchronisation (vrais sockets locaux)."""
import struct
import time
import unittest
import urllib.error
import urllib.request

from suivi.adapters.driving.sync_server import SyncHTTPServer
from suivi.adapters.driving.websocket import (
    MAX_MESSAGE, OP_BINARY, OP_CLOSE, OP_CONTINUATION, OP_PING, OP_PONG, OP_TEXT, accept_key, apply_mask,
    encode_frame)
from tests.ws_client import WsClient, free_port


def wait_for(server, count, timeout=3.0):
    events = []
    end = time.time() + timeout
    while len(events) < count and time.time() < end:
        events += server.poll()
        time.sleep(0.01)
    return events


class CodecTest(unittest.TestCase):
    def test_cle_d_acceptation_de_la_rfc(self):
        self.assertEqual(accept_key("dGhlIHNhbXBsZSBub25jZQ=="), "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_masque_reversible(self):
        mask = b"\x37\xfa\x21\x3d"
        for data in (b"", b"a", b"Hello", bytes(range(256)) * 3):
            self.assertEqual(apply_mask(apply_mask(data, mask), mask), data)

    def test_longueurs_d_en_tete(self):
        self.assertEqual(encode_frame(OP_TEXT, b"x" * 125)[1], 125)
        frame = encode_frame(OP_TEXT, b"x" * 126)
        self.assertEqual((frame[1], struct.unpack(">H", frame[2:4])[0]), (126, 126))
        frame = encode_frame(OP_TEXT, b"x" * 70000)
        self.assertEqual((frame[1], struct.unpack(">Q", frame[2:10])[0]), (127, 70000))


class ServerWebSocketTest(unittest.TestCase):
    def setUp(self):
        self.server = SyncHTTPServer(free_port())
        self.server.start()
        self.addCleanup(self.server.stop)
        self.clients = []
        self.addCleanup(lambda: [c.close() for c in self.clients])

    def connect(self, token=None):
        client = WsClient(self.server.port, token or self.server.token)
        self.clients.append(client)
        return client

    def test_jeton_obligatoire(self):
        for token in ("", "mauvais"):
            with self.subTest(token=token), self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(f"http://127.0.0.1:{self.server.port}/ws?token={token}", timeout=3)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()

    def test_requete_sans_en_tetes_websocket_refusee(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"http://127.0.0.1:{self.server.port}/ws?token={self.server.token}", timeout=3)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()

    def test_adresse_d_appairage_contient_le_jeton(self):
        self.assertTrue(self.server.pairing_url.endswith(f"/?token={self.server.token}"))
        self.assertNotIn(self.server.token, self.server.base_url)

    def test_connexion_messages_et_deconnexion(self):
        client = self.connect()
        self.assertEqual(client.status, 101)
        (connected,) = wait_for(self.server, 1)
        self.assertEqual((connected.kind, connected.address), ("connected", "127.0.0.1"))
        self.assertEqual(self.server.client_count, 1)

        client.send_text("bonjour é")
        (message,) = wait_for(self.server, 1)
        self.assertEqual((message.kind, message.text, message.client), ("message", "bonjour é", connected.client))

        self.assertEqual(self.server.send("réponse", connected.client), 1)
        self.assertEqual(client.recv_text(), "réponse")
        self.assertEqual(self.server.send("à tous"), 1)
        self.assertEqual(client.recv_text(), "à tous")
        self.assertEqual(self.server.send("personne", client=999), 0)

        client.close()
        (gone,) = wait_for(self.server, 1)
        self.assertEqual((gone.kind, gone.client), ("disconnected", connected.client))
        self.assertEqual(self.server.client_count, 0)

    def test_grand_message_dans_les_deux_sens(self):
        client = self.connect()
        wait_for(self.server, 1)
        big = "é" * 100_000   # > 64 Kio : longueur sur 8 octets
        client.send_text(big)
        (message,) = wait_for(self.server, 1)
        self.assertEqual(message.text, big)
        self.server.send(big)
        self.assertEqual(client.recv_text(), big)

    def test_ping_pong_et_messages_fragmentes(self):
        client = self.connect()
        wait_for(self.server, 1)
        client.send_frame(OP_PING, b"x")
        self.assertEqual(client.recv_frame(), (OP_PONG, b"x"))
        client.send_frame(OP_TEXT, "par".encode(), final=False)
        client.send_frame(OP_PING, b"")                       # contrôle intercalé : permis
        client.send_frame(OP_CONTINUATION, "tie".encode(), final=True)
        self.assertEqual(client.recv_frame(), (OP_PONG, b""))
        texts = [e.text for e in wait_for(self.server, 1)]
        self.assertEqual(texts, ["partie"])

    def test_violations_fermees_avec_le_bon_code(self):
        cases = {
            "non masquée": (1002, lambda c: c.send_frame(OP_TEXT, b"x", masked=False)),
            "binaire": (1003, lambda c: c.send_frame(OP_BINARY, b"x")),
            "trop gros": (1009, lambda c: c.send_frame(OP_TEXT, b"", declared_length=MAX_MESSAGE + 1)),
            "UTF-8 invalide": (1007, lambda c: c.send_frame(OP_TEXT, b"\xff\xfe")),
            "suite sans début": (1002, lambda c: c.send_frame(OP_CONTINUATION, b"x")),
        }
        for label, (code, action) in cases.items():
            with self.subTest(label):
                client = self.connect()
                action(client)
                opcode, payload = client.recv_frame()
                self.assertEqual((opcode, struct.unpack(">H", payload[:2])[0]), (OP_CLOSE, code))

    def test_fermeture_demandee_par_le_client(self):
        client = self.connect()
        wait_for(self.server, 1)
        client.send_frame(OP_CLOSE, struct.pack(">H", 1000))
        self.assertEqual(client.recv_frame()[0], OP_CLOSE)
        self.assertEqual([e.kind for e in wait_for(self.server, 1)], ["disconnected"])

    def test_arret_du_serveur_coupe_les_connexions(self):
        client = self.connect()
        wait_for(self.server, 1)
        self.server.stop()
        self.assertIsNone(client.recv_frame())   # fin de flux, pas de blocage

    def test_page_de_test_servie(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.server.port}/", timeout=3) as response:
            body = response.read().decode("utf-8")
        self.assertIn("WebSocket", body)
        self.assertIn("/ws?token=", body)


if __name__ == "__main__":
    unittest.main()
