

import time
from robot.lib.xgoedu import XGOEDU

# Minimum example: press button A to take a photo and display it on the LCD

def main():
    # Initialize the robot display and camera
    robot = XGOEDU()

    # Start camera preview on LCD
    robot.xgoCamera(True)

    try:
        while True:
            # When button A is pressed, take a photo and display it
            if robot.xgoButton("a"):  # "a" corresponds to the upper-left key
                robot.xgoTakePhoto("photo")  # Saves photo.jpg and shows it on the screen
                print("Took Photo")

            # Optional: Press button C to exit camera mode
            if robot.xgoButton("c"):  # "c" corresponds to the lower-left key
                robot.xgoCamera(False)
                break

            # Debounce and reduce CPU usage
            time.sleep(0.1)

    except KeyboardInterrupt:
        # Ensure camera preview stops on interrupt
        robot.xgoCamera(False)


if __name__ == "__main__":
    main()