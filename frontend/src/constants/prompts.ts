import type { Key } from '../i18n'

/** Quick-start prompts shown on the welcome screen. These are suggestions, not data. The label is translated; the prompt sent stays English,
 *  because the server already answers in the technician's language. */
export const suggestions: { key: Key; prompt: string; appliance: string }[] = [
  { key: 'sug.ac', prompt: "My split AC is running, but it isn't cooling properly.", appliance: 'split_ac' },
  { key: 'sug.fan', prompt: 'My ceiling fan is slow and hums but does not spin fully.', appliance: 'ceiling_fan' },
  { key: 'sug.wm', prompt: 'My washing machine is making a loud noise during spinning.', appliance: 'washing_machine' },
  { key: 'sug.part', prompt: 'Help me identify this component.', appliance: 'mcb_electrical' },
]

/** The appliance categories the backend and knowledge base support. */
export const appliances = [
  { id: 'split_ac', label: 'Split AC' },
  { id: 'washing_machine', label: 'Washing machine' },
  { id: 'refrigerator', label: 'Refrigerator' },
  { id: 'ceiling_fan', label: 'Ceiling fan' },
  { id: 'microwave_oven', label: 'Microwave' },
  { id: 'water_purifier', label: 'Water purifier' },
  { id: 'mcb_electrical', label: 'MCB / wiring' },
  { id: 'rooftop_solar', label: 'Rooftop solar' },
] as const
