import pygame


class Logger:
    def __init__(self, file):
        self.file = file
        self.queue = []

    def export(self):
        with open(self.file, "w") as file:
            for line in self.queue:
                file.write(line + "\n")

    def log(self, text):
        print(text)
        self.queue.append(text)


def test_gamepad():
    # Open a window, the only purpose of which is to take the focus and let you use the keyboard.
    pygame.init()
    window = pygame.display.set_mode((100, 100))
    pygame.display.set_caption("Testing controller")
    window.fill((0, 0, 0))
    pygame.display.update()

    # Start the log.
    log = Logger("C:\\[YOUR FILE PATH HERE]\\controller_log.txt") # <-- PUT YOUR FILE PATH HERE.

    if pygame.joystick.get_count() <= 0:
        log.log("ERROR: No controller detected.")
    else:
        # Read from the first connected controller (in case you have more than one).
        gamepad = pygame.joystick.Joystick(0)

        # Log some controller metadata.
        log.log("Controller detected with:")
        log.log("\tnum_axis= " + str(gamepad.get_numaxes()))
        log.log("\tnum_hats= " + str(gamepad.get_numhats()))
        log.log("\tnum_buttons= " + str(gamepad.get_numbuttons()))

        # List the inputs to test. Please add more if I missed anything, or remove things if they don't exist.
        inputs_left = ["Left thumbstick up", "Left thumbstick down", "Left thumbstick right", "Left thumbstick left", "DPAD up", "DPAD down", "DPAD right", "DPAD left", "Left trigger", "Left bumper"]
        inputs_right = ["Right thumbstick up", "Right thumbstick down", "Right thumbstick right", "Right thumbstick left", "Button A", "Button B", "Button X", "Button Y", "Right trigger", "Right bumper"]

        # Filter out noise, since some controllers always give a tiny joystick value even if you aren't using it.
        JOYSTICK_TOLERANCE = 0.1

        # Test each of the specified inputs.
        for input in inputs_left + inputs_right:
            # Log the input.
            log.log("Input= " + input)
            logged = False
            while not logged:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        log.export()
                        pygame.quit()
                        exit()
                    elif event.type == pygame.JOYAXISMOTION and abs(gamepad.get_axis(event.axis)) > JOYSTICK_TOLERANCE:
                        log.log("\tAxis= " + str(event.axis) + ", value= " + str(gamepad.get_axis(event.axis)))
                        logged = True
                    elif event.type == pygame.JOYHATMOTION:
                        log.log("\tHat= " + str(event.hat) + ", value= " + str(gamepad.get_hat(event.hat)))
                        logged = True
                    elif event.type == pygame.JOYBUTTONDOWN:
                        log.log("\tButton pressed= " + str(event.button))
                        logged = True

            # Wait to continue, since otherwise the input is read too fast to move your hand.
            print("Press [SPACE BAR] to continue")
            wait = True
            while wait:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        exit()
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        wait = False

    # Close everything and export.
    pygame.quit()
    log.log("Testing complete")
    log.export()

# Run the function.
test_gamepad()
