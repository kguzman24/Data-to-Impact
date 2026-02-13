#same setup as visualizations.py 

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path
import numpy as np

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

# Paths
DATA_PATH = Path("../data/va_data_centers.json")
OUTPUT_PATH = Path("../outputs/figures")
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

#print("Loading Virginia data centers...")
with open(DATA_PATH, 'r') as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data)

# Create commonly used columns early
df['power_numeric'] = pd.to_numeric(
    df['estimate power consumption in kw/hr (calculated 50%)'].astype(str).str.replace(',', '').str.replace(' ', ''),
    errors='coerce'
)
df['pop_numeric'] = pd.to_numeric(
    df['total population within 1 mile of site'],
    errors='coerce'
)
df['size_category'] = df['size category at 50% capacity'].fillna('Unknown')


def calculate_disclosure_score(row):
    score = 0
    max_score = 4
    
    if row['annual water consumption (gallons)'] not in ['-', '', None]:
        score += 1
    if row['daily water consumption (gallons)'] not in ['-', '', None]:
        score += 1
    if row['estimate power consumption in kw/hr (calculated 50%)'] not in ['-', '', None]:
        score += 1
    if row['total population within 1 mile of site'] not in ['-', '', None]:
        score += 1
    
    return (score / max_score) * 100

df['disclosure_score'] = df.apply(calculate_disclosure_score, axis=1)

def calculate_exemption_eligibility(row):
    score = 0
    max_score = 100
    reasons = []
    
    renewable_pct = 0
    score += (renewable_pct / 100) * 15
    if renewable_pct < 40:
        reasons.append(f"Low renewable energy ({renewable_pct}%)")
    
    water_stress = row['water stress']
    water_data = row['annual water consumption (gallons)']
    if water_stress in ['Low (<10%)', 'Low - Medium (10-20%)']:
        score += 8
    elif water_stress in ['Medium - High (20-40%)'] and water_data not in ['-', '', None]:
        score += 5
        reasons.append("Medium-high water stress with data")
    elif water_stress in ['High (40-80%)', 'Extremely High (>80%)']:
        score += 0
        reasons.append(f"High water stress ({water_stress})")
    else:
        score += 3
    
    nox = row['nox tpy']
    pm25 = row['pm2.5 tpy']
    co2e = row['co2e tpy']
    
    emissions_disclosed = sum([
        nox not in ['-', '', None],
        pm25 not in ['-', '', None],
        co2e not in ['-', '', None]
    ])
    score += (emissions_disclosed / 3) * 15
    
    if emissions_disclosed < 2:
        reasons.append(f"Missing emissions data ({3-emissions_disclosed} fields)")
    
    pop = row['total population within 1 mile of site']
    if pd.notna(pop) and pop != '-':
        pop_num = float(pop) if isinstance(pop, (int, float)) else 0
        if pop_num < 1000:
            score += 10
        elif pop_num < 5000:
            score += 5
            reasons.append(f"Population exposure: {pop_num:.0f} residents")
        else:
            score += 0
            reasons.append(f"High population exposure: {pop_num:.0f} residents")
    else:
        score += 3
    
    ej_state = row['state environmental justice concern']
    ej_us = row['us environmental justice concern']
    if ej_state == 'no' and ej_us == 'no':
        score += 10
    else:
        score += 0
        reasons.append("Environmental justice concerns flagged")
    
    score += 5
    
    power = row['power_numeric']
    if pd.notna(power):
        if power < 50000:
            score += 5
        elif power < 100000:
            score += 3
        else:
            score += 0
            reasons.append(f"High power demand ({power/1000:.0f} MW)")
    else:
        score += 2
    
    disclosure = row['disclosure_score']
    score += (disclosure / 100) * 25
    
    if disclosure < 50:
        reasons.append(f"Low disclosure score ({disclosure:.0f}%)")
    
    if score >= 80:
        tier = "Full Exemption (100%)"
    elif score >= 60:
        tier = "Partial Exemption (50%)"
    else:
        tier = "No Exemption (0%)"
    
    return score, tier, reasons


def print_detailed_breakdown(row, idx):
    """Print a detailed scoring breakdown for a single facility"""
    
    facility_name = row.get('name', 'Unknown Facility')
    county = row.get('county', 'Unknown County')
    
    print(f"\n{'='*80}")
    print(f"FACILITY #{idx}: {facility_name} - {county}")
    print(f"{'='*80}")
    
    # Initialize score tracking
    score_breakdown = {}
    total = 0
    
    # 1. RENEWABLE ENERGY (15 pts)
    renewable_pct = 0
    renewable_score = (renewable_pct / 100) * 15
    total += renewable_score
    score_breakdown['Renewable Energy'] = (renewable_score, 15, f'{renewable_pct}% renewable commitment')
    
    # 2. WATER MANAGEMENT (8 pts)
    water_stress = row['water stress']
    water_data = row['annual water consumption (gallons)']
    
    if water_stress in ['Low (<10%)', 'Low - Medium (10-20%)']:
        water_score = 8
        water_detail = f'Low stress area: {water_stress}'
    elif water_stress in ['Medium - High (20-40%)'] and water_data not in ['-', '', None]:
        water_score = 5
        water_detail = f'Med-high stress w/ disclosure: {water_stress}'
    elif water_stress in ['High (40-80%)', 'Extremely High (>80%)']:
        water_score = 0
        water_detail = f'High/extreme stress: {water_stress}'
    else:
        water_score = 3
        water_detail = 'Partial credit'
    
    total += water_score
    score_breakdown['Water Management'] = (water_score, 8, water_detail)
    
    # 3. EMISSIONS DISCLOSURE (15 pts)
    nox = row['nox tpy']
    pm25 = row['pm2.5 tpy']
    co2e = row['co2e tpy']
    
    emissions_disclosed = sum([
        nox not in ['-', '', None],
        pm25 not in ['-', '', None],
        co2e not in ['-', '', None]
    ])
    emissions_score = (emissions_disclosed / 3) * 15
    total += emissions_score
    
    disclosed = []
    if nox not in ['-', '', None]: disclosed.append('NOx')
    if pm25 not in ['-', '', None]: disclosed.append('PM2.5')
    if co2e not in ['-', '', None]: disclosed.append('CO2e')
    
    emissions_detail = f'{emissions_disclosed}/3 disclosed: {", ".join(disclosed) if disclosed else "None"}'
    score_breakdown['Emissions Disclosure'] = (emissions_score, 15, emissions_detail)
    
    # 4. POPULATION EXPOSURE (10 pts)
    pop = row['total population within 1 mile of site']
    if pd.notna(pop) and pop != '-':
        pop_num = float(pop) if isinstance(pop, (int, float)) else 0
        if pop_num < 1000:
            pop_score = 10
            pop_detail = f'{int(pop_num):,} residents (low density)'
        elif pop_num < 5000:
            pop_score = 5
            pop_detail = f'{int(pop_num):,} residents (medium density)'
        else:
            pop_score = 0
            pop_detail = f'{int(pop_num):,} residents (high density)'
    else:
        pop_score = 3
        pop_detail = 'No data (partial credit)'
    
    total += pop_score
    score_breakdown['Population Exposure'] = (pop_score, 10, pop_detail)
    
    # 5. ENVIRONMENTAL JUSTICE (10 pts)
    ej_state = row['state environmental justice concern']
    ej_us = row['us environmental justice concern']
    
    if ej_state == 'no' and ej_us == 'no':
        ej_score = 10
        ej_detail = 'No EJ concerns'
    else:
        ej_score = 0
        concerns = []
        if ej_state != 'no': concerns.append('State')
        if ej_us != 'no': concerns.append('Federal')
        ej_detail = f'EJ flags: {", ".join(concerns)}'
    
    total += ej_score
    score_breakdown['Environmental Justice'] = (ej_score, 10, ej_detail)
    
    # 6. COMMUNITY ENGAGEMENT (5 pts)
    total += 5
    score_breakdown['Community Engagement'] = (5, 5, 'Default (stakeholder outreach)')
    
    # 7. POWER DEMAND (5 pts)
    power = row['power_numeric']
    if pd.notna(power):
        if power < 50000:
            power_score = 5
            power_detail = f'{power/1000:.1f} MW (low)'
        elif power < 100000:
            power_score = 3
            power_detail = f'{power/1000:.1f} MW (medium)'
        else:
            power_score = 0
            power_detail = f'{power/1000:.1f} MW (high)'
    else:
        power_score = 2
        power_detail = 'No data (partial credit)'
    
    total += power_score
    score_breakdown['Power Demand'] = (power_score, 5, power_detail)
    
    # 8. DISCLOSURE QUALITY (25 pts)
    disclosure = row['disclosure_score']
    disclosure_score = (disclosure / 100) * 25
    total += disclosure_score
    score_breakdown['Transparency & Disclosure'] = (disclosure_score, 25, f'{disclosure:.0f}% fields complete')
    
    # Print breakdown
    print(f"\nFINAL SCORE: {total:.1f}/100")
    print(f"TIER: {row['exemption_tier']}\n")
    
    
    # Environmental (38 pts)
    env_total = sum(score_breakdown[k][0] for k in ['Renewable Energy', 'Water Management', 'Emissions Disclosure'])
    print(f"\nENVIRONMENTAL IMPACT: {env_total:.1f}/38 pts")
    for cat in ['Renewable Energy', 'Water Management', 'Emissions Disclosure']:
        score, max_pts, detail = score_breakdown[cat]
        print(f"  • {cat}: {score:.1f}/{max_pts} pts — {detail}")
    
    # Community (30 pts)
    comm_total = sum(score_breakdown[k][0] for k in ['Population Exposure', 'Environmental Justice', 'Community Engagement', 'Power Demand'])
    print(f"\nCOMMUNITY IMPACT: {comm_total:.1f}/30 pts")
    for cat in ['Population Exposure', 'Environmental Justice', 'Community Engagement', 'Power Demand']:
        score, max_pts, detail = score_breakdown[cat]
        print(f"  • {cat}: {score:.1f}/{max_pts} pts — {detail}")
    
    # Transparency (25 pts)
    trans_score, trans_max, trans_detail = score_breakdown['Transparency & Disclosure']
    print(f"\nTRANSPARENCY: {trans_score:.1f}/{trans_max} pts")
    print(f"  • Disclosure Quality: {trans_score:.1f}/{trans_max} pts — {trans_detail}")
    
    # Issues
    if row['failing_criteria']:
        print(f"\n KEY ISSUES:")
        for issue in row['failing_criteria']:
            print(f"  • {issue}")


# Calculate SCORES
results = df.apply(calculate_exemption_eligibility, axis=1)
df['exemption_score'] = results.apply(lambda x: x[0])
df['exemption_tier'] = results.apply(lambda x: x[1])
df['failing_criteria'] = results.apply(lambda x: x[2])

# Select 5 diverse examples - mix of high, medium, low scorers
# Sort by score to pick from different ranges
df_sorted = df.sort_values('exemption_score')

sample_indices = [
    0,  # Lowest scorer
    len(df_sorted) // 4,  # Lower quartile
    len(df_sorted) // 2,  # Median
    3 * len(df_sorted) // 4,  # Upper quartile
    len(df_sorted) - 1  # Highest scorer
]

for i, idx in enumerate(sample_indices, 1):
    row = df_sorted.iloc[idx]
    print_detailed_breakdown(row, i)
