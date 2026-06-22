# Copyright (C) 2026  Vates SAS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
import ipaddress
import pathlib
import ssl

import pytest

from xcp_storage.typing import (
    Final,
    NamedTuple,
    Optional,
)

# ==============================================================================

TLS_SERVER_CERTIFICATE_NAME: Final = "server.crt"
TLS_SERVER_KEY_NAME: Final = "server.key"

class TlsContexts(NamedTuple):
    server: ssl.SSLContext
    client: ssl.SSLContext

@pytest.fixture
def tls_contexts(tmp_path: pathlib.Path) -> TlsContexts:
    """
    Server/client TLS contexts built around a throwaway self-signed certificate,
    valid for `127.0.0.1` only.
    """

    pytest.importorskip("cryptography")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = datetime.timedelta(days=1)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - delta)
        .not_valid_after(now + delta)
        .add_extension(x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.ip_address("127.0.0.1"))
        ]), critical=False)
        .sign(key, hashes.SHA256())
    )

    cert_path = tmp_path / TLS_SERVER_CERTIFICATE_NAME
    key_path = tmp_path / TLS_SERVER_KEY_NAME
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    ))

    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(str(cert_path), str(key_path))
    client_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client_context.load_verify_locations(str(cert_path))
    return TlsContexts(server_context, client_context)

@pytest.fixture
def ssl_contexts(request: pytest.FixtureRequest) -> Optional[TlsContexts]:
    """
    `None` by default (plain TCP). Parametrize it indirectly with `True` (see `over_plain_and_tls`)
    to run a test over TLS; `cryptography` is then required.
    """

    if getattr(request, "param", False):
        return request.getfixturevalue("tls_contexts")
    return None

@pytest.fixture
def client_ssl_context(ssl_contexts: Optional[TlsContexts]) -> Optional[ssl.SSLContext]:
    return ssl_contexts.client if ssl_contexts else None

# Run a test twice: over plain TCP then over TLS.
over_plain_and_tls = pytest.mark.parametrize("ssl_contexts", [False, True], indirect=True, ids=["plain", "tls"])
