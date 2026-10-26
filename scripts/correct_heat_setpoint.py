"""Resolve explicitly stated setpoint +/- tolerance, without imputing a range."""
import json
from collect_grain_size import key, save_json
from expand_heat_treatment_data import OUT

doi='10.1039/d5ra08480f'
p=OUT/'extractions'/f'{key(doi)}.json'
d=json.loads(p.read_text(encoding='utf-8'))
before=OUT/'manual_corrections'/p.name
if not before.exists():save_json(before,d)
for r in d['records']:
    for a in r['attributes']:
        if a['field']=='heat_treatment_temperature_C':
            assert a['quote']=='final tempering at (482 ± 3) °C for 6 h with air cooling.' and a['quote_verified']
            a.update(value=482,basis='reported',manual_correction_note='482 C is the explicitly stated nominal furnace setpoint; +/-3 C is its tolerance, not an unreported uniform range. Bounds retained as tolerance.')
save_json(p,d)
review=OUT/'reviews'/p.name
if review.exists():review.unlink()
print('Corrected five source-explicit 482 C setpoints; independent review pending.')
