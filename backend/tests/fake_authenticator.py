"""Minimal software passkey (ES256, 'none' attestation) that behaves like a browser + authenticator."""
import hashlib
import json
import os
import struct

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import bytes_to_base64url


class FakeAuthenticator:
    def __init__(self, origin: str, rp_id: str):
        self.origin, self.rp_id = origin, rp_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.cred_id = os.urandom(16)
        self.sign_count = 0
        self.user_handle = None

    def _client_data(self, kind: str, challenge: str) -> bytes:
        return json.dumps({"type": kind, "challenge": challenge, "origin": self.origin, "crossOrigin": False}).encode()

    def _auth_data(self, flags: int, extra: bytes = b"") -> bytes:
        return hashlib.sha256(self.rp_id.encode()).digest() + bytes([flags]) + struct.pack(">I", self.sign_count) + extra

    def create(self, options: dict) -> dict:
        """navigator.credentials.create() → RegistrationResponseJSON."""
        self.user_handle = options["user"]["id"]
        nums = self.key.public_key().public_numbers()
        cose = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: nums.x.to_bytes(32, "big"), -3: nums.y.to_bytes(32, "big")})
        attested = b"\0" * 16 + struct.pack(">H", len(self.cred_id)) + self.cred_id + cose
        auth_data = self._auth_data(0x45, attested)  # UP | UV | AT
        att_obj = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        cid = bytes_to_base64url(self.cred_id)
        return {"id": cid, "rawId": cid, "type": "public-key", "response": {
            "clientDataJSON": bytes_to_base64url(self._client_data("webauthn.create", options["challenge"])),
            "attestationObject": bytes_to_base64url(att_obj), "transports": ["internal"]}}

    def get(self, options: dict) -> dict:
        """navigator.credentials.get() → AuthenticationResponseJSON."""
        self.sign_count += 1
        auth_data = self._auth_data(0x05)  # UP | UV
        client_data = self._client_data("webauthn.get", options["challenge"])
        sig = self.key.sign(auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256()))
        cid = bytes_to_base64url(self.cred_id)
        return {"id": cid, "rawId": cid, "type": "public-key", "response": {
            "clientDataJSON": bytes_to_base64url(client_data), "authenticatorData": bytes_to_base64url(auth_data),
            "signature": bytes_to_base64url(sig), "userHandle": self.user_handle}}
