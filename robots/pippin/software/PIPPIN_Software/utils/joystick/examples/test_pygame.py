import pygame


def read_joystick():
    # Initialize Pygame
    pygame.init()

    # Initialize the joystick
    pygame.joystick.init()

    # Check for at least one joystick
    if pygame.joystick.get_count() == 0:
        print("No joystick connected!")
        return

    # Get the first joystick
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick initialized: {joystick.get_name()}")

    try:
        while True:
            # Pump Pygame's event system to read joystick events
            pygame.event.pump()

            # Read axes (e.g., analog stick positions)
            axis_data = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]

            # Read buttons (e.g., A, B, X, Y on a typical controller)
            button_data = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]

            # Read hats (e.g., D-pad positions)
            hat_data = [joystick.get_hat(i) for i in range(joystick.get_numhats())]

            # Print out the joystick state
            print(f"Axes: {axis_data}")
            print(f"Buttons: {button_data}")
            print(f"Hats: {hat_data}")

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # Clean up
        joystick.quit()
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    read_joystick()
