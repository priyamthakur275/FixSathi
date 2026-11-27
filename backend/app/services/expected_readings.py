"""Informational nominal readings per appliance (reference values only, never instructions for live work)."""

DISCLAIMER = (
    'Reference values only — never instructions to work on or probe live circuits. '
    'Isolate at the MCB, discharge capacitors, and confirm dead with your own tester before touching any internal part.'
)

READINGS: list[dict] = [
    {
        'id': 'cf-cap',
        'appliance_type': 'ceiling_fan',
        'parameter': 'Run capacitor value',
        'hindi_name': 'रन कैपेसिटर (µF रेटिंग)',
        'expected_range': '2.0 µF – 2.5 µF (within ±5% of label rating)',
        'out_of_range_meaning': 'Below 1.5 µF causes weak starting torque, slow speed, and humming.',
        'condition': 'isolated_and_discharged',
    },
    {
        'id': 'cf-winding',
        'appliance_type': 'ceiling_fan',
        'parameter': 'Stator winding resistance',
        'hindi_name': 'वाइंडिंग रेजिस्टेंस (ओम)',
        'expected_range': '150 Ω – 300 Ω per coil pair; infinity (OL) between winding and body',
        'out_of_range_meaning': 'OL or 0 Ω indicates burnt or shorted winding; low ohms to body means insulation fault.',
        'condition': 'isolated_and_discharged',
    },
    {
        'id': 'ac-thermistor',
        'appliance_type': 'split_ac',
        'parameter': 'Room / coil NTC thermistor at 25 °C',
        'hindi_name': 'रूम / कॉइल सेंसर (NTC)',
        'expected_range': '5 kΩ – 10 kΩ nominal at 25 °C (varies smoothly when warmed)',
        'out_of_range_meaning': 'Infinite resistance or stuck reading triggers sensor error codes and short-cycling.',
        'condition': 'isolated_and_discharged',
    },
    {
        'id': 'ac-airflow',
        'appliance_type': 'split_ac',
        'parameter': 'Supply vs return air temperature drop',
        'hindi_name': 'कूलिंग ग्रिल तापमान अंतर',
        'expected_range': '8 °C – 12 °C drop across clean indoor coil during steady cooling',
        'out_of_range_meaning': 'Small drop points to blocked filter, low airflow, or refrigerant/compressor fault.',
        'condition': 'visual_or_non_contact',
    },
    {
        'id': 'wm-inlet-valve',
        'appliance_type': 'washing_machine',
        'parameter': 'Water inlet solenoid coil resistance',
        'hindi_name': 'इनलेट वाल्व कॉइल',
        'expected_range': '1.0 kΩ – 4.5 kΩ (unplugged at coil terminals)',
        'out_of_range_meaning': 'Infinite resistance (OL) explains no water entry; clean inlet mesh if coil is within range.',
        'condition': 'isolated_and_discharged',
    },
    {
        'id': 'wm-drain-pump',
        'appliance_type': 'washing_machine',
        'parameter': 'Drain pump motor winding resistance',
        'hindi_name': 'ड्रेन पंप मोटर',
        'expected_range': '120 Ω – 280 Ω across isolated motor terminals',
        'out_of_range_meaning': 'Infinite resistance indicates broken coil; seized impeller often stalls a healthy coil.',
        'condition': 'isolated_and_discharged',
    },
    {
        'id': 'rf-defrost-heater',
        'appliance_type': 'refrigerator',
        'parameter': 'Defrost heater & bimetal resistance',
        'hindi_name': 'डीफ्रॉस्ट हीटर और बाईमेटल',
        'expected_range': '250 Ω – 450 Ω on heater; bimetal shows near 0 Ω while frosted',
        'out_of_range_meaning': 'Broken heater element (OL) or failed bimetal causes heavy ice build-up blocking evaporator airflow.',
        'condition': 'isolated_and_discharged',
    },
    {
        'id': 'wp-tds',
        'appliance_type': 'water_purifier',
        'parameter': 'Treated water TDS & storage shut-off',
        'hindi_name': 'टीडीएस (TDS) और टैंक कट-ऑफ',
        'expected_range': 'TDS reduction ≥ 80% vs feed water (taste/drinking target per site water)',
        'out_of_range_meaning': 'Rising TDS signals exhausted RO membrane or damaged O-ring seal.',
        'condition': 'visual_or_non_contact',
    },
    {
        'id': 'mcb-earth',
        'appliance_type': 'mcb_electrical',
        'parameter': 'Earth-fault / dead-circuit verification check',
        'hindi_name': 'अर्थिंग और आइसोलेशन जाँच',
        'expected_range': '0 V verified between phase, neutral, and earth on isolated circuit',
        'out_of_range_meaning': 'Any voltage means upstream supply is still live — stop and re-check upstream MCB.',
        'condition': 'isolated_and_discharged',
    },
    {
        'id': 'solar-isolator',
        'appliance_type': 'rooftop_solar',
        'parameter': 'Array irradiance / inverter fault LED',
        'hindi_name': 'सोलर इन्वर्टर इंडिकेटर और DC आइसोलेटर',
        'expected_range': 'Inverter fault LED code noted before switching DC isolator off',
        'out_of_range_meaning': 'PV strings stay energised in daylight even when AC mains is off; escalate DC wiring faults.',
        'condition': 'visual_or_non_contact',
    },
    {
        'id': 'mw-escalate',
        'appliance_type': 'microwave_oven',
        'parameter': 'High-voltage internal readings',
        'hindi_name': 'माइक्रोवेव आंतरिक जाँच',
        'expected_range': 'Sealed cabinet — do not open in the field',
        'out_of_range_meaning': 'High-voltage capacitor retains lethal charge even unplugged; hand over internal faults to authorised service.',
        'condition': 'authorised_service_only',
    },
]


def for_appliance(appliance_type: str | None = None) -> dict:
    app = (appliance_type or '').strip().lower()
    items = [r for r in READINGS if r['appliance_type'] == app] if app and app != 'unknown' else list(READINGS)
    return {'appliance_type': app or 'all', 'disclaimer': DISCLAIMER, 'items': items}
