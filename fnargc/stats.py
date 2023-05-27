#!/usr/bin/env python3

import sys


def histogram(counts: [int]) -> {}:
    hist = {}

    for c in counts:
        if c in hist:
            hist[c] += 1
        else:
            hist[c] = 1

    return hist


def main():
    input_file = sys.argv[1]

    arg_counts = []
    with open(input_file, "r") as f:
        while True:
            line = f.readline()
            if not line:
                break
            argc = line.split(",")[1]
            arg_counts.append(int(argc))

    arg_counts.sort()

    total = len(arg_counts)
    hist = histogram(arg_counts)

    print("total no. of funcs:", total)

    print("")

    print("breakdown by no. of args:")
    for k, v in hist.items():
        percent = (v / total) * 100
        print(f"  {k} args\t{v}\t{percent:.2f}%")

    print("")

    print("what percentage of funcs have?")
    print("  3 or less args\t%.2f%%" % (percentage_for_argc(3, total, hist)))
    print("  4 or less args\t%.2f%%" % (percentage_for_argc(4, total, hist)))
    print("  5 or less args\t%.2f%%" % (percentage_for_argc(5, total, hist)))
    print("  6 or less args\t%.2f%%" % (percentage_for_argc(6, total, hist)))
    print("  7 or less args\t%.2f%%" % (percentage_for_argc(7, total, hist)))
    print("  8 or less args\t%.2f%%" % (percentage_for_argc(8, total, hist)))


def percentage_for_argc(argc: int, total: int, hist: {}) -> float:
    sum = 0
    for i in range(1, argc + 1):
        if i in hist:
            sum += hist[i]
    return (sum / total) * 100


if __name__ == "__main__":
    main()
