"""Unified FixSaathi repair-record schema. Every imported record, whatever its source, is normalised into this shape.
Unknown values stay None / empty. Nothing is inferred to fill a gap."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

# Primary FixSaathi categories plus related ones imported from sources. Extend freely; nothing else is hard-coded to this list.
CATEGORIES = {
    'washing_machine', 'refrigerator', 'split_ac', 'ceiling_fan', 'mcb_electrical', 'rooftop_solar',
    'dryer', 'dishwasher', 'oven_range', 'aircon_dehumidifier', 'fan_other', 'microwave_oven', 'water_purifier',
}
# Categories retrieval may fall back to (labelled as related) when the primary one has little data.
RELATED = {'split_ac': ['aircon_dehumidifier'], 'ceiling_fan': ['fan_other']}

VerificationStatus = Literal['verified_source', 'technician_reviewed', 'unverified', 'synthetic_demo']
VERIFICATION_MEANING = {
    'verified_source': 'Taken from manufacturer documentation on the manufacturer\'s own site, or the upstream dataset states it was derived from an official manufacturer listing. Not re-verified by FixSaathi.',
    'technician_reviewed': 'Reviewed by a named field technician for FixSaathi.',
    'unverified': 'Imported from a secondary or community source, or authored by the FixSaathi team, and not reviewed by a technician.',
    'synthetic_demo': 'Made-up demonstration record. Never real repair history. Excluded from retrieval unless explicitly enabled.',
}


class Part(BaseModel):
    name: str
    part_number: str | None = None


class RepairRecord(BaseModel):
    record_id: str = Field(min_length=3, max_length=120)
    appliance_category: str
    appliance_brand: str | None = None
    appliance_model: str | None = None
    model_year: int | None = Field(default=None, ge=1950, le=2100)
    market: str | None = None
    error_code: str | None = None
    error_code_original: str | None = None
    reported_symptoms: list[str] = Field(default_factory=list)
    observed_conditions: list[str] = Field(default_factory=list)
    possible_faults: list[str] = Field(default_factory=list)
    suspected_components: list[str] = Field(default_factory=list)
    diagnostic_questions: list[str] = Field(default_factory=list)
    diagnostic_procedure: list[str] = Field(default_factory=list)
    recommended_repair: str | None = None
    repair_steps: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_parts: list[Part] = Field(default_factory=list)
    safety_requirements: list[str] = Field(default_factory=list, description='As stated by the source only')
    fixsaathi_safety_policy: list[str] = Field(default_factory=list, description='Added by FixSaathi policy, kept separate from source text')
    requires_power_off: bool = False
    severity: Literal['informational', 'degraded', 'stop_failure', 'hazardous'] | None = None
    repair_difficulty: Literal['diy', 'intermediate', 'professional'] | None = None
    estimated_repair_duration_minutes: int | None = Field(default=None, ge=1, le=10000)
    repair_outcome: Literal['fixed', 'repairable', 'end_of_life', 'unknown'] | None = None
    source_name: str = Field(min_length=2)
    source_url: str | None = None
    source_license: str = Field(min_length=2)
    source_record_id: str = Field(min_length=1)
    verification_status: VerificationStatus
    last_updated: date
    provenance: dict = Field(default_factory=dict)

    @field_validator('appliance_category')
    @classmethod
    def _cat(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f'unknown appliance_category {v!r}')
        return v

    @model_validator(mode='after')
    def _rules(self):
        if not (self.reported_symptoms or self.possible_faults or self.error_code or self.repair_steps):
            raise ValueError('record has no symptom, fault, error code or repair step')
        synthetic_name = 'SYNTHETIC' in self.source_name.upper()
        if (self.verification_status == 'synthetic_demo') != synthetic_name:
            raise ValueError('synthetic records must be labelled SYNTHETIC in source_name and use verification_status synthetic_demo, and only they may')
        if self.verification_status != 'synthetic_demo' and not self.source_url and not self.provenance.get('authored_by'):
            raise ValueError('non-synthetic record needs a source_url or provenance.authored_by')
        return self

    def search_text(self) -> str:
        parts = [self.appliance_category.replace('_', ' '), self.appliance_brand, self.appliance_model, self.error_code, self.error_code_original if self.error_code_original != self.error_code else None, *self.reported_symptoms,
                 *self.observed_conditions, *self.possible_faults, *self.suspected_components, self.recommended_repair or '', *self.repair_steps]
        return ' | '.join(p for p in parts if p)
