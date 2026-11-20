import json
import os
import urllib.parse

import numpy as np
import pandas as pd

STUDENT_NAME = "Bùi Ngọc Sơn"
STUDENT_ID = "25021967"
STUDENT_CLASS = "K70I-CS2"
COURSE_CODE = "2627I_UET.CS1058_9"


def badge(label, message, color):
    l_enc = urllib.parse.quote(str(label))
    m_enc = urllib.parse.quote(str(message))
    return f"![{label}](https://img.shields.io/badge/{l_enc}-{m_enc}-{color})"


def main():
    os.makedirs("report", exist_ok=True)
    with open("results/machine.json", "r", encoding="utf-8") as f:
        m = json.load(f)

    summary = pd.read_csv("results/summary_stats.csv")
    ranking = pd.read_csv("results/overall_ranking.csv")

    best_row = ranking.iloc[0]
    second_row = ranking.iloc[1]
    best_c = int(best_row["cutoff"])
    second_c = int(second_row["cutoff"])

    r7 = ranking[ranking["cutoff"] == 7].iloc[0]
    r10 = ranking[ranking["cutoff"] == 10].iloc[0]
    diff_10_vs_7 = (r10["gmean_speedup_median"] / r7["gmean_speedup_median"] - 1.0) * 100.0
    max_n = int(summary["N"].max())

    # 1. Bang xep hang tong the (Top 10 + moc 7, 10, 0)
    show_ranks = set(ranking.head(10)["cutoff"].tolist() + [7, 10, 0])
    rank_sub = ranking[ranking["cutoff"].isin(show_ranks)]

    rank_rows = []
    for _, row in rank_sub.iterrows():
        c = int(row["cutoff"])
        c_label = f"**{c}**" if c in (best_c, 7, 10) else ("0 (Baseline)" if c == 0 else str(c))
        gm_med = f"**{row['gmean_speedup_median']:.4f}x**" if c in (best_c, 7, 10) else f"{row['gmean_speedup_median']:.4f}x"
        gm_mean = f"{row['gmean_speedup_mean']:.4f}x"
        rank_rows.append(
            f"| {int(row['rank'])} | {c_label} | {gm_med} | {gm_mean} | {row['mean_norm_median']:.4f} | {row['avg_cv_pct']:.2f}% |"
        )
    rank_table = "\n".join(rank_rows)

    # 2. Bang so sanh tai N lon nhat
    comp_rows = []
    for dist in ["ascending", "descending", "duplicates", "random"]:
        def get_med(c):
            return float(summary[(summary["distribution"] == dist) & (summary["N"] == max_n) & (summary["cutoff"] == c)]["median_ms"].iloc[0])

        t0, t7, t10, tb = get_med(0), get_med(7), get_med(10), get_med(best_c)
        sp = t0 / tb
        comp_rows.append(
            f"| `{dist}` | {t0:.3f} | {t7:.3f} | {t10:.3f} | **{tb:.3f}** | **{sp:.3f}x** |"
        )
    comp_table = "\n".join(comp_rows)

    # 3. Kiem chung bac tang truong Log-Log (Random)
    rand_base = summary[(summary["distribution"] == "random") & (summary["cutoff"] == 0)].sort_values("N")
    rand_best = summary[(summary["distribution"] == "random") & (summary["cutoff"] == best_c)].sort_values("N")
    slope_base = np.polyfit(np.log2(rand_base["N"]), np.log2(rand_base["median_ms"]), 1)[0]
    slope_best = np.polyfit(np.log2(rand_best["N"]), np.log2(rand_best["median_ms"]), 1)[0]

    growth_rows = []
    for (_, rb), (_, ro) in zip(rand_base.iterrows(), rand_best.iterrows()):
        growth_rows.append(
            f"| {int(rb['N']):,} | {rb['median_ms']:.4f} | {ro['median_ms']:.4f} | {rb['median_ms']/ro['median_ms']:.3f}x |"
        )
    growth_table = "\n".join(growth_rows)

    javac_short = m["javac"].replace("javac ", "")
    badges = " ".join([
        badge("Java", javac_short, "ED8B00"),
        badge("JVM", m["jvm_flags"], "444444"),
        badge("Python", m["python"], "3776AB"),
        badge("Pandas", m["pandas"], "150458"),
        badge("NumPy", m["numpy"], "013243"),
        badge("Matplotlib", m["matplotlib"], "11557C"),
    ])

    readme_content = f"""# MergeSort CUTOFF — Experimental Benchmark & Analysis (Java)

{badges}

- **Họ và tên:** {STUDENT_NAME}
- **Mã sinh viên:** {STUDENT_ID}
- **Lớp:** {STUDENT_CLASS}
- **Học phần:** {COURSE_CODE}

Nghiên cứu thực nghiệm tìm giá trị `CUTOFF` tối ưu (ngưỡng chuyển sang **Insertion Sort** cho mảng con kích thước nhỏ) trong thuật toán **MergeSort** xây dựng bằng Java đúng theo giáo trình *Algorithms, 4th Edition* (`src/Merge.java` và `src/Insertion.java`), đồng thời kiểm chứng hai mốc kinh điển `CUTOFF = 7` (Java 6 / giáo trình cũ) và `CUTOFF = 10` (giáo trình mới).

---

## 1. Thiết kế & Môi trường thí nghiệm

### Cấu hình máy thực nghiệm (`results/machine.txt`)
- **Hệ điều hành:** {m['os']}
- **CPU:** {m['cpu']}
- **RAM:** {m['ram']}
- **Java Runtime:** `{m['java']}`
- **Java Compiler & JVM Flags:** `{m['javac']}` với `{m['jvm_flags']}`
- **Python:** {m['python']} (`pandas` {m['pandas']}, `numpy` {m['numpy']}, `matplotlib` {m['matplotlib']})

### Phương pháp đo
- **17 giá trị CUTOFF:** `0, 2, 4, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 64` (với `CUTOFF = 0` là MergeSort thuần túy làm baseline).
- **4 kích thước mảng ($N$):** `1,000`, `10,000`, `100,000`, `500,000`.
- **4 phân bố dữ liệu (seed cố định `25021967 + n`):** `random`, `ascending` (tăng dần), `descending` (giảm dần), `duplicates` (16 giá trị lặp).
- **Quy trình kiểm soát nhiễu:** Chạy **JVM Warm-up toàn cục** kích hoạt JIT Compiler (C2) và 2 vòng warm-up trước mỗi tập dữ liệu; cố định Heap `-Xms2g -Xmx4g` giảm dừng GC; lặp **15 lần** mỗi cấu hình (tổng cộng **4,080 lượt đo thô**); xáo trộn ngẫu nhiên thứ tự `CUTOFF` ở mỗi vòng; sao chép mảng bằng `System.arraycopy` ngoài vùng đo `System.nanoTime()`; kiểm chứng `Merge.isSorted()` sau mỗi lượt chạy.

---

## 2. Kết quả thực nghiệm

### Bảng xếp hạng tổng thể (Geometric Mean Speedup trên 16 bộ dữ liệu)

| Hạng | CUTOFF | Geometric Mean Speedup (Median) | Geometric Mean Speedup (Mean) | Mean Normalized Median | CV trung bình (%) |
| :---: | :---: | :---: | :---: | :---: | :---: |
{rank_table}

### So sánh tại kích thước lớn nhất ($N = {max_n:,}$)

| Dạng dữ liệu | CUTOFF = 0 (ms) | CUTOFF = 7 (ms) | CUTOFF = 10 (ms) | CUTOFF = {best_c} (ms) | Speedup ({best_c} vs 0) |
| :--- | :---: | :---: | :---: | :---: | :---: |
{comp_table}

*(Giá trị trong bảng là thời gian trung vị `median_ms` qua 15 lần đo.)*

### Kết luận chính
- **CUTOFF tối ưu:** Trên cấu hình máy thử nghiệm với JVM hiện tại, `CUTOFF = {best_c}` đạt hiệu năng tổng hợp cao nhất (**{best_row['gmean_speedup_median']:.3f}x**, CV trung bình {best_row['avg_cv_pct']:.2f}%), tiếp sát theo sau là `CUTOFF = {second_c}` (**{second_row['gmean_speedup_median']:.3f}x**, CV {second_row['avg_cv_pct']:.2f}%).
- **So sánh mốc giáo trình 7 và 10:** Tổng thể `CUTOFF = 10` ({r10['gmean_speedup_median']:.3f}x) chênh lệch **{diff_10_vs_7:+.2f}%** so với `CUTOFF = 7` ({r7['gmean_speedup_median']:.3f}x). Cả hai mốc đều cải thiện rõ rệt so với MergeSort thuần túy (`CUTOFF = 0`).

---

## 3. Biểu đồ trực quan

### Biểu đồ 1: Thời gian chạy trung bình và trung vị theo CUTOFF ($N = {max_n:,}$)
![Biểu đồ 1](results/charts/chart1_time_vs_cutoff.png)

### Biểu đồ 2: So sánh các mốc CUTOFF chính ($N = {max_n:,}$)
![Biểu đồ 2](results/charts/chart2_compare_key_cutoffs.png)

### Biểu đồ 3: Speedup so với MergeSort cơ bản (CUTOFF = 0)
![Biểu đồ 3](results/charts/chart3_speedup_overview.png)

### Biểu đồ 4: Ảnh hưởng của kích thước mảng $N$ (Dữ liệu Random)
![Biểu đồ 4](results/charts/chart4_size_impact.png)

### Biểu đồ 5: Phân bố và độ biến động thời gian chạy (Random, $N = {max_n:,}$)
![Biểu đồ 5](results/charts/chart5_boxplot_variability.png)

---

## 4. Hướng dẫn tái lập thí nghiệm

Cài đặt JDK 17+ và Python 3, sau đó chạy lệnh duy nhất tại thư mục gốc:

```bat
reproduce.bat
```
"""

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    report_content = f"""# BÁO CÁO THÍ NGHIỆM: KHẢO SÁT GIÁ TRỊ CUTOFF TỐI ƯU CHO THUẬT TOÁN MERGESORT (JAVA)

- **Sinh viên thực hiện:** {STUDENT_NAME}
- **Mã sinh viên:** {STUDENT_ID}
- **Lớp:** {STUDENT_CLASS}
- **Học phần:** {COURSE_CODE}

---

## 1. Đặt vấn đề và Cơ sở lý thuyết

Theo giáo trình *Algorithms, 4th Edition* (Robert Sedgewick & Kevin Wayne, Chương 2.2), cài đặt MergeSort top-down chuẩn trên mảng `Comparable[]` đảm bảo tối đa $N \\lg N$ phép so sánh, tối đa $6N \\lg N$ phép truy cập mảng, sử dụng bộ nhớ phụ tỉ lệ với $N$ (`aux[]`) và có tính **ổn định (stable)**. Tuy nhiên, việc chia đệ quy xuống tận các mảng con kích thước rất nhỏ sinh ra chi phí gọi đệ quy và sao chép mảng phụ đáng kể.

Một cải tiến thực tiễn chung cho cả **Mergesort** (Chương 2.2) và **Quicksort** (Chương 2.3) là chuyển sang dùng **Insertion Sort** khi kích thước mảng con không vượt quá ngưỡng `CUTOFF`:

```java
if (hi <= lo + CUTOFF - 1) {{
    Insertion.sort(a, lo, hi);
    return;
}}
```

Do cả `Insertion.sort` và thao tác `merge` (ưu tiên lấy phần tử nửa trái khi khóa bằng nhau) đều ổn định, phiên bản MergeSort kết hợp `CUTOFF` vẫn bảo toàn tính ổn định của thuật toán gốc. Các ấn bản giáo trình nhắc đến những mốc khác nhau:
- **`CUTOFF = 7`:** Mốc kinh điển dùng trong bộ sắp xếp hệ thống Java 6 (`Arrays.sort` cho kiểu đối tượng).
- **`CUTOFF ≈ 10`:** Mốc khuyến nghị trong phiên bản bài giảng mới cho cả Mergesort và Quicksort (bên cạnh minh họa với `cutoff = 12`).

Bởi hiệu năng thực tế chịu tác động mạnh từ kiến trúc bộ nhớ đệm (CPU cache) và trình biên dịch JIT trên từng máy, thí nghiệm này tiến hành đo đạc thực nghiệm để tìm giá trị `CUTOFF` tối ưu cho cấu hình máy cá nhân.

---

## 2. Thiết kế thí nghiệm (Áp dụng Chủ đề 1.3 — Algorithm Analysis)

### 2.1. Cấu hình phần cứng và phần mềm
- **Hệ điều hành:** {m['os']}
- **CPU:** {m['cpu']}
- **RAM:** {m['ram']}
- **Java Runtime:** `{m['java']}`
- **Java Compiler & JVM Flags:** `{m['javac']}` (`{m['jvm_flags']}`)
- **Môi trường phân tích:** Python {m['python']} (`pandas` {m['pandas']}, `numpy` {m['numpy']}, `matplotlib` {m['matplotlib']})

### 2.2. Cài đặt thuật toán theo nội dung bài giảng (`src/Merge.java`, `src/Insertion.java`)
- Dựng đầy đủ 2 lớp `Insertion` và `Merge` trên kiểu `Comparable[]` với các phương thức `less()`, `exch()`, `merge()` và `sort()` khớp hoàn toàn với mã nguồn trong bài giảng 2.2.
- **Cô lập biến thí nghiệm:** Giáo trình 2.2 còn đề cập 2 cải tiến thực tiễn khác là *dừng sớm nếu mảng đã có thứ tự* (`if (!less(a[mid+1], a[mid])) return;`) và *đảo vai trò `a`/`aux` để bỏ bước sao chép*. Trong thí nghiệm này, hai cải tiến đó **không được gộp vào** nhằm đánh giá độc lập tác động thuần túy của `CUTOFF` (tránh làm triệt tiêu bước trộn trên tập `ascending` hoặc làm thay đổi bản chất chi phí của mảng con nhỏ).
- **Mốc đối chiếu (Baseline):** `CUTOFF = 0` tương ứng với MergeSort thuần túy (chỉ dừng tại `hi <= lo`, không gọi `Insertion.sort`).

### 2.3. Không gian dữ liệu và quy trình kiểm soát sai số trên JVM
- **17 mức `CUTOFF`:** `0, 2, 4, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 64`.
- **4 kích thước $N$:** `1,000`, `10,000`, `100,000`, `500,000`.
- **4 phân bố (seed cố định `25021967 + n`):** `random`, `ascending`, `descending`, `duplicates` (16 giá trị duy nhất).
- **Chống nhiễu đo đạc:**
  1. Thực hiện **JVM Warm-up toàn cục** (mảng 50,000 phần tử qua 17 mức) kết hợp 2 vòng warm-up riêng cho từng tập dữ liệu nhằm kích hoạt tối ưu hóa JIT (C2) trước khi ghi nhận số liệu.
  2. Cấp phát bộ nhớ Heap cố định (`{m['jvm_flags']}`) để hạn chế Garbage Collector tạm dừng giữa phép đo.
  3. Lặp $T = 15$ lần cho mỗi cấu hình (tổng $4 \\times 4 \\times 17 \\times 15 = 4{{,}}080$ lượt đo); xáo trộn ngẫu nhiên thứ tự 17 mức `CUTOFF` ở từng vòng để tránh thiên lệch nhiệt độ CPU.
  4. Sao chép mảng đầu vào bằng `System.arraycopy` ngoài vùng đo `System.nanoTime()` và xác minh `Merge.isSorted()` sau từng lượt.
  5. Tổng hợp bằng **Trung vị (`median_ms`)**, **Trung bình nhân tốc độ (`Geometric Mean Speedup`)** và **Hệ số biến thiên (`CV%`)** để giảm tác động của các outlier từ hệ điều hành hoặc GC.

---

## 3. Kết quả thực nghiệm và Thống kê

### 3.1. Xếp hạng tổng hợp trên toàn bộ 16 bộ dữ liệu

| Hạng | CUTOFF | Geometric Mean Speedup (Median) | Geometric Mean Speedup (Mean) | Mean Normalized Median | CV trung bình (%) |
| :---: | :---: | :---: | :---: | :---: | :---: |
{rank_table}

### 3.2. Chi tiết thời gian trung vị tại $N = {max_n:,}$

| Dạng dữ liệu | CUTOFF = 0 (ms) | CUTOFF = 7 (ms) | CUTOFF = 10 (ms) | CUTOFF = {best_c} (ms) | Speedup ({best_c} vs 0) |
| :--- | :---: | :---: | :---: | :---: | :---: |
{comp_table}

### 3.3. Kiểm chứng bậc tăng trưởng theo kích thước mảng $N$ (Dữ liệu `random`)

| Kích thước $N$ | Median CUTOFF = 0 (ms) | Median CUTOFF = {best_c} (ms) | Speedup |
| :---: | :---: | :---: | :---: |
{growth_table}

Hệ số góc ước lượng trên đồ thị Log-Log ($\\log_2 T(N)$ theo $\\log_2 N$):
- **CUTOFF = 0 (Baseline):** $\\text{{slope}} \\approx {slope_base:.3f}$
- **CUTOFF = {best_c} (Tối ưu):** $\\text{{slope}} \\approx {slope_best:.3f}$

### 3.4. Hệ thống biểu đồ trực quan

![Biểu đồ 1](../results/charts/chart1_time_vs_cutoff.png)
![Biểu đồ 2](../results/charts/chart2_compare_key_cutoffs.png)
![Biểu đồ 3](../results/charts/chart3_speedup_overview.png)
![Biểu đồ 4](../results/charts/chart4_size_impact.png)
![Biểu đồ 5](../results/charts/chart5_boxplot_variability.png)

---

## 4. Phân tích và Thảo luận

1. **Hiệu quả của CUTOFF và đường cong chữ U:** Ở các phân bố `random`, `descending` và `duplicates`, thời gian chạy giảm rõ khi tăng `CUTOFF` rời khỏi `0` nhờ triệt tiêu hàng trăm nghìn lời gọi đệ quy và thao tác sao chép mảng phụ `aux[]` kích thước nhỏ. Khi `CUTOFF` tiến về `40..64`, chi phí $O(k^2)$ của Insertion Sort (đặc biệt trên `Comparable[]` với các phép `exch()` đổi chỗ từng cặp) tăng mạnh, kéo hiệu năng đi xuống.
2. **Ảnh hưởng của đặc trưng dữ liệu đầu vào:**
   - `ascending`: Insertion Sort chỉ tốn đúng 1 phép so sánh cho mỗi phần tử ($O(k)$) và tránh được toàn bộ chi phí sao chép `aux[]`, nên `CUTOFF` càng lớn càng nhanh.
   - `descending`: Insertion Sort rơi vào trường hợp xấu nhất ($\\sim k^2/2$ phép so sánh và hoán đổi), khiến thời gian tăng nhanh ngay khi vượt qua ngưỡng nhỏ.
   - `duplicates` và `random`: phản ánh rõ điểm cân bằng thực tế giữa giảm chi phí đệ quy và chi phí sắp xếp chèn cục bộ trong cache CPU.
3. **Độ ổn định trên JVM (Boxplot & CV%):** Biểu đồ 5 cho thấy phần lớn lượt đo tập trung sát trung vị, trong khi một vài điểm ngoại lai phía trên đến từ tác vụ nền hoặc GC. Việc đánh giá bằng `median_ms` kết hợp `Geometric Mean Speedup` giúp xếp hạng khách quan hơn so với trung bình cộng đơn thuần.
4. **Tác động tới bậc tăng trưởng tiệm cận:** Hệ số góc trên đồ thị Log-Log (Biểu đồ 4) giữa `CUTOFF = 0` ({slope_base:.3f}) và `CUTOFF = {best_c}` ({slope_best:.3f}) gần như tương đương nhau. Cải tiến `CUTOFF` giúp **giảm hằng số nhân** (dịch đường cong xuống dưới) nhưng giữ nguyên độ phức tạp tiệm cận $\\Theta(N \\log N)$.

---

## 5. Kết luận

Trên cấu hình thử nghiệm ({m['cpu']}, `{m['javac']}`), cải tiến **CUTOFF** cho cài đặt MergeSort chuẩn bài giảng giúp đạt mức tăng tốc tổng thể **{best_row['gmean_speedup_median']:.3f}x** tại **`CUTOFF = {best_c}`** (kế tiếp là `CUTOFF = {second_c}` đạt **{second_row['gmean_speedup_median']:.3f}x**). Hai mốc giáo trình `7` và `10` đều mang lại cải thiện rõ rệt so với bản gốc, trong đó `CUTOFF = 10` chênh lệch {diff_10_vs_7:+.2f}% so với `CUTOFF = 7`.
"""

    with open("report/BaoCao_MergeSort_Cutoff.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    print("Da cap nhat thanh cong README.md va report/BaoCao_MergeSort_Cutoff.md")


if __name__ == "__main__":
    main()
