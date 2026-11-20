import os
import random

BASE_SEED = 25021967
SIZES = [1_000, 10_000, 100_000, 500_000]
DISTRIBUTIONS = ["random", "ascending", "descending", "duplicates"]


def make_array(dist: str, n: int):
    rng = random.Random(BASE_SEED + n)
    if dist == "random":
        return [rng.randint(0, 1_000_000_000) for _ in range(n)]
    if dist == "ascending":
        return list(range(n))
    if dist == "descending":
        return list(range(n, 0, -1))
    if dist == "duplicates":
        return [rng.randint(0, 15) for _ in range(n)]
    raise ValueError(f"Unknown distribution: {dist}")


def main():
    os.makedirs("data", exist_ok=True)
    for dist in DISTRIBUTIONS:
        for n in SIZES:
            filepath = os.path.join("data", f"{dist}_{n}.txt")
            arr = make_array(dist, n)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"{n}\n")
                f.write(" ".join(map(str, arr)) + "\n")
            print(f"Generated: {filepath}")


if __name__ == "__main__":
    main()
