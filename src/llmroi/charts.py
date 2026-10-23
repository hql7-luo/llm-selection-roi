"""Static charts for the README (PNG), in one quiet, consistent style."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

SOURCE = "Prices checked 2026-10-23 (see data/pricing.csv). Labor and error-cost inputs: data/roi_inputs.csv."


def use_style():
    for path in Path("/usr/share/fonts/opentype/inter").glob("Inter-*.otf"):
        font_manager.fontManager.addfont(str(path))
    plt.rcParams.update({
        "font.family": ["Inter", "DejaVu Sans"],
        "font.size": 10,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "xtick.color": MUTED,
        "ytick.color": INK_2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.facecolor": SURFACE,
        "savefig.dpi": 200,
        "text.parse_math": False,
    })


def titles(fig, title, subtitle):
    fig.text(0.03, 0.965, title, fontsize=15, fontweight="bold", color=INK, va="top")
    fig.text(0.03, 0.905, subtitle, fontsize=10.5, color=INK_2, va="top")


def source(fig, text=SOURCE):
    fig.text(0.03, 0.012, text, fontsize=8, color=MUTED, va="bottom")


def usd(v):
    if v < 1:
        return f"${v:.2f}"
    return f"${v:,.0f}" if v >= 10 else f"${v:.1f}"


# Figure 1: API cost per 1,000 inquiries for each model, next to the labor it could save
def plot_cost_vs_labor(models, labor_saved_1000, manual_cost_1000, path):
    models = sorted(models, key=lambda m: m["cost_per_1000"])
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.2, right=0.95, top=0.78, bottom=0.16)
    y = range(len(models))
    ax.barh(list(y), [m["cost_per_1000"] for m in models], height=0.55, color=BLUE)
    ax.set_xscale("log")
    ax.set_xlim(0.03, 3000)
    ax.set_yticks(list(y), [m["name"] for m in models])
    for i, m in enumerate(models):
        ax.text(m["cost_per_1000"] * 1.15, i, usd(m["cost_per_1000"]), va="center", fontsize=9, color=INK_2)
    ax.axvline(labor_saved_1000, color=INK, lw=1)
    ax.text(labor_saved_1000 * 0.9, len(models) - 0.45, f"Labor an AI draft\ncould save: {usd(labor_saved_1000)}",
            ha="right", va="top", fontsize=8.5, color=INK)
    ax.axvline(manual_cost_1000, color=MUTED, lw=1)
    ax.text(manual_cost_1000 * 1.1, -0.2, f"All-manual\nlabor: {usd(manual_cost_1000)}",
            ha="left", va="bottom", fontsize=8.5, color=INK_2)
    ax.set_xticks([0.1, 1, 10, 100, 1000], ["$0.10", "$1", "$10", "$100", "$1,000"])
    ax.set_xlabel("USD per 1,000 inquiries (log scale)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    share = max(m["cost_per_1000"] for m in models) / labor_saved_1000
    titles(fig, f"The priciest model costs about {share:.0%} of the labor it could save",
           "Estimated API cost per 1,000 inquiries at list prices; bars are model cost, lines are labor cost.")
    source(fig, "Token counts estimated from the prompt and answer length (about 4 characters per token). "
                + "Prices: data/pricing.csv, checked 2026-10-23.")
    fig.savefig(path)
    plt.close(fig)


# Figure 2: monthly net benefit against critical error rate, cheapest vs priciest model, plus measured points
def plot_breakeven(curves, rules_point, llm_points, breakeven, volume, path):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.11, right=0.95, top=0.78, bottom=0.16)
    for (name, xs, ys), color in zip(curves, [BLUE, ORANGE]):
        ax.plot([x * 100 for x in xs], ys, color=color, lw=2, label=name)
    ax.axhline(0, color=AXIS, lw=1)
    ax.axvline(breakeven * 100, color=INK, lw=1)
    ax.text(breakeven * 100 + 0.6, ax.get_ylim()[1] * 0.92, f"Break-even\n{breakeven:.0%} critical errors",
            fontsize=9, color=INK, va="top")
    signed = lambda v: usd(v) if v >= 0 else "-" + usd(-v)
    rx, ry = rules_point
    ax.plot([rx * 100], [ry], "o", ms=9, color=INK, mec=SURFACE, mew=2, zorder=5)
    ax.annotate(f"Rules, no AI (measured)\n{rx:.0%} errors, {signed(ry)}/month",
                (rx * 100, ry), xytext=(16, 14), textcoords="offset points", fontsize=9, color=INK)
    if llm_points:
        for e, net in llm_points:
            ax.plot([e * 100], [net], "o", ms=9, color=INK, mec=SURFACE, mew=2, zorder=5)
        lo = min(e for e, _ in llm_points)
        hi = max(e for e, _ in llm_points)
        bottom = min(net for _, net in llm_points)
        top = max(net for _, net in llm_points)
        ax.text(0.035, 0.54, f"Tested models (measured errors)\n{lo:.2%} to {hi:.2%} errors\n"
                f"API-price scenario: {signed(bottom)} to {signed(top)}/month",
                transform=ax.transAxes, fontsize=9, color=INK, va="top", ha="left")
    ax.set_xlabel("Critical error rate: share of inquiries with a wrong product, spec, quantity, price or date")
    ax.set_ylabel(f"Net benefit per month at {volume:,.0f} inquiries (USD)")
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}" if v >= 0 else f"-${-v:,.0f}")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    titles(fig, "Estimated net benefit falls as critical errors increase",
           "Cheapest vs priciest model with the same workflow (AI draft + human review): the lines almost overlap.")
    source(fig, "Claude and GPT: non-API batches of 20, two runs each. API costs are scenario estimates, not actual Codex costs.\n"
                + SOURCE)
    fig.savefig(path)
    plt.close(fig)


# Figure 3: rules baseline, field accuracy on regular vs hard inquiries
def plot_rules_by_field(rows, critical, traps_caught, traps_total, path):
    fig, ax = plt.subplots(figsize=(9, 5.4))
    fig.subplots_adjust(left=0.17, right=0.95, top=0.76, bottom=0.16)
    fields = [r["field"] for r in rows]
    y = list(range(len(fields)))
    h = 0.36
    ax.barh([i - h / 2 - 0.02 for i in y], [r["regular"] * 100 for r in rows], height=h, color=BLUE,
            label=f"Regular (critical errors: {critical['regular']:.0%} of inquiries)")
    ax.barh([i + h / 2 + 0.02 for i in y], [r["hard"] * 100 for r in rows], height=h, color=ORANGE,
            label=f"Hard (critical errors: {critical['hard']:.0%} of inquiries)")
    ax.set_yticks(y, [f.replace("_", " ") for f in fields])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlabel("Share of fields correct (test set)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9)
    titles(fig, "Rules read tidy forms well but break on real-world messages",
           f"No-AI baseline (keywords + regular expressions) on the 80 test inquiries. "
           f"Traps marked low priority: {traps_caught} of {traps_total}.")
    source(fig, "Measured: runs/rules/run1.jsonl scored by src/llmroi/scoring.py. Rules and data have the same author, "
                "so this score is likely optimistic.")
    fig.savefig(path)
    plt.close(fig)


# Figure 4: which assumption moves the break-even error rate the most
def plot_sensitivity(rows, base, path):
    labels = {
        "catch_rate": "Reviewer catches 60% / 95% of AI errors",
        "escaped_error_cost_usd": "Cost of an escaped error $10 / $150",
        "manual_error_rate": "Manual error rate 0% / 5%",
        "manual_minutes": "Manual handling 3 / 10 minutes",
        "review_minutes": "Review 0.75 / 3 minutes",
        "monthly_salary_cny": "Salary ¥7,000 / ¥11,000 a month",
        "employer_overhead": "Employer overhead 1.20x / 1.45x",
        "fix_minutes": "Fixing a caught error 1 / 6 minutes",
        "monthly_volume": "Volume 100 / 2,000 inquiries a month",
        "monthly_maintenance_usd": "Maintenance $0 / $200 a month",
        "model_price": "Model: cheapest / priciest",
    }
    rows = sorted(rows, key=lambda r: r["swing"])
    fig, ax = plt.subplots(figsize=(9, 5.6))
    fig.subplots_adjust(left=0.36, right=0.95, top=0.76, bottom=0.16)
    for i, r in enumerate(rows):
        lo, hi = r["breakeven_at_low"] * 100, r["breakeven_at_high"] * 100
        ax.barh(i, lo - base * 100, left=base * 100, height=0.55, color=BLUE)
        ax.barh(i, hi - base * 100, left=base * 100, height=0.55, color=ORANGE)
    ax.axvline(base * 100, color=INK, lw=1)
    ax.set_yticks(range(len(rows)), [labels.get(r["input"], r["input"]) for r in rows])
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlabel(f"Break-even critical error rate (base case {base:.1%})")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    for i, r in enumerate(rows):
        if r["swing"] < 0.005:                          # too small to see as a bar
            ax.text(base * 100 + 0.6, i, f"moves it by {r['swing'] * 100:.2f} points", va="center",
                    fontsize=9, color=INK)
    ax.legend(handles=[Patch(color=BLUE, label="First value in the label"),
                       Patch(color=ORANGE, label="Second value")],
              frameon=False, loc="lower right", fontsize=9)
    titles(fig, "What moves the bar: the review step, not the model price",
           "How the highest acceptable error rate changes when one assumption moves at a time.")
    source(fig)
    fig.savefig(path)
    plt.close(fig)


# Figure 5: measured critical error rate against cost for each tested method
def plot_measured(methods, breakeven, path):
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.11, right=0.95, top=0.78, bottom=0.16)
    methods = sorted(methods, key=lambda m: max(m["cost_per_1000"], 0.05))
    xs = [max(m["cost_per_1000"], 0.05) for m in methods]
    label_positions = []
    for i, m in enumerate(methods):
        x, y = xs[i], m["critical_error_rate"] * 100
        ax.plot([x], [y], "o", ms=9, color=INK if m["method"] == "rules" else BLUE, mec=SURFACE, mew=2, zorder=5)
        # Stagger labels for nearby points on the log axis, including equal-cost models.
        label_y = y + 1.3
        nearby = [py for px, py in label_positions if max(px, x) / min(px, x) < 3]
        while any(abs(label_y - py) < 3.5 for py in nearby):
            label_y = max(py + 3.5 for py in nearby if abs(label_y - py) < 3.5)
        label_positions.append((x, label_y))
        label_x = x
        if i + 1 < len(xs) and xs[i + 1] == x and abs(methods[i + 1]["critical_error_rate"] * 100 - y) < 3.5:
            label_x = x * 1.6
        elif i > 0 and xs[i - 1] == x and abs(methods[i - 1]["critical_error_rate"] * 100 - y) < 3.5:
            label_x = x / 2
        # Use the same four-decimal rate as method_summary.csv for displayed percentages.
        displayed_rate = round(m["critical_error_rate"], 4)
        ax.annotate(f"{m['name']}\n{displayed_rate:.2%}", (x, y), xytext=(label_x, label_y), textcoords="data",
                    fontsize=9, color=INK_2, ha="center", va="bottom",
                    arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.6}
                    if label_y > y + 1.3 or label_x != x else None)
    ax.axhline(breakeven * 100, color=INK, lw=1)
    ax.text(0.055, breakeven * 100 - 1.2, f"Break-even: {breakeven:.0%}", fontsize=9, color=INK, va="top")
    ax.set_xscale("log")
    ax.set_xlim(0.02, 30)
    ax.set_ylim(-2, 30)
    ax.set_xticks([0.05, 0.1, 1, 10], ["no API", "$0.10", "$1", "$10"])
    ax.set_xlabel("Estimated API cost per 1,000 inquiries at list price (log scale)")
    ax.set_ylabel("Critical error rate (80 test inquiries)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    titles(fig, "Tested models have lower critical error rates than the rules baseline",
           "Claude and GPT: non-API batches of 20, two runs each, averaged. Rules use no AI.")
    source(fig, "API costs are scenario estimates, not actual Codex costs. Test data was written with Claude's help,\n"
                "which may favor Claude. Results cover 80 synthetic inquiries.")
    fig.savefig(path)
    plt.close(fig)
