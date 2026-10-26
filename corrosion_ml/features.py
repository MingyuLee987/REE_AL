"""Outcome-blind corrosion descriptors; unknown concentrations remain missing."""
import re
import unicodedata
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator,TransformerMixin
from .composition import NUMERIC,CATEGORICAL

FEATURE_SETS=['environment']
COMPOUNDS=['nacl','hcl','h2so4','naoh','koh','na2so4','cacl2','mgso4']
MOLAR_MASS={'nacl':58.44,'hcl':36.46,'h2so4':98.079,'naoh':40.,'koh':56.11}
UNIT=r'(wt\.?\s*%|wtpct|pct|%|mmol\s*[/ ]?\s*l|mol\s*[/ ]?\s*l|mm\b|m\b|g\s*[/ ]?\s*l)'
NUMBER=r'(\d+(?:\.\d+)?)'


def parse_medium(value):
    text='' if pd.isna(value) else unicodedata.normalize('NFKC',str(value)).lower()
    text=text.replace('_',' ').replace('\u200b','').replace('(oh)','oh')
    compact=text.replace(' ','')
    first_compound=re.search(r'\b(?:'+ '|'.join(COMPOUNDS) +r')\b',text)
    first_concentration=re.search(NUMBER+r'\s*'+UNIT,text)
    prefix_layout=bool(first_compound and first_concentration and first_concentration.start()<first_compound.start())
    if 'pore' in text or 'caoh2' in compact or '포화' in text:family='pore_solution'
    elif 'seawater' in text or '해수' in text:family='seawater'
    elif 'soil' in text:family='soil_solution'
    elif 'hanks' in text:family='hanks'
    elif 'saliva' in text:family='artificial_saliva'
    elif 'h2so4' in text:family='sulfuric_acid'
    elif 'hcl' in text:family='hydrochloric_acid'
    elif 'koh' in text or 'naoh' in text:family='alkaline_solution'
    elif 'nacl' in text:family='chloride_solution'
    elif 'nahso3' in text:family='bisulfite_solution'
    elif 'na2so4' in text:family='sulfate_solution'
    else:family='unreported'
    result={'medium_family':family,'nacl_percent_basis':'unreported',
            'medium_co2_saturated':float('co2' in text and 'saturat' in text),
            'medium_deaerated':float('탈기' in text or 'deaerat' in text or 'nitrogen' in text),
            'medium_concentration_conflict':float('conflict' in text)}
    for compound in COMPOUNDS:
        result[compound+'_mol_L']=np.nan
        result[compound+'_g_L']=np.nan
    result['nacl_percent_reported']=np.nan
    for compound in COMPOUNDS:
        post=re.search(r'\b'+compound+r'\s*'+NUMBER+r'\s*'+UNIT,text)
        pre=re.search(NUMBER+r'\s*'+UNIT+r'\s*'+compound+r'\b',text)
        # Mixed strings use a consistent recipe layout. Choosing a posterior
        # value in a prefix recipe would attach the next salt's concentration.
        match=(pre or post) if prefix_layout else (post or pre)
        if not match:continue
        val=float(match[1]);unit=re.sub(r'\s+','',match[2])
        if compound=='nacl' and ('%' in unit or 'pct' in unit):
            result['nacl_percent_reported']=val
            result['nacl_percent_basis']='mass_percent' if unit.startswith('wt') else 'unspecified_percent'
        elif unit.startswith('mm'):
            result[compound+'_mol_L']=val/1000
        elif unit.startswith('mol') or unit=='m':
            result[compound+'_mol_L']=val
        elif unit.startswith('g'):
            result[compound+'_g_L']=val
            if compound in MOLAR_MASS:result[compound+'_mol_L']=val/MOLAR_MASS[compound]
    # Only explicitly quantified components; not total seawater ion concentration.
    chloride=[result[c+'_mol_L']*factor for c,factor in [('nacl',1),('hcl',1),('cacl2',2)] if pd.notna(result[c+'_mol_L'])]
    sulfate=[result[c+'_mol_L'] for c in ['h2so4','na2so4','mgso4'] if pd.notna(result[c+'_mol_L'])]
    hydroxide=[result[c+'_mol_L'] for c in ['naoh','koh'] if pd.notna(result[c+'_mol_L'])]
    result['quantified_chloride_mol_L']=sum(chloride) if chloride else np.nan
    result['quantified_sulfate_mol_L']=sum(sulfate) if sulfate else np.nan
    result['added_strong_base_mol_L']=sum(hydroxide) if hydroxide else np.nan
    if 'no added chloride' in text or '0cl' in compact:result['quantified_chloride_mol_L']=0.
    # Never infer chloride concentration from seawater/Hanks/saliva names.
    return result


class CorrosionFeatures(BaseEstimator,TransformerMixin):
    def __init__(self,feature_set='environment'):
        self.feature_set=feature_set

    def fit(self,X,y=None):
        if self.feature_set not in FEATURE_SETS:raise ValueError('Unknown feature set')
        return self

    def transform(self,X):
        result=X[NUMERIC+CATEGORICAL].copy()
        medium=pd.DataFrame([parse_medium(v) for v in X.electrolyte_condition_cat],index=X.index)
        result=result.drop(columns=['electrolyte_condition_cat']).join(medium)
        result['RE_element_cat']=result.RE_element_cat.map(lambda s:'+'.join(sorted(str(s).split('+'))))
        result['temperature_K']=X.temperature_C+273.15
        result['inverse_temperature_1000_K']=1000/result.temperature_K.where(result.temperature_K>0)
        result['pH_value_or_bound']=X.pH.combine_first(X.pH_lower_bound)
        result['pH_uses_lower_bound']=(X.pH.isna()&X.pH_lower_bound.notna()).astype(float)
        for c in ['exposure_h','ocp_stabilization_min','heat_treatment_time_min','scan_rate_mV_s']:
            result['log1p_'+c]=np.log1p(X[c].where(X[c]>=0))
        for c in ['quantified_chloride_mol_L','quantified_sulfate_mol_L','added_strong_base_mol_L','nacl_percent_reported']:
            result['log1p_'+c]=np.log1p(medium[c].where(medium[c]>=0))
        result['time_inverse_temperature']=result.log1p_exposure_h*result.inverse_temperature_1000_K
        cats=[c for c in CATEGORICAL if c!='electrolyte_condition_cat']+['medium_family','nacl_percent_basis']
        for c in cats:result[c]=result[c].fillna('missing').astype(str)
        numeric=[c for c in result if c not in cats]
        result[numeric]=result[numeric].replace([np.inf,-np.inf],np.nan)
        return result
