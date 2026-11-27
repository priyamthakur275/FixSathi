"""Fault finder: instant record lookup without the AI, with power-sensitive steps still locked."""
from tests.test_dataset_pipeline import _ingest, rec


def test_lookup_by_error_code_returns_the_record_without_calling_gemini(client, tech):
    _ingest(rec(record_id='t:lgch38', appliance_category='split_ac', appliance_brand='LG', error_code='CH38', reported_symptoms=['CH38 shown', 'poor cooling'],
                possible_faults=['Low refrigerant'], diagnostic_procedure=['Check the indoor filter', 'Open the outdoor unit cover and test the capacitor']))
    r = client.get('/api/v1/lookup?q=LG CH38', headers=tech['h'])
    assert r.status_code == 200
    d = r.json()
    top = d['results'][0]
    assert top['record_id'] == 't:lgch38' and top['match'] == 'error_code' and d['error_codes_found'] == ['CH38']
    assert top['title'] == 'LG split ac: code CH38' and top['appliance_label'] == 'Split AC'
    assert top['steps'][0] == {'text': 'Check the indoor filter', 'locked': False}
    assert top['steps'][1] == {'text': None, 'locked': True}  # the server never sends power work outside a session
    assert top['locked_steps'] == 1


def test_lookup_reports_codes_it_has_no_record_for(client, tech):
    d = client.get('/api/v1/lookup?q=Whirlpool ZZ9&appliance_type=washing_machine', headers=tech['h']).json()
    assert 'ZZ9' in d['error_codes_unknown']


def test_lookup_needs_sign_in(client):
    assert client.get('/api/v1/lookup?q=CH38').status_code == 401


def test_repeated_knowledge_lookup_uses_cache_and_ingest_invalidates_it(client, tech):
    from app.services import knowledge_base as kb

    _ingest(rec(record_id='t:cache1', appliance_category='split_ac', appliance_brand='LG', error_code='CH38',
                reported_symptoms=['CH38 shown'], possible_faults=['Low refrigerant']))
    before = kb.cache_stats()
    assert before == {'hits': 0, 'misses': 0}

    r1 = client.get('/api/v1/lookup?q=LG CH38', headers=tech['h'])
    assert r1.status_code == 200
    assert kb.cache_stats() == {'hits': 0, 'misses': 1}

    r2 = client.get('/api/v1/lookup?q=LG CH38', headers=tech['h'])
    assert r2.status_code == 200
    assert r2.json() == r1.json()
    assert kb.cache_stats() == {'hits': 1, 'misses': 1}

    # Ingesting new records must invalidate the cache so newly added records appear immediately.
    _ingest(rec(record_id='t:cache2', appliance_category='washing_machine', appliance_brand='Bosch', error_code='E18',
                reported_symptoms=['E18 drain error'], possible_faults=['Blocked drain pump filter']))
    assert kb.cache_stats() == {'hits': 0, 'misses': 0}

    r3 = client.get('/api/v1/lookup?q=Bosch E18', headers=tech['h'])
    assert r3.status_code == 200
    assert r3.json()['results'][0]['record_id'] == 't:cache2'
    assert kb.cache_stats() == {'hits': 0, 'misses': 1}
