import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import seaborn as sns

# Ensure directory
output_dir = r"C:\Users\spnay\.gemini\antigravity\brain\c3e31b6d-3e68-4f38-95c5-076b8a8473d8"

# Setup beautiful style
sns.set_theme(style="whitegrid")

# -------------------------------------------------------------
# GRAPH 1: Pie Chart for Overall Performance
# -------------------------------------------------------------
plt.figure(figsize=(8, 6))
labels = ['Perfect Match (90%)', 'Failed Edge Case (10%)']
sizes = [9, 1]
colors = ['#2ECC71', '#E74C3C']
explode = (0.1, 0)

plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
        shadow=True, startangle=140, textprops={'fontsize': 14, 'color': 'black'})
plt.title('Voice AI Overall Parsing Accuracy', fontsize=18, pad=20)
plt.savefig(os.path.join(output_dir, 'accuracy_pie.png'), bbox_inches='tight', dpi=300)
plt.close()

# -------------------------------------------------------------
# GRAPH 2: Bar Chart for Component Heuristics
# -------------------------------------------------------------
plt.figure(figsize=(10, 6))
components = ['Intent Prediction', 'Priority Detection', 'Date/Time Extraction', 'Entity/Task Name Extraction']
scores = [100, 100, 100, 90]

ax = sns.barplot(x=components, y=scores, palette="viridis")
plt.ylim(0, 110)
plt.ylabel('Accuracy (%)', fontsize=14)
plt.title('Performance Breakdown by NLP Component', fontsize=18, pad=20)

for i, v in enumerate(scores):
    ax.text(i, v + 2, f"{v}%", ha='center', fontsize=12, fontweight='bold', color='black')

plt.xticks(rotation=15, fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'component_metrics.png'), bbox_inches='tight', dpi=300)
plt.close()

print("Graphs successfully generated and saved to artifact directory.")
