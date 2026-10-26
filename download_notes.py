"""Download the public 15-122 lecture notes into ./data/lectures/."""
import os
import urllib.request

BASE = "https://www.cs.cmu.edu/~15122/handouts/lectures/"
LECTURES = [
    "01-contracts", "02-ints", "03-arrays", "04-linsearch", "05-bigo",
    "06-binsearch", "07-quicksort", "08-libraries",
    "09-stackqueue", "10-linkedlist", "11-uba", "12-hashing",
    "13-hdict", "14-generic", "15-bst", "16-avl", "17-cintro",
    "18-cmem", "19-cnum", "20-c0vm", "21-graphs", "22-dfs", "23-spanning",
    "24-unionfind", "25-pq", "26-heap",
]
OUT_DIR = os.path.join("data", "lectures")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in LECTURES:
        path = os.path.join(OUT_DIR, name + ".pdf")
        if os.path.exists(path):
            print(f"skip   {name} (already downloaded)")
            continue
        try:
            urllib.request.urlretrieve(BASE + name + ".pdf", path)
            print(f"got    {name}")
        except Exception as e:
            print(f"FAILED {name}: {e}")


if __name__ == "__main__":
    main()
