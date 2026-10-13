"""Live NUT access-isolation regression tests (Python standard library only).

No supported UPS instant command is sent. Authenticated control checks use
an unknown UPS or the unsupported SET handler; authenticated FSD is not sent.
"""
import argparse
import getpass
import shlex
import socket
import unittest


class Connection:
    def __init__(self, host, port):
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(10)
        self.stream = self.sock.makefile("rb")

    def close(self):
        self.stream.close()
        self.sock.close()

    def line(self):
        raw = self.stream.readline()
        if not raw:
            raise RuntimeError("NUT server disconnected")
        return raw.decode("utf-8").strip()

    def query(self, command):
        if "\n" in command or "\r" in command:
            raise ValueError("Command must be one line")
        self.sock.sendall((command + "\n").encode("utf-8"))
        first = self.line()
        if first.startswith("BEGIN LIST "):
            end = "END " + first[6:]
            rows = []
            while True:
                row = self.line()
                if row == end:
                    return rows
                rows.append(row)
                if len(rows) > 1000:
                    raise RuntimeError("Unterminated LIST response")
        return first


class AccessTests(unittest.TestCase):
    host = None
    port = 3493
    ups = None
    username = None
    password = None

    def setUp(self):
        self.client = Connection(self.host, self.port)
        self.addCleanup(self.client.close)

    def reads(self):
        rows = self.client.query("LIST UPS")
        self.assertIsInstance(rows, list)
        self.assertIn(self.ups, [shlex.split(row)[1] for row in rows])
        rows = self.client.query("LIST VAR " + self.ups)
        self.assertIsInstance(rows, list)
        self.assertTrue(rows)
        for row in rows:
            parts = shlex.split(row)
            self.assertEqual(parts[:2], ["VAR", self.ups])
            self.assertEqual(len(parts), 4)
            self.assertEqual(self.client.query("GET VAR " + self.ups + " " + parts[2]), row)
        self.assertTrue(self.client.query("GET DESC " + self.ups + " ups.mfr").startswith("DESC "))

    def denies_controls(self):
        # Unknown UPS/unsupported command also prevent physical execution if
        # a regression accidentally dispatches a protected handler.
        for cmd in ["FSD __missing_ups__", "INSTCMD __missing_ups__ __unsupported__",
                    "SET VAR __missing_ups__ ups.delay.shutdown 0", "LIST CLIENTS"]:
            with self.subTest(command=cmd):
                self.assertEqual(self.client.query(cmd), "ERR ACCESS-DENIED")

    def test_anonymous_reads_and_control_isolation(self):
        self.reads()
        self.denies_controls()
        self.assertEqual(self.client.query("GET VAR __missing_ups__ ups.status"), "ERR UNKNOWN-UPS")

    def test_existing_login_and_failed_reauthentication(self):
        if self.username is None:
            self.skipTest("Credentials not supplied")
        self.assertEqual(self.client.query("USERNAME " + self.username), "OK")
        self.assertEqual(self.client.query("PASSWORD " + self.password), "OK")
        self.assertEqual(self.client.query("LOGIN " + self.ups), "OK")
        self.reads()
        # Check dispatch through the control gate without controlling the UPS.
        self.assertEqual(self.client.query("INSTCMD __missing_ups__ __unsupported__"), "ERR UNKNOWN-UPS")
        self.assertEqual(self.client.query("SET VAR " + self.ups + " unsupported.variable 0"), "ERR CMD-NOT-SUPPORTED")
        self.assertEqual(self.client.query("USERNAME " + self.username), "OK")
        self.assertEqual(self.client.query("PASSWORD " + self.password + "__invalid__"), "ERR ACCESS-DENIED")
        self.denies_controls()
        self.reads()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=3493)
    parser.add_argument("--ups", required=True)
    parser.add_argument("--username")
    args = parser.parse_args()
    AccessTests.host, AccessTests.port, AccessTests.ups = args.host, args.port, args.ups
    AccessTests.username = args.username
    if args.username:
        AccessTests.password = getpass.getpass("NUT password: ")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AccessTests))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
