import os
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAW_CSV = "results/raw_results.csv"
SUMMARY_CSV = "results/summary_stats.csv"
RANKING_CSV = "results/overall_ranking.csv"
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

    best_cutoff = int(ranking.iloc[0]["cutoff"])
    best_gmean = float(ranking.iloc[0]["gmean_speedup_median"])
    max_n = int(summary["N"].max())

    print("=== BANG XEP HANG TOP 10 CUTOFF ===")
    print(ranking.head(10).to_string(index=False))

    # Bieu do 1: Thoi gian chay Mean & Median theo CUTOFF (2x2, N lon nhat)
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    fig.suptitle(
        f"Biểu đồ 1: Thời gian chạy trung bình và trung vị theo CUTOFF (N = {max_n:,})",
        fontsize=13, fontweight="bold"
    )
    for ax, dist in zip(axes.flat, DIST_ORDER):
        sub = summary[(summary["distribution"] == dist) & (summary["N"] == max_n)].sort_values("cutoff")
        ax.plot(sub["cutoff"], sub["mean_ms"], "-o", markersize=5, label="Mean (ms)")
        ax.plot(sub["cutoff"], sub["median_ms"], "--s", markersize=4.5, label="Median (ms)")

        min_row = sub.loc[sub["mean_ms"].idxmin()]
        ax.scatter(
            [min_row["cutoff"]], [min_row["mean_ms"]],
            color="red", s=65, zorder=5,
            label=f"Min Mean: C={int(min_row['cutoff'])} ({min_row['mean_ms']:.2f} ms)"
        )
        ax.set_title(f"{DIST_LABELS[dist]} (N = {max_n:,})", fontsize=11)
        ax.set_ylabel("Time (milliseconds)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

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

    fig, ax = plt.subplots(figsize=(11, 6))
    for idx, c in enumerate(key_cutoffs):
        vals = [
            float(summary[(summary["distribution"] == d) & (summary["N"] == max_n) & (summary["cutoff"] == c)]["median_ms"].iloc[0])
            for d in DIST_ORDER
        ]
        lbl = f"CUTOFF = {c}"
        if c == 0:
            lbl += " (Baseline)"
        elif c == best_cutoff:
            lbl += " (Best)"

        offset = (idx - (len(key_cutoffs) - 1) / 2) * width
        bars = ax.bar(x + offset, vals, width, label=lbl, color=colors_bar[idx % len(colors_bar)])
        for bar, v in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2, v + max(vals) * 0.015,
                f"{v:.1f}", ha="center", va="bottom", fontsize=9
            )

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
        ax.plot(
            d_sub["cutoff"], d_sub["speedup_median"],
            marker="o", markersize=3.5, linewidth=1.6, alpha=0.75, label=DIST_LABELS[dist]
        )

    gm_sorted = ranking.sort_values("cutoff")
    ax.plot(
        gm_sorted["cutoff"], gm_sorted["gmean_speedup_median"],
        color="black", marker="o", markersize=5, linewidth=2.4,
        label="Geometric Mean (All Datasets)"
    )
    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1.2, label="Baseline (CUTOFF = 0, 1.00x)")
    ax.scatter([best_cutoff], [best_gmean], color="red", s=70, zorder=6)
    ax.annotate(
        f"Best: C={best_cutoff} ({best_gmean:.3f}x)",
        xy=(best_cutoff, best_gmean),
        xytext=(min(best_cutoff + 4, 48), best_gmean + 0.08),
        color="red", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="red", lw=1.2)
    )

    ax.set_title(
        "Biểu đồ 3: Speedup so với MergeSort cơ bản (CUTOFF = 0) trên các dạng dữ liệu",
        fontsize=12.5, fontweight="bold"
    )
    ax.set_xlabel("CUTOFF")
    ax.set_ylabel("Speedup = T(CUTOFF=0) / T(CUTOFF=k)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(f"{CHARTS_DIR}/chart3_speedup_overview.png", dpi=220)
    plt.close()

    # Bieu do 4: Anh huong kich thuoc mang N (Random, 1x2 Log-Log & Speedup)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.2))
    fig.suptitle(
        "Biểu đồ 4: Ảnh hưởng của kích thước mảng N đến hiệu năng (Dữ liệu Random)",
        fontsize=12.5, fontweight="bold"
    )
    rand_df = summary[summary["distribution"] == "random"]

    for idx, c in enumerate(key_cutoffs):
        sub = rand_df[rand_df["cutoff"] == c].sort_values("N")
        lbl = f"CUTOFF = {c}" + (" (Best)" if c == best_cutoff and c != 0 else "")
        color = colors_bar[idx % len(colors_bar)]

        ax1.loglog(sub["N"], sub["median_ms"], "-o", color=color, linewidth=1.8, label=lbl)
        ax2.semilogx(sub["N"], sub["speedup_median"], "-o", color=color, linewidth=1.8, label=lbl)

    ax1.set_title("Thời gian chạy theo kích thước N (Random)")
    ax1.set_xlabel("Array Size N (log scale)")
    ax1.set_ylabel("Median Time (milliseconds, log scale)")
    ax1.grid(True, which="both", alpha=0.3)
    ax1.legend(fontsize=9)

    ax2.set_title("Speedup theo kích thước N (Random)")
    ax2.set_xlabel("Array Size N (log scale)")
    ax2.set_ylabel("Speedup vs CUTOFF = 0")
    ax2.grid(True, which="both", alpha=0.3)
    ax2.legend(fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig(f"{CHARTS_DIR}/chart4_size_impact.png", dpi=220)
    plt.close()

    # Bieu do 5: Boxplot phan bo va do bien dong qua 15 lan do (Random, max N)
    raw_sub = df[(df["distribution"] == "random") & (df["N"] == max_n)]
    cutoffs_sorted = sorted(raw_sub["cutoff"].unique())
    box_data = [raw_sub[raw_sub["cutoff"] == c]["time_ms"].values for c in cutoffs_sorted]

    fig, ax = plt.subplots(figsize=(13, 6))
    bp = ax.boxplot(box_data, patch_artist=True)
    ax.set_xticklabels([str(c) for c in cutoffs_sorted])

    for patch, c in zip(bp["boxes"], cutoffs_sorted):
        if c == 0:
            patch.set_facecolor("#d3d3d3")
        elif c == best_cutoff:
            patch.set_facecolor("#ff9999")
        elif c in (7, 10):
            patch.set_facecolor("#99ccff")
        else:
            patch.set_facecolor("#e8f4ff")

    ax.set_title(
        f"Biểu đồ 5: Phân bố và độ biến động thời gian chạy qua 15 lần đo (Random, N = {max_n:,})",
        fontsize=12.5, fontweight="bold"
    )
    ax.set_xlabel("CUTOFF")
    ax.set_ylabel("Execution Time (milliseconds)")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{CHARTS_DIR}/chart5_boxplot_variability.png", dpi=220)
    plt.close()

    print(f"Da xuat 5 bieu do vao {CHARTS_DIR}/ va luu thong ke CSV thanh cong!")


if __name__ == "__main__":
    main()
