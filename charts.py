import matplotlib.pyplot as plt

__all__ = ["plot_cost_comparison"]


def plot_cost_comparison(baseline: int, optimised: int, output_path: str = "/output/cost_comparison.png") -> None:
    """Save a stacked bar chart comparing baseline and optimised costs."""
    fig, ax = plt.subplots()
    ax.bar(["baseline"], [baseline], label="baseline")
    ax.bar(["optimised"], [optimised], bottom=[0], label="optimised")
    ax.set_ylabel("Cost")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
