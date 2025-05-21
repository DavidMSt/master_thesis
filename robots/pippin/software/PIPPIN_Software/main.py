import time
import math
from robot.pippin import Pippin


def main():
    pippin = Pippin()
    pippin.start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
