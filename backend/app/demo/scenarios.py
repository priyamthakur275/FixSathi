"""Labelled demo scenarios. Every response here is SCRIPTED sample content written by the FixSaathi team, never presented
as AI output. Demo sessions still go through the real server: safety gate, step locking, event logging and reports are
exactly the same code paths as live sessions."""
from pathlib import Path

DEMO_MODEL = 'demo-scenario'
HERE = Path(__file__).parent

SCENARIOS: dict[str, dict] = {
 'ceiling_fan_burn': {
  'title': 'Ceiling fan: burn marks around the hook', 'appliance': 'ceiling_fan', 'photo': 'ceiling_fan_burn.jpg',
  'issue': 'Ceiling fan was humming and running slow. Now there are burn marks on the ceiling around the hook.',
  'chat': [
   'DEMO SCENARIO (scripted sample, not live AI).\n\nThe photo shows soot and scorching on the ceiling around the fan hook and canopy. '
   'That pattern usually points to overheating or arcing at the ceiling junction: a loose or burnt connection, or a failed capacitor in the canopy.\n\n'
   'Before you touch anything, switch the fan circuit off at the MCB and check with your own tester that the line is dead. '
   'Record both statements in the safety panel. Because there is visible burn damage, a senior technician should inspect the wiring.',
   'DEMO SCENARIO (scripted sample, not live AI).\n\nOpen the repair workspace to see the ranked causes and the guided steps. '
   'Steps that need the power off stay locked by the server until both safety statements are recorded.'],
  'diagnosis': {'appliance_type': 'ceiling_fan', 'problem_summary': 'Burn marks at the ceiling junction: likely overheated or arcing connection',
   'possible_faults': [
    {'fault': 'Loose or burnt junction connection', 'explanation': 'Soot spreading from the hook point suggests arcing at the terminal block above the canopy.', 'confidence': 0.6,
     'evidence': [{'source': 'observed_in_image', 'detail': 'Soot and scorching radiating from the fan hook'}]},
    {'fault': 'Failed fan capacitor', 'explanation': 'A shorted capacitor inside the canopy can overheat and scorch nearby surfaces.', 'confidence': 0.25,
     'evidence': [{'source': 'technician_statement', 'detail': 'Fan was humming and running slow'}]},
    {'fault': 'Damaged supply wiring', 'explanation': 'Old insulation in the ceiling run can break down under load.', 'confidence': 0.15,
     'evidence': [{'source': 'ai_inference', 'detail': 'Common in older homes'}]}],
   'recommended_checks': ['Inspect the terminal block for blackened or loose wires', 'Check the capacitor for bulging or leakage', 'Have the ceiling supply insulation tested'],
   'follow_up_questions': ['Did the fan trip the MCB?', 'Is there a burning smell?'], 'safety_requirements': ['Switch off at the MCB', 'Verify dead with your own tester'],
   'requires_escalation': True},
  'guidance': {'steps': [
   {'title': 'Look without touching', 'instruction': 'From a safe distance, check for smoke, smell or sparking and note the burn pattern.', 'kind': 'observation', 'requires_power_off': False},
   {'title': 'Open the canopy', 'instruction': 'Lower the canopy cover to expose the terminal block and capacitor.', 'kind': 'power_sensitive', 'requires_power_off': True},
   {'title': 'Inspect the connections', 'instruction': 'Look for blackened, loose or melted wires at the terminal block. Do not re-energise.', 'kind': 'diagnostic_check', 'requires_power_off': True},
   {'title': 'Escalate if wiring is burnt', 'instruction': 'Leave the circuit off and hand over to a senior technician for rewiring.', 'kind': 'escalation', 'requires_power_off': False}]},
  'part_locator': {'found': True, 'component_name': 'Canopy and ceiling junction', 'explanation': 'Burn damage is centred on the fan hook and canopy area.',
   'box': {'x_min': 380, 'y_min': 330, 'x_max': 720, 'y_max': 640}, 'confidence': 0.5}},
 'split_ac_not_cooling': {
  'title': 'Split AC: running but not cooling', 'appliance': 'split_ac', 'photo': None,
  'issue': 'Split AC runs and the indoor fan blows, but the air is not cold.',
  'chat': [
   'DEMO SCENARIO (scripted sample, not live AI).\n\nCommon causes, in the order to check: clogged indoor filters, a dirty outdoor condenser, '
   'an outdoor fan or compressor that is not starting (often a failed capacitor), and low refrigerant from a leak.\n\n'
   'Start with what you can check safely: mode set to Cool, set temperature below room temperature, and the filters. '
   'Anything inside the outdoor unit needs the power off at the isolator, checked with your own tester. Refrigerant work needs a certified technician.',
   'DEMO SCENARIO (scripted sample, not live AI).\n\nOpen the repair workspace for the ranked causes and guided steps.'],
  'diagnosis': {'appliance_type': 'split_ac', 'problem_summary': 'Indoor unit runs but no cooling: airflow or outdoor-unit fault likely',
   'possible_faults': [
    {'fault': 'Clogged indoor filters', 'explanation': 'Blocked filters cut airflow over the cooling coil.', 'confidence': 0.35, 'evidence': [{'source': 'ai_inference', 'detail': 'Most common cause'}]},
    {'fault': 'Outdoor fan or compressor not starting', 'explanation': 'A failed start capacitor often stops the outdoor unit while the indoor fan still runs.', 'confidence': 0.35,
     'evidence': [{'source': 'technician_statement', 'detail': 'Indoor fan blows but air is not cold'}]},
    {'fault': 'Low refrigerant (leak)', 'explanation': 'A leak reduces cooling gradually; needs a certified technician.', 'confidence': 0.3, 'evidence': [{'source': 'ai_inference', 'detail': 'Check after airflow causes'}]}],
   'recommended_checks': ['Confirm Cool mode and set temperature', 'Clean or replace indoor filters', 'Check whether the outdoor fan spins'],
   'follow_up_questions': ['Is the outdoor unit humming or silent?', 'Is there ice on the pipes?'], 'safety_requirements': ['Isolate power before opening the outdoor unit'],
   'requires_escalation': False},
  'guidance': {'steps': [
   {'title': 'Check settings', 'instruction': 'Confirm the remote is on Cool mode and the set temperature is below room temperature.', 'kind': 'observation', 'requires_power_off': False},
   {'title': 'Check the outdoor fan', 'instruction': 'With the AC on, look from a safe distance: does the outdoor fan spin and is the unit humming?', 'kind': 'observation', 'requires_power_off': False},
   {'title': 'Clean the indoor filters', 'instruction': 'Switch the AC off at the isolator, remove the filters, wash with water and let them dry fully.', 'kind': 'safe_action', 'requires_power_off': True},
   {'title': 'Inspect the outdoor capacitor', 'instruction': 'Open the outdoor unit service panel and check the capacitor for bulging or leakage.', 'kind': 'power_sensitive', 'requires_power_off': True},
   {'title': 'Escalate refrigerant work', 'instruction': 'If airflow and capacitor are fine, hand over to a certified technician for a leak check.', 'kind': 'escalation', 'requires_power_off': False}]},
  'part_locator': {'found': False, 'component_name': None, 'explanation': 'No photo in this demo scenario.', 'box': None, 'confidence': 0.0}},
}


def public_list() -> list[dict]:
    return [{'id': k, 'title': v['title'], 'appliance': v['appliance'], 'issue': v['issue'], 'has_photo': bool(v['photo'])} for k, v in SCENARIOS.items()]
