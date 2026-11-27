"""Informational expected-readings reference cards: never live-work guidance."""
from app.core.power_rules import instructs_power_work
from app.services.expected_readings import DISCLAIMER, READINGS


def test_expected_readings_require_auth_and_filter_by_appliance(client, tech):
    assert client.get('/api/v1/expected-readings').status_code == 401

    all_r = client.get('/api/v1/expected-readings', headers=tech['h'])
    assert all_r.status_code == 200
    assert all_r.json()['disclaimer'] == DISCLAIMER
    assert len(all_r.json()['items']) == len(READINGS)

    fan_r = client.get('/api/v1/expected-readings?appliance_type=ceiling_fan', headers=tech['h']).json()
    assert fan_r['appliance_type'] == 'ceiling_fan'
    assert fan_r['items'] and all(x['appliance_type'] == 'ceiling_fan' for x in fan_r['items'])

    mw_r = client.get('/api/v1/expected-readings?appliance_type=microwave_oven', headers=tech['h']).json()
    assert mw_r['items'][0]['condition'] == 'authorised_service_only'


def test_expected_readings_contain_no_live_work_instructions():
    assert 'never instructions to work on or probe live circuits' in DISCLAIMER.lower()
    for card in READINGS:
        for field in ('parameter', 'hindi_name', 'expected_range', 'out_of_range_meaning'):
            text = card[field]
            assert not instructs_power_work(text), f'Card {card["id"]}.{field} triggered instructs_power_work: {text!r}'
            assert 'while live' not in text.lower() and 'with power on' not in text.lower()
