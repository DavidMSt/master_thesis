import time

from robot.lib.xgolib import XGO


def main():
    xgo = XGO('xgorider')

    color = [0,0,155]
    xgo.rider_led(1, color=color)
    xgo.rider_led(2, color=color)
    xgo.rider_led(3, color=color)
    xgo.rider_led(4, color=color)

    # battery = xgo.rider_read_battery()
    # print("Battery: ", battery)

    # for i in range(0,15):
    #     xgo.rider_height(i*10)
    #     time.sleep(0.1)
    # # xgo.rider_height(1)
    # xgo.rider_move_x(0.1, 2)
    # xgo.rider_turn(-100,3)

    # xgo.turn_to(720)  # Moves a certain angle
    # print(xgo.read_motor())

    # xgo.unload_motor()
    # xgo.unload_allmotor()
    # xgo.imu(0)

    # xgo.action(1)
    # xgo.brute_force_unknown_commands(0.1)
    xgo.rider_reset()
    time.sleep(1)
    xgo.rider_move_x(0.75)
    time.sleep(1)
    xgo.rider_move_x(0)
    print("Done")
    # xgo.stop()
    # xgo.rider_move_x(0.75)
    # xgo.rider_turn(50)
    # time.sleep(2)
    # xgo.rider_move_x(0)
    # xgo.rider_turn(0)
    # print("Done")
    # time.sleep(3)



if __name__ == '__main__':
    main()

