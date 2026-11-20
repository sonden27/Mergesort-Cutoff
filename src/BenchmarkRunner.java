import java.io.BufferedInputStream;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Random;

public class BenchmarkRunner {

    private static final String[] DISTRIBUTIONS = {
        "random", "ascending", "descending", "duplicates"
    };
    private static final int[] SIZES = {1_000, 10_000, 100_000, 500_000};
    private static final int[] CUTOFFS = {
        0, 2, 4, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 64
    };
    private static final int TRIALS = 15;
    private static final int DATASET_WARMUP_ROUNDS = 2;

    private static class FastIntReader implements AutoCloseable {
        private final InputStream in;
        private final byte[] buf = new byte[1 << 16];
        private int ptr = 0;
        private int len = 0;

        FastIntReader(Path file) throws IOException {
            this.in = new BufferedInputStream(Files.newInputStream(file), 1 << 16);
        }

        private int readByte() throws IOException {
            if (ptr >= len) {
                len = in.read(buf);
                ptr = 0;
                if (len <= 0) return -1;
            }
            return buf[ptr++];
        }

        int nextInt() throws IOException {
            int c = readByte();
            while (c <= ' ' && c != -1) c = readByte();
            int sign = 1;
            if (c == '-') {
                sign = -1;
                c = readByte();
            }
            int val = 0;
            while (c > ' ') {
                val = val * 10 + (c - '0');
                c = readByte();
            }
            return val * sign;
        }

        @Override
        public void close() throws IOException {
            in.close();
        }
    }

    private static Integer[] loadDataset(Path file) throws IOException {
        try (FastIntReader reader = new FastIntReader(file)) {
            int n = reader.nextInt();
            Integer[] data = new Integer[n];
            for (int i = 0; i < n; i++) {
                data[i] = reader.nextInt();
            }
            return data;
        }
    }

    private static void globalJvmWarmup() {
        System.out.print("Dang chay JVM Warm-up (JIT Compilation)... ");
        Random rng = new Random(12345L);
        Integer[] base = new Integer[50_000];
        for (int i = 0; i < base.length; i++) {
            base[i] = rng.nextInt(1_000_000);
        }
        Integer[] work = new Integer[base.length];
        for (int round = 0; round < 2; round++) {
            for (int c : CUTOFFS) {
                System.arraycopy(base, 0, work, 0, base.length);
                Merge.sort(work, c);
            }
        }
        System.out.println("OK");
    }

    public static void main(String[] args) throws IOException {
        Path resultsDir = Paths.get("results");
        Files.createDirectories(resultsDir);
        Path outCsv = resultsDir.resolve("raw_results.csv");

        globalJvmWarmup();

        Random shuffleRng = new Random(25021967L);
        List<Integer> order = new ArrayList<>(CUTOFFS.length);
        for (int c : CUTOFFS) order.add(c);

        int totalConfigs = DISTRIBUTIONS.length * SIZES.length;
        int currentConfig = 0;

        try (BufferedWriter bw = Files.newBufferedWriter(outCsv)) {
            bw.write("distribution,N,cutoff,trial,time_ms\n");

            for (String dist : DISTRIBUTIONS) {
                for (int n : SIZES) {
                    currentConfig++;
                    Path dataFile = Paths.get("data", dist + "_" + n + ".txt");
                    Integer[] baseData = loadDataset(dataFile);
                    Integer[] work = new Integer[n];

                    System.out.printf("[%2d/%2d] Benchmarking %-10s | N = %7d ... ",
                            currentConfig, totalConfigs, dist, n);

                    for (int r = 0; r < DATASET_WARMUP_ROUNDS; r++) {
                        for (int c : CUTOFFS) {
                            System.arraycopy(baseData, 0, work, 0, n);
                            Merge.sort(work, c);
                        }
                    }

                    for (int trial = 1; trial <= TRIALS; trial++) {
                        Collections.shuffle(order, shuffleRng);
                        for (int c : order) {
                            System.arraycopy(baseData, 0, work, 0, n);

                            long t0 = System.nanoTime();
                            Merge.sort(work, c);
                            long t1 = System.nanoTime();

                            if (!Merge.isSorted(work)) {
                                throw new AssertionError(
                                    "Loi sap xep: dist=" + dist + ", N=" + n + ", cutoff=" + c
                                );
                            }

                            double elapsedMs = (t1 - t0) / 1_000_000.0;
                            bw.write(String.format(Locale.US, "%s,%d,%d,%d,%.6f%n",
                                    dist, n, c, trial, elapsedMs));
                        }
                    }

                    bw.flush();
                    System.out.println("OK");
                }
            }
        }

        System.out.println("Hoan tat benchmark! Ket qua luu tai: " + outCsv);
    }
}
