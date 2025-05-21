import time
from PIL import Image
from robot.lib.LCD_2inch import LCD_2inch


def main():
    # 1. Instantiate & initialize
    lcd = LCD_2inch()
    lcd.Init()

    # 2. Load an image (make sure it’s not larger than 240×320)
    img = Image.open('../../../../robot/lib/imes.png')
    img = img.resize((lcd.height, lcd.width))  # rotate if you like

    # 3. Show it
    lcd.ShowImage(img)
    print("Image displayed. Waiting 5 seconds...")
    time.sleep(50000)

    # 4. Clear the screen (white)
    lcd.clear()
    print("Screen cleared. Exiting.")


if __name__ == '__main__':
    main()
