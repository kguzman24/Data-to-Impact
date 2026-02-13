#!/usr/bin/env python3
"""
Data Center Transparency & Accountability Framework
Visualization Script for Virginia Data Centers

Creates 4 key plots:
1. Geographic concentration map (VA counties)
2. Power vs Population scatter (community impact)
3. Missing data analysis (disclosure gaps)
4. Dashboard mockup comparison (before/after)
"""

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

# PLOT 1: Geographic Concentration - Facilities by County
# Count facilities by county
county_counts = df.groupby('county').size().sort_values(ascending=False)

# Create figure
fig, ax = plt.subplots(figsize=(14, 8))

# Bar plot
colors = ["#771e25" if count > 50 else '#457b9d' for count in county_counts.values]
bars = ax.barh(county_counts.index[:15], county_counts.values[:15], color=colors)

# Styling
ax.set_xlabel('Number of Data Centers', fontsize=12, fontweight='bold')
ax.set_ylabel('County', fontsize=12, fontweight='bold')
ax.set_title('Virginia Data Center Concentration by County\nNorthern Virginia Dominance', 
             fontsize=14, fontweight='bold', pad=20)

# Add value labels
for i, (county, count) in enumerate(zip(county_counts.index[:15], county_counts.values[:15])):
    ax.text(count + 2, i, str(count), va='center', fontsize=10, fontweight='bold')

# Add annotation
ax.text(0.02, 0.98, 
        f'Total VA Facilities: {len(df)}\nLoudoun County: {county_counts["Loudoun"]} ({county_counts["Loudoun"]/len(df)*100:.1f}%)',
        transform=ax.transAxes, fontsize=11, verticalalignment='bottom', 
        horizontalalignment='right', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig(OUTPUT_PATH / '1_geographic_concentration.png', dpi=300, bbox_inches='tight')
plt.close()


# PLOT 2: Power vs Population - Community Impact

# Filter for valid data
plot_df = df[
    (df['power_numeric'].notna()) & 
    (df['pop_numeric'].notna()) &
    (df['power_numeric'] > 0)
].copy()

#print(f"Found {len(plot_df)} facilities with both power and population data")

# Create figure
fig, ax = plt.subplots(figsize=(12, 8))

# Map water stress to colors
water_stress_colors = {
    'Extremely High (>80%)': '#d62828',
    'High (40-80%)': '#f77f00',
    'Medium - High (20-40%)': '#fcbf49',
    'Low - Medium (10-20%)': '#06d6a0',
    'Low (<10%)': '#118ab2',
    'Arid and Low Water Use': '#073b4c',
    '': '#cccccc',
    '-': '#cccccc'
}

# Add color based on water stress
plot_df['color'] = plot_df['water stress'].map(water_stress_colors).fillna('#cccccc')

# Scatter plot
scatter = ax.scatter(
    plot_df['power_numeric'],
    plot_df['pop_numeric'],
    c=plot_df['color'],
    s=100,
    alpha=0.6,
    edgecolors='black',
    linewidth=0.5
)

# Styling
ax.set_xlabel('Power Consumption (kW/hr at 50% capacity)', fontsize=12, fontweight='bold')
ax.set_ylabel('Population Within 1 Mile', fontsize=12, fontweight='bold')
ax.set_title('Data Center Community Impact:\nPower Consumption vs. Population Exposure',
             fontsize=14, fontweight='bold', pad=20)

# Log scale for better visibility
ax.set_xscale('log')

# Add grid
ax.grid(True, alpha=0.3)

# Create custom legend for water stress
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#d62828', label='Extremely High (>80%)'),
    Patch(facecolor='#f77f00', label='High (40-80%)'),
    Patch(facecolor='#fcbf49', label='Medium-High (20-40%)'),
    Patch(facecolor='#06d6a0', label='Low-Medium (10-20%)'),
    Patch(facecolor='#cccccc', label='No data/Other')
]
ax.legend(handles=legend_elements, title='Water Stress Level', 
          loc='upper right', fontsize=9, title_fontsize=10)

# Add annotation for high-impact facilities
high_impact = plot_df[(plot_df['power_numeric'] > 50000) & (plot_df['pop_numeric'] > 5000)]
ax.text(0.02, 0.98, 
        f'High Impact Facilities:\n{len(high_impact)} with >50MW power\nAND >5,000 nearby residents',
        transform=ax.transAxes, fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig(OUTPUT_PATH / '2_power_vs_population.png', dpi=300, bbox_inches='tight')
plt.close()

# PLOT 3: Missing Data Analysis - The Disclosure Gap

# Define key fields to check
fields_to_check = {
    'Water Consumption\n(Annual)': 'annual water consumption (gallons)',
    'Water Consumption\n(Daily)': 'daily water consumption (gallons)',
    'NOx Emissions': 'nox tpy',
    'PM Emissions': 'pm tpy',
    'PM2.5 Emissions': 'pm2.5 tpy',
    'CO2e Emissions': 'co2e tpy',
    'Power (Actual)': 'estimate power consumption in kw/hr (calculated 50%)'
}

# Calculate missing data percentages
missing_data = {}
for label, field in fields_to_check.items():
    total = len(df)
    missing = df[field].isin(['-', '', 'redacted']).sum() + df[field].isna().sum()
    missing_data[label] = {
        'missing': missing,
        'present': total - missing,
        'missing_pct': (missing / total) * 100
    }

# Create stacked bar chart
fig, ax = plt.subplots(figsize=(12, 8))

categories = list(missing_data.keys())
missing_counts = [missing_data[cat]['missing'] for cat in categories]
present_counts = [missing_data[cat]['present'] for cat in categories]

x = np.arange(len(categories))
width = 0.6

# Stacked bars
bars1 = ax.barh(x, present_counts, width, label='Data Available', color="#448b78")
bars2 = ax.barh(x, missing_counts, width, left=present_counts, label='Missing/Redacted', color="#af464f")

# Styling
ax.set_yticks(x)
ax.set_yticklabels(categories)
ax.set_xlabel('Number of Facilities (out of 329 total)', fontsize=12, fontweight='bold')
ax.set_title('The Transparency Gap:\nMissing Data in Virginia Data Center Permits',
             fontsize=14, fontweight='bold', pad=20)

# Add percentage labels
for i, cat in enumerate(categories):
    total = len(df)
    missing_pct = missing_data[cat]['missing_pct']
    present_pct = 100 - missing_pct
    
    # Label for present data
    if present_counts[i] > 0:
        ax.text(present_counts[i]/2, i, f'{present_pct:.0f}%', 
                ha='center', va='center', fontweight='bold', color='white')
    
    # Label for missing data
    if missing_counts[i] > 0:
        ax.text(present_counts[i] + missing_counts[i]/2, i, f'{missing_pct:.0f}%', 
                ha='center', va='center', fontweight='bold', color='white')

ax.legend(loc='lower right', fontsize=11)

# Add annotation
ax.text(0.98, 0.98, 
        'WHY THIS MATTERS:\nWithout complete data,\nlocalities cannot assess\ncommunity impact',
        transform=ax.transAxes, fontsize=11, verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

plt.tight_layout()
plt.savefig(OUTPUT_PATH / '3_missing_data_analysis.png', dpi=300, bbox_inches='tight')
plt.close()

# PLOT 4: County Comparison - NoVA vs I-95 Corridor vs Rest

# Define regions
nova_counties = ['Loudoun', 'Fairfax', 'Prince William', 'Arlington']
i95_corridor = ['Henrico', 'Mecklenberg', 'Chesterfield']

df['region'] = df['county'].apply(
    lambda x: 'Northern VA' if x in nova_counties 
    else ('I-95 Corridor' if x in i95_corridor else 'Rest of VA')
)

region_counts = df['region'].value_counts()

# Create pie chart
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Pie chart
colors_pie = ['#e63946', '#457b9d', '#f1faee']
wedges, texts, autotexts = ax1.pie(
    region_counts.values,
    labels=region_counts.index,
    autopct='%1.1f%%',
    startangle=90,
    colors=colors_pie,
    textprops={'fontsize': 12, 'fontweight': 'bold'}
)

ax1.set_title('Distribution of Virginia Data Centers\nby Region',
              fontsize=14, fontweight='bold', pad=20)

# Bar chart showing top counties
top_counties = df['county'].value_counts().head(10)
ax2.barh(range(len(top_counties)), top_counties.values, color='#457b9d')
ax2.set_yticks(range(len(top_counties)))
ax2.set_yticklabels(top_counties.index)
ax2.set_xlabel('Number of Facilities', fontsize=12, fontweight='bold')
ax2.set_title('Top 10 Counties by Facility Count',
              fontsize=14, fontweight='bold', pad=20)

# Add value labels
for i, count in enumerate(top_counties.values):
    ax2.text(count + 2, i, str(count), va='center', fontweight='bold')

# Add summary stats
summary_text = f"""
REGIONAL BREAKDOWN:
Northern VA: {region_counts['Northern VA']} facilities ({region_counts['Northern VA']/len(df)*100:.1f}%)
I-95 Corridor: {region_counts.get('I-95 Corridor', 0)} facilities ({region_counts.get('I-95 Corridor', 0)/len(df)*100:.1f}%)
Rest of VA: {region_counts.get('Rest of VA', 0)} facilities ({region_counts.get('Rest of VA', 0)/len(df)*100:.1f}%)
"""

fig.text(0.98, 0.98, summary_text, ha='center', fontsize=10,
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig(OUTPUT_PATH / '4_regional_distribution.png', dpi=300, bbox_inches='tight')
plt.close()



# PLOT 5: Tax Exemption Value vs. Disclosure Quality
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

df['estimated_tax_exemption'] = df['power_numeric'].apply(
    lambda x: 15_500_000 if pd.notna(x) and x > 100000 else 
             (9_000_000 if pd.notna(x) and x > 50000 else 5_000_000)
)

fig, ax = plt.subplots(figsize=(14, 9))

colors_map = {
    'Possible hyperscaler': '#e63946',
    'large-scale': '#f77f00',
    'small-scale': '#457b9d',
    'Unknown': '#cccccc'
}

for category, color in colors_map.items():
    mask = df['size_category'] == category
    if mask.sum() > 0:
        ax.scatter(df[mask]['disclosure_score'], 
                  df[mask]['estimated_tax_exemption'],
                  c=color, s=100, alpha=0.6, 
                  edgecolors='black', linewidth=0.5,
                  label=category)

ax.set_xlabel('Disclosure Score (0-100%)\nBased on Data Completeness', 
              fontsize=12, fontweight='bold')
ax.set_ylabel('Estimated Tax Exemption Value ($)', fontsize=12, fontweight='bold')
ax.set_title('The Accountability Gap:\nMillion-Dollar Tax Breaks With Minimal Transparency',
             fontsize=14, fontweight='bold', pad=20)

ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))

ax.axvline(50, color='gray', linestyle='--', alpha=0.5, linewidth=1)
ax.axhline(10_000_000, color='gray', linestyle='--', alpha=0.5, linewidth=1)

ax.text(75, 16_000_000, 'HIGH VALUE\nHIGH TRANSPARENCY\n(Rare)', 
        ha='center', va='center', fontsize=10, style='italic',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

ax.text(25, 16_000_000, 'HIGH VALUE\nLOW TRANSPARENCY\n(Current Reality)', 
        ha='center', va='center', fontsize=10, style='italic', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='#ffe5e5', alpha=0.7))

ax.text(25, 4_000_000, 'LOW VALUE\nLOW TRANSPARENCY', 
        ha='center', va='center', fontsize=10, style='italic',
        bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

ax.text(75, 4_000_000, 'LOW VALUE\nHIGH TRANSPARENCY', 
        ha='center', va='center', fontsize=10, style='italic',
        bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.3))

median_score = df['disclosure_score'].median()
total_exemptions = df['estimated_tax_exemption'].sum()

annotation_text = f"""
THE PROBLEM:
Median disclosure score: {median_score:.0f}%
Total estimated tax exemptions: ${total_exemptions/1e9:.2f}B

Most facilities cluster in upper-left:
Getting millions in tax breaks while
providing minimal environmental data.

OUR SOLUTION:
Condition exemptions on disclosure.
"""

ax.text(0.98, 0.02, annotation_text, transform=ax.transAxes,
        fontsize=10, verticalalignment='bottom', horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

ax.legend(loc='upper left', fontsize=10, title='Facility Size')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_PATH / '5_tax_exemption_vs_transparency.png', dpi=300, bbox_inches='tight')
plt.close()

# PLOT 6: Tiered Exemption Eligibility Under Proposed Standards

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

results = df.apply(calculate_exemption_eligibility, axis=1)
df['exemption_score'] = results.apply(lambda x: x[0])
df['exemption_tier'] = results.apply(lambda x: x[1])
df['failing_criteria'] = results.apply(lambda x: x[2])

tier_counts = df['exemption_tier'].value_counts()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

colors_tier = ['#e63946', '#f77f00', '#06d6a0']
# Dynamic explode based on actual number of tiers
explode = tuple([0.1 if i == 0 else 0.05 if i == 1 else 0 for i in range(len(tier_counts))])

wedges, texts, autotexts = ax1.pie(
    tier_counts.values,
    labels=[f"{label}\n({count} facilities)" for label, count in zip(tier_counts.index, tier_counts.values)],
    autopct='%1.1f%%',
    startangle=90,
    colors=colors_tier,
    explode=explode,
    textprops={'fontsize': 11, 'fontweight': 'bold'}
)

ax1.set_title('Tiered Exemption Eligibility\nUnder Proposed Standards',
              fontsize=14, fontweight='bold', pad=20)

ax2.hist(df['exemption_score'], bins=20, color='#457b9d', edgecolor='black', alpha=0.7)

ax2.axvline(80, color='#06d6a0', linestyle='--', linewidth=2, 
            label='Full Exemption (≥80)')
ax2.axvline(60, color='#f77f00', linestyle='--', linewidth=2,
            label='Partial Exemption (≥60)')

ax2.set_xlabel('Exemption Eligibility Score (0-100)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Number of Facilities', fontsize=12, fontweight='bold')
ax2.set_title('Distribution of Exemption Scores\nMost Facilities Would Need to Improve',
              fontsize=14, fontweight='bold', pad=20)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_PATH / '6_tiered_exemption_eligibility.png', dpi=300, bbox_inches='tight')
plt.close()

print("SUMMARY STATISTICS")
print(f"\nTotal VA Facilities: {len(df)}")
print(f"\nTop 3 Counties:")
for county, count in county_counts.head(3).items():
    print(f"  {county}: {count} ({count/len(df)*100:.1f}%)")

print(f"\nFacilities with Population Data: {len(df[df['pop_numeric'].notna()])}")
print(f"Facilities with Power Data: {len(df[df['power_numeric'].notna()])}")

print(f"\nWater Data Completeness:")
water_fields = ['annual water consumption (gallons)', 'daily water consumption (gallons)']
for field in water_fields:
    missing = df[field].isin(['-', '']).sum() + df[field].isna().sum()
    print(f"  {field}: {(1 - missing/len(df))*100:.1f}% complete")

print(f"\nTRANSPARENCY & ACCOUNTABILITY:")
print(f"  Median disclosure score: {df['disclosure_score'].median():.1f}%")
print(f"  Total estimated tax exemptions: ${df['estimated_tax_exemption'].sum()/1e9:.2f}B")

print(f"\nTIERED EXEMPTION ELIGIBILITY:")
for tier in ['Full Exemption (100%)', 'Partial Exemption (50%)', 'No Exemption (0%)']:
    count = (df['exemption_tier'] == tier).sum()
    print(f"  {tier}: {count} facilities ({count/len(df)*100:.1f}%)")

print(f"\nMean exemption score: {df['exemption_score'].mean():.1f}")
print(f"Median exemption score: {df['exemption_score'].median():.1f}")