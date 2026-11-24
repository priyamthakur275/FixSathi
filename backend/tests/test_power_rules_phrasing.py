"""Phrasings found by the offline safety evaluation (scripts/evaluate.py)."""
from app.core.power_rules import instructs_power_work


def test_take_part_out_is_withheld():
    for t in ('Take the regulator out of the switchboard and test it.', 'Take the PCB out.', 'Take out the capacitor.', 'Take it apart.'):
        assert instructs_power_work(t), t


def test_everyday_take_out_stays_readable():
    for t in ('Take the plug out of the socket.', 'Take the food out and stir it.', 'Take the filter out and wash it.'):
        assert not instructs_power_work(t), t


def test_live_voltage_checks_are_withheld():
    for t in ('Check the voltage across the compressor terminals.', 'Test the voltage between the two wires.'):
        assert instructs_power_work(t), t
    assert not instructs_power_work('Never check the voltage across the terminals with bare hands.')
