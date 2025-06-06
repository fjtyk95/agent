import os
import matplotlib.pyplot as plt

__all__ = ["plot_cost_comparison"]

def plot_cost_comparison(baseline_cost: float, optimised_cost: float, output_path: str = "/output/cost_comparison.png") -> None:
    """Plot stacked bar chart comparing baseline and optimised cost."""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(4, 6))

    # Single stacked bar
    ax.bar(["Cost"], [baseline_cost], label="Baseline")
    ax.bar(["Cost"], [optimised_cost], bottom=[baseline_cost], label="Optimised")

    ax.set_ylabel("Cost")
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)

