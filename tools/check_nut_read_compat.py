"""Read-only NUT interoperability check; requires only the Python standard library."""
import argparse
import getpass
import shlex
import socket


def check(host, port, ups, username, password):
    with socket.create_connection((host, port), timeout=10) as sock:
        sock.settimeout(10)
        with sock.makefile("rb") as stream:
            def query(command):
                sock.sendall((command + "\n").encode("utf-8"))
                line = stream.readline()
                if not line:
                    raise RuntimeError("Server disconnected")
                return line.decode("utf-8").strip()

            def argument(value):
                if "\n" in value or "\r" in value:
                    raise ValueError("Protocol arguments must not contain newlines")
                return value

            for command in ["USERNAME " + argument(username), "PASSWORD " + argument(password)]:
                if query(command) != "OK":
                    raise RuntimeError("Authentication failed")
            ups_arg = argument(ups)
            if query("LIST VAR " + ups_arg) != "BEGIN LIST VAR " + ups:
                raise RuntimeError("LIST VAR failed")
            variables = []
            while True:
                raw = stream.readline()
                if not raw:
                    raise RuntimeError("Server disconnected during LIST VAR")
                line = raw.decode("utf-8").strip()
                if line == "END LIST VAR " + ups:
                    break
                parts = shlex.split(line)
                if len(parts) != 4 or parts[:2] != ["VAR", ups]:
                    raise RuntimeError("Malformed LIST VAR response")
                variables.append(parts[2])
            if not variables:
                raise RuntimeError("Server advertised no variables")
            for variable in variables:
                parts = shlex.split(query("GET DESC " + ups_arg + " " + argument(variable)))
                if len(parts) != 4 or parts[:3] != ["DESC", ups, variable]:
                    raise RuntimeError("Invalid description response for " + variable)
            missing = ups + "_missing"
            checks = [
                ("GET DESC " + argument(missing) + " ups.mfr", "ERR UNKNOWN-UPS"),
                ("GET DESC " + ups_arg + " unsupported.variable", "ERR VAR-NOT-SUPPORTED"),
                ("GET DESC " + ups_arg, "ERR INVALID-ARGUMENT"),
            ]
            for command, expected in checks:
                if query(command) != expected:
                    raise RuntimeError("Unexpected error response for " + command)
            for variable in ["battery.voltage", "battery.voltage.nominal"]:
                print(query("GET VAR " + ups_arg + " " + variable))
            print("PASS:", len(variables), "variable descriptions and 3 invalid requests")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=3493)
    parser.add_argument("--ups", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    check(args.host, args.port, args.ups, args.username, getpass.getpass("NUT password: "))


if __name__ == "__main__":
    main()
