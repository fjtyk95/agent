import os
import matplotlib.pyplot as plt

__all__ = ["plot_cost_comparison"]

def plot_cost_comparison(baseline_cost: float, optimised_cost: float, output_path: str = "/output/cost_comparison.png") -> None:
    """Plot stacked bar chart comparing baseline and optimised cost."""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(4, 6))

    # Side-by-side comparison bars
    categories = ["Baseline", "Optimised"]
    costs = [baseline_cost, optimised_cost]
    
    bars = ax.bar(categories, costs, color=["#ff7f7f", "#7fbf7f"])
    
    # Add value labels on bars
    for bar, cost in zip(bars, costs):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{cost:,.0f}', ha='center', va='bottom')

    ax.set_ylabel("Cost")
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)

