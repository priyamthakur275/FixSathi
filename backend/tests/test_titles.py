from app.services.sessions import _title_from


def test_title_uses_first_sentence_and_never_cuts_mid_word():
    t = _title_from('Ceiling fan was humming and slow, now there are burn marks on the ceiling. What should I inspect?')
    assert t.endswith('...') and len(t) <= 63 and 'What' not in t and not t[:-3].endswith(' ')
    assert _title_from("My split AC is running, but it isn't cooling properly.") == "My split AC is running, but it isn't cooling properly"
    assert _title_from('   ') == ''
