import sys

from patron_arby.patron_arby import fib

if __name__ == "__main__":
    n = int(sys.argv[1])
    print(fib(n))
