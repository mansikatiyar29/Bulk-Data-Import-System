"""
generate_large_dataset.py

Generate a large CSV dataset to demonstrate how bulk_create() scales.

Usage:
    python generate_large_dataset.py            # default 10,000 records
    python generate_large_dataset.py 10000      # explicit
    python generate_large_dataset.py 50000      # any number you like

The generated file (large_dataset.csv) contains unique emails so the entire
file imports successfully -- perfect for benchmarking bulk_insertion.
"""
import random
import sys


def make_email(index):
    """Produce a unique, valid email."""
    return f"student{index:06d}@example.com"


def make_phone():
    """Produce a valid Indian 10-digit mobile number starting with 6-9."""
    return f"{random.randint(6, 9)}{random.randint(10**8, 10**9 - 1)}"


def make_name(index):
    """Produce a random full name."""
    first = random.choice(["Aarav", "Ananya", "Ishaan", "Priya", "Vivaan",
                           "Diya", "Arjun", "Sneha", "Karan", "Meera"])
    last = random.choice(["Sharma", "Verma", "Iyer", "Nair", "Patel",
                          "Gupta", "Singh", "Reddy", "Joshi", "Kapoor"])
    return f"{first} {last} {index % 500}"


def make_row(i):
    return [
        make_name(i),
        make_email(i),
        make_phone(),
        str(random.randint(5, 60)),
        random.choice(["Mumbai", "Delhi", "Bengaluru", "Hyderabad",
                       "Ahmedabad", "Chennai", "Kolkata", "Pune", "Jaipur", "Kochi"]),
        random.choice(["Maharashtra", "Delhi", "Karnataka", "Telangana",
                       "Gujarat", "Tamil Nadu", "West Bengal", "Rajasthan", "Kerala"]),
    ]


HEADER = "name,email,phone,age,city,state"


def main():
    count = 10000
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
            if count <= 0:
                raise ValueError
        except ValueError:
            print("Please provide a positive integer, e.g.  python generate_large_dataset.py 10000")
            sys.exit(1)

    filename = "large_dataset.csv"
    print(f"Generating {count:,} records ...")

    with open(filename, "w", newline="", encoding="utf-8") as f:
        f.write(HEADER + "\n")
        for i in range(count):
            f.write(",".join(make_row(i)) + "\n")

    print(f"Done! File written to '{filename}' with {count:,} rows.")


if __name__ == "__main__":
    main()