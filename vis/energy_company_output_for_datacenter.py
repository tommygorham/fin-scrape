import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Data extracted from the document (in GW)
# Using current/contracted capacity where available, otherwise using planned/pipeline figures
data = {
    'Company': [
        'Dominion Energy',
        'American Electric Power', 
        'Duke Energy',
        'Southern Company',
        'Entergy',
        'Xcel Energy',
        'MidAmerican Energy',
        'DTE Energy',
        'Talen Energy',
        'Constellation Energy',
        'NextEra Energy',
        'AES Corporation',
        'NV Energy'
    ],
    'Current/Contracted (GW)': [
        9.8,   # Dominion - currently supplying
        2.0,   # AEP - brought online Q3 2025
        0,     # Duke - no current figure given
        7.0,   # Southern - under development
        0,     # Entergy - securing new
        1.0,   # Xcel - contracted/construction
        1.66,  # MidAmerican
        1.4,   # DTE
        0.96,  # Talen
        0.819, # Constellation
        0.615, # NextEra (nuclear restart)
        0.5,   # AES
        0.495  # NV Energy (Switch Vegas max)
    ],
    'Pipeline/Planned (GW)': [
        47.0,  # Dominion total contracted
        22.0,  # AEP pipeline through 2030
        13.0,  # Duke planned additions
        50.0,  # Southern pipeline
        4.5,   # Entergy new generation
        3.0,   # Xcel total capacity
        0,     # MidAmerican
        0,     # DTE
        0,     # Talen
        0,     # Constellation
        29.6,  # NextEra total backlog
        0,     # AES
        0      # NV Energy
    ]
}

df = pd.DataFrame(data)

# Calculate total capacity (using pipeline if larger than current)
df['Total Capacity (GW)'] = df[['Current/Contracted (GW)', 'Pipeline/Planned (GW)']].max(axis=1)

# Sort by total capacity
df = df.sort_values('Total Capacity (GW)', ascending=True)

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))

# Subplot 1: Horizontal bar chart showing current vs pipeline
y_pos = np.arange(len(df))
bar_height = 0.35

ax1.barh(y_pos - bar_height/2, df['Current/Contracted (GW)'], bar_height, 
         label='Current/Contracted', color='#2E86AB', alpha=0.8)
ax1.barh(y_pos + bar_height/2, df['Pipeline/Planned (GW)'], bar_height,
         label='Pipeline/Planned', color='#A23B72', alpha=0.8)

ax1.set_yticks(y_pos)
ax1.set_yticklabels(df['Company'])
ax1.set_xlabel('Capacity (GW)', fontsize=12)
ax1.set_title('AI Data Center Energy Capacity by Utility', fontsize=14, fontweight='bold')
ax1.legend(loc='lower right')
ax1.grid(axis='x', alpha=0.3)

# Add value labels on bars
for i, (current, pipeline) in enumerate(zip(df['Current/Contracted (GW)'], df['Pipeline/Planned (GW)'])):
    if current > 0:
        ax1.text(current + 0.5, i - bar_height/2, f'{current:.2f}', 
                va='center', fontsize=9)
    if pipeline > 0:
        ax1.text(pipeline + 0.5, i + bar_height/2, f'{pipeline:.1f}', 
                va='center', fontsize=9)

# Subplot 2: Pie chart of total capacity (top companies)
top_n = 8
df_top = df.nlargest(top_n, 'Total Capacity (GW)')
other_capacity = df.nsmallest(len(df) - top_n, 'Total Capacity (GW)')['Total Capacity (GW)'].sum()

pie_data = df_top['Total Capacity (GW)'].tolist()
pie_labels = df_top['Company'].tolist()

if other_capacity > 0:
    pie_data.append(other_capacity)
    pie_labels.append('Others')

colors = plt.cm.Set3(np.linspace(0, 1, len(pie_data)))
explode = [0.02] * len(pie_data)

wedges, texts, autotexts = ax2.pie(pie_data, labels=pie_labels, colors=colors, 
                                    explode=explode, autopct='%1.1f%%',
                                    shadow=True, startangle=90)

ax2.set_title('Market Share by Total Capacity\n(Current + Pipeline)', 
              fontsize=14, fontweight='bold')

# Adjust text properties
for text in texts:
    text.set_fontsize(10)
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontweight('bold')
    autotext.set_fontsize(9)

plt.tight_layout()

# Print summary statistics
print("\n" + "="*60)
print("AI DATA CENTER ENERGY CAPACITY SUMMARY")
print("="*60)
print(f"\nTotal Current/Contracted Capacity: {df['Current/Contracted (GW)'].sum():.2f} GW")
print(f"Total Pipeline/Planned Capacity: {df['Pipeline/Planned (GW)'].sum():.2f} GW")
print(f"Combined Maximum Capacity: {df['Total Capacity (GW)'].sum():.2f} GW")
print("\nTop 5 Companies by Total Capacity:")
print("-"*40)
for idx, row in df.nlargest(5, 'Total Capacity (GW)').iterrows():
    print(f"{row['Company']:30s} {row['Total Capacity (GW)']:>8.2f} GW")

# Show the plot
plt.show()
