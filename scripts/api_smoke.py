#!/usr/bin/env python3
"""Exercise the running application through real HTTP APIs."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
import uuid

BASE_URL = "http://127.0.0.1:8000"


def request(
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode())
        return exc.code, payload


def expect(status: int, expected: int, payload: dict, label: str) -> None:
    if status != expected:
        raise AssertionError(f"{label}: expected HTTP {expected}, got {status}: {payload}")


def main() -> int:
    username = f"ci-{uuid.uuid4().hex[:12]}"
    password = "ci-password-123"

    status, registered = request(
        "POST",
        "/auth/register",
        {"username": username, "password": password, "role": "viewer"},
    )
    expect(status, 201, registered, "register")
    assert registered["access_token"]

    status, logged_in = request(
        "POST",
        "/auth/token",
        {"username": username, "password": password},
    )
    expect(status, 200, logged_in, "login")
    access_token = logged_in["access_token"]
    refresh_token = logged_in["refresh_token"]

    status, refreshed = request(
        "POST",
        "/auth/refresh",
        {"refresh_token": refresh_token},
    )
    expect(status, 200, refreshed, "refresh")
    assert refreshed["access_token"]

    status, api_key = request(
        "POST",
        "/auth/api-keys",
        {"label": "ci-smoke"},
        token=access_token,
    )
    expect(status, 201, api_key, "create api key")
    assert api_key["secret"]

    client_order_id = f"ci-{uuid.uuid4().hex}"
    order = {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": "0.001",
        "price": "50000",
        "client_order_id": client_order_id,
        "equity": "100000",
    }

    status, first_order = request("POST", "/trading/orders/paper", order)
    expect(status, 201, first_order, "paper order")
    assert first_order["status"] == "filled"
    assert first_order["executed_price"] == "50000.00000000"

    status, duplicate_order = request("POST", "/trading/orders/paper", order)
    expect(status, 201, duplicate_order, "idempotent paper order")
    assert duplicate_order["id"] == first_order["id"]

    print("API smoke passed: register, login, refresh, API key, paper order, idempotency")
    return 0


if __name__ == "__main__":
    sys.exit(main())
