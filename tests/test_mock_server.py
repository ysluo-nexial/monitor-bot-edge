# SPDX-License-Identifier: AGPL-3.0-or-later
from scripts.mock_license_server import LicenseStore

def test_same_machine_ok_other_machine_409():
    store = LicenseStore()
    code, body = store.activate("k", "m1")
    assert code == 200 and body["license_token"]
    code, body = store.activate("k", "m1")
    assert code == 200
    code, body = store.activate("k", "m2")
    assert code == 409
