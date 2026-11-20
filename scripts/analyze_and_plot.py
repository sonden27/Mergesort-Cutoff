import os
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

RAW_CSV = "results/raw_results.csv"
SUMMARY_CSV = "results/summary_stats.csv"
RANKING_CSV = "results/overall_ranking.csv"
LARGE_N_RANKING_CSV = "results/large_n_ranking.csv"
CV_BY_SIZE_CSV = "results/cv_by_size.csv"
CHARTS_DIR = "results/charts"

DIST_LABELS = {
    "random": "Random",
    "ascending": "Ascending (Sorted)",
    "descending": "Descending (Reversed)",
    "duplicates": "Many Duplicates",
}
DIST_ORDER = ["random", "ascending", "descending", "duplicates"]


def gmean(series: pd.Series) -> float:
    return float(np.exp(np.mean(np.log(series))))


def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)
    df = pd.read_csv(RAW_CSV)

    summary = (
        df.groupby(["distribution", "N", "cutoff"])["time_ms"]
        .agg(
            mean_ms="mean",
            median_ms="median",
            std_ms="std",
            min_ms="min",
            max_ms="max",
            q1_ms=lambda s: s.quantile(0.25),
            q3_ms=lambda s: s.quantile(0.75),
        )
        .reset_index()
    )
    summary["cv_pct"] = (summary["std_ms"] / summary["mean_ms"]) * 100.0

    base = summary[summary["cutoff"] == 0][
        ["distribution", "N", "mean_ms", "median_ms"]
    ].rename(columns={"mean_ms": "base_mean_ms", "median_ms": "base_median_ms"})

    summary = summary.merge(base, on=["distribution", "N"])
    summary["speedup_median"] = summary["base_median_ms"] / summary["median_ms"]
    summary["speedup_mean"] = summary["base_mean_ms"] / summary["mean_ms"]
    summary["norm_median"] = summary["median_ms"] / summary["base_median_ms"]
    summary.to_csv(SUMMARY_CSV, index=False)

    # Xep hang tong the tren toan bo bo du lieu
    ranking = (
        summary.groupby("cutoff")
        .agg(
            gmean_speedup_median=("speedup_median", gmean),
            gmean_speedup_mean=("speedup_mean", gmean),
            mean_norm_median=("norm_median", "mean"),
            avg_cv_pct=("cv_pct", "mean"),
        )
        .reset_index()
        .sort_values("gmean_speedup_median", ascending=False)
        .reset_index(drop=True)
    )
    ranking.insert(0, "rank", range(1, len(ranking) + 1))
    ranking.to_csv(RANKING_CSV, index=False)

    # Xep hang rieng cho cac mang kich thuoc lon (N >= 100,000)
    large_sub = summary[summary["N"] >= 100_000]
    if large_sub.empty:
        large_sub = summary[summary["N"] == summary["N"].max()]
    large_ranking = (
        large_sub.groupby("cutoff")
        .agg(
            gmean_speedup_median=("speedup_median", gmean),
            gmean_speedup_mean=("speedup_mean", gmean),
            avg_cv_pct=("cv_pct", "mean"),
        )
        .reset_index()
        .sort_values("gmean_speedup_median", ascending=False)
        .reset_index(drop=True)
    )
    large_ranking.insert(0, "rank", range(1, len(large_ranking) + 1))
    large_ranking.to_csv(LARGE_N_RANKING_CSV, index=False)

    # Thong ke do on dinh (CV%) theo tung kich thuoc mang N
    cv_by_size = (
        summary.groupby("N")
        .agg(
            mean_cv_pct=("cv_pct", "mean"),
            median_cv_pct=("cv_pct", "median"),
            max_cv_pct=("cv_pct", "max"),
            median_time_ms=("median_ms", "median"),
        )
        .reset_index()
        .sort_values("N")
    )
    cv_by_size.to_csv(CV_BY_SIZE_CSV, index=False)

    best_cutoff = int(ranking.iloc[0]["cutoff"])
    best_gmean = float(ranking.iloc[0]["gmean_speedup_median"])
    max_n = int(summary["N"].max())
    n_trials = int(df["trial"].nunique())

    print("=== BANG XEP HANG TOP 10 CUTOFF (TOAN BO 16 BO DU LIEU) ===")
    print(ranking.head(10).to_string(index=False))
    print("\n=== BANG XEP HANG TOP 5 CUTOFF (MANG LON N >= 100,000) ===")
    print(large_ranking.head(5).to_string(index=False))
    print("\n=== DO BIEN THIEN CV% THEO KICH THUOC MANG N ===")
    print(cv_by_size.to_string(index=False))

    # Bieu do 1: Thoi gian chay Mean, Median & IQR theo CUTOFF (2x2, N lon nhat)
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    fig.suptitle(
        f"Biểu đồ 1: Thời gian chạy trung bình, trung vị và IQR theo CUTOFF (N = {max_n:,})",
        fontsize=13, fontweight="bold"
    )
    for ax, dist in zip(axes.flat, DIST_ORDER):
        sub = summary[(summary["distribution"] == dist) & (summary["N"] == max_n)].sort_values("cutoff")
        ax.fill_between(
            sub["cutoff"], sub["q1_ms"], sub["q3_ms"],
            color="#ff7f0e", alpha=0.16, label="IQR (Q1–Q3)"
        )
        ax.plot(sub["cutoff"], sub["mean_ms"], "-o", markersize=4.5, alpha=0.8, label="Mean (ms)")
        ax.plot(sub["cutoff"], sub["median_ms"], "--s", markersize=4.5, linewidth=1.8, label="Median (ms)")

        min_row = sub.loc[sub["median_ms"].idxmin()]
        ax.scatter(
            [min_row["cutoff"]], [min_row["median_ms"]],
            color="red", s=70, zorder=5,
            label=f"Min Median: C={int(min_row['cutoff'])} ({min_row['median_ms']:.2f} ms)"
        )
        ax.set_title(f"{DIST_LABELS[dist]} (N = {max_n:,})", fontsize=11)
        ax.set_ylabel("Time (milliseconds)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8.5)

    axes[1, 0].set_xlabel("CUTOFF")
    axes[1, 1].set_xlabel("CUTOFF")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"{CHARTS_DIR}/chart1_time_vs_cutoff.png", dpi=220)
    plt.close()

    # Bieu do 2: So sanh thoi gian trung vi giua CUTOFF 0, 7, 10 va Best
    key_cutoffs = [0, 7, 10]
    if best_cutoff not in key_cutoffs:
        key_cutoffs.append(best_cutoff)

    colors_bar = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    x = np.arange(len(DIST_ORDER))
    width = 0.78 / len(key_cutoffs)

    all_vals_by_c = []
    for c in key_cutoffs:
        vals = [
            float(summary[(summary["distribution"] == d) & (summary["N"] == max_n) & (summary["cutoff"] == c)]["median_ms"].iloc[0])
            for d in DIST_ORDER
        ]
        all_vals_by_c.append(vals)
    global_max = max(max(v) for v in all_vals_by_c)

    fig, ax = plt.subplots(figsize=(11, 6))
    for idx, (c, vals) in enumerate(zip(key_cutoffs, all_vals_by_c)):
        lbl = f"CUTOFF = {c}"
        if c == 0:
            lbl += " (Baseline)"
        elif c == best_cutoff:
            lbl += " (Best Overall)"

        offset = (idx - (len(key_cutoffs) - 1) / 2) * width
        bars = ax.bar(x + offset, vals, width, label=lbl, color=colors_bar[idx % len(colors_bar)])
        for bar, v in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2, v + global_max * 0.015,
                f"{v:.1f}", ha="center", va="bottom", fontsize=8.8
            )

    ax.set_ylim(0, global_max * 1.15)
    ax.set_title(
        f"Biểu đồ 2: So sánh thời gian trung vị giữa các mốc CUTOFF (N = {max_n:,})",
        fontsize=12.5, fontweight="bold"
    )
    ax.set_xticks(x)
    ax.set_xticklabels([DIST_LABELS[d] for d in DIST_ORDER])
    ax.set_ylabel("Median Time (milliseconds)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig(f"{CHARTS_DIR}/chart2_compare_key_cutoffs.png", dpi=220)
    plt.close()

    # Bieu do 3: Speedup so voi CUTOFF = 0 + Geometric Mean (All Datasets)
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    for dist in DIST_ORDER:
        d_sub = (
            summary[summary["distribution"] == dist]
            .groupby("cutoff")["speedup_median"]
            .apply(gmean)
            .reset_index()
            .sort_values("cutoff")
        )