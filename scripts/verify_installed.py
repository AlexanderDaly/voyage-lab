"""Run with an isolated installed wheel: python -I scripts/verify_installed.py EXPORT.json."""

import socket
import sys
from pathlib import Path

import voyage_lab
from voyage_lab.cli import main
from voyage_lab.fixtures import default_scenario


def no_network(*_args, **_kwargs):
    raise AssertionError("Offline verification attempted network access")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network
socket.getaddrinfo = no_network
assert "site-packages" in str(Path(voyage_lab.__file__)), "Expected an installed wheel, not source imports"
assert default_scenario().environment.kind == "synthetic", "Installed fixture assets missing"
sys.argv = ["voyage-lab", "replay", sys.argv[1]]
main()
print("Installed package and embedded replay passed with network functions blocked.")
