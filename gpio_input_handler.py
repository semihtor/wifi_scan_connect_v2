# gpio_input_handler.py

from gpiozero import RotaryEncoder, Button
import config

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
        start_switch_instance.when_pressed = start_action_callback
        
        stop_switch_instance = Button(config.STOP_BUTTON_GPIO, pull_up=True, bounce_time=0.2)
        stop_switch_instance.when_pressed = stop_action_callback
        
        print("GPIO setup complete.")
        return encoder_instance 
    except Exception as e:
        print(f"ERROR: GPIO setup failed: {e}")
        return None

def internal_handle_rotation():
    if encoder_instance and rotate_callback:
        delta = round(encoder_instance.steps)
        encoder_instance.steps = 0 
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
        encoder_instance = None
    if button_instance:
        button_instance.close()
        button_instance = None
    if start_switch_instance:
        start_switch_instance.close()
        start_switch_instance = None
    if stop_switch_instance:
        stop_switch_instance.close()
        stop_switch_instance = None
    print("GPIO resources closed.")
