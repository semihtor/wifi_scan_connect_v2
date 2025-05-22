# gpio_input_handler.py

from gpiozero import RotaryEncoder, Button
import config

# These will be set by the main script to functions that can alter main_app_state
# and call functions from other modules.
rotate_callback = None
click_callback = None
start_action_callback = None
stop_action_callback = None

encoder_instance = None
button_instance = None
start_switch_instance = None
stop_switch_instance = None


def setup_gpio(rotate_cb, click_cb, start_cb, stop_cb):
    """Sets up GPIO pins and event handlers."""
    global encoder_instance, button_instance, start_switch_instance, stop_switch_instance
    global rotate_callback, click_callback, start_action_callback, stop_action_callback

    rotate_callback = rotate_cb
    click_callback = click_cb
    start_action_callback = start_cb
    stop_action_callback = stop_cb

    try:
        encoder_instance = RotaryEncoder(a=config.ROTARY_ENCODER_A_GPIO, b=config.ROTARY_ENCODER_B_GPIO, max_steps=0)
        encoder_instance.when_rotated = internal_handle_rotation
        
        button_instance = Button(config.ROTARY_ENCODER_BUTTON_GPIO, pull_up=True, bounce_time=0.1)
        button_instance.when_pressed = internal_handle_click
        
        start_switch_instance = Button(config.START_BUTTON_GPIO, pull_up=True, bounce_time=0.2)
        start_switch_instance.when_pressed = start_action_callback # Directly call the main app's function
        
        stop_switch_instance = Button(config.STOP_BUTTON_GPIO, pull_up=True, bounce_time=0.2)
        stop_switch_instance.when_pressed = stop_action_callback # Directly call the main app's function
        
        print("GPIO setup complete.")
        return encoder_instance # Return encoder if needed by main for steps reset
    except Exception as e:
        print(f"ERROR: GPIO setup failed: {e}")
        return None

def internal_handle_rotation():
    if encoder_instance and rotate_callback:
        delta = round(encoder_instance.steps)
        encoder_instance.steps = 0  # Reset for the next delta
        if delta != 0:
            rotate_callback(delta)

def internal_handle_click():
    if click_callback:
        click_callback()

def cleanup_gpio():
    """Closes GPIO resources if necessary."""
    global encoder_instance, button_instance, start_switch_instance, stop_switch_instance
    if encoder_instance:
        encoder_instance.close()
    if button_instance:
        button_instance.close()
    if start_switch_instance:
        start_switch_instance.close()
    if stop_switch_instance:
        stop_switch_instance.close()
    print("GPIO resources closed.")