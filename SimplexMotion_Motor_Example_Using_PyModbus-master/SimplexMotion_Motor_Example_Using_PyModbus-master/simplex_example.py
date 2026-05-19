import time
from simplexMotor import SimplexMotor
import logging
import reg_map as regmap


logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s', 
    datefmt='%H:%M:%S'
)

logging.getLogger("pymodbus").setLevel(logging.WARNING)

motor = SimplexMotor(debug=True)

try:
    motor.connect() 

    motor.set_position(0) 

   
    print("Enabling Motor...")
    
    # motor.set_mode(regmap.MODE_POSITION_RAMP)
    motor.set_mode(regmap.MODE_SPEED_RAMP)
    # motor.set_mode(regmap.MODE_FREEWHEEL)
    while True:
        motor.get_register_value("RampSpeed", regmap.RAMP_SPEED)
        motor.get_register_value("TargetInput", regmap.TARGET_INPUT)
        try:
            str_in = input("Enter target position (degrees) or 'q' to quit: ")
            if str_in.lower() == 'q':
                break
            
            if int(str_in) > 10000:
                motor.get_register_value("Test", int(str_in)-10000)
                continue
                
            target_pos = float(str_in)
            target_speed = int(str_in)

            motor.set_target_speed(target_speed)
            time.sleep(0.5)
            motor.get_speed()

            # motor.set_position(target_pos)
            # time.sleep(0.5)
            # motor.get_position()
            
        except ValueError:
            print("Invalid number!")
        

finally:
    print("Disabling motor...")
    motor.set_mode(regmap.MODE_RESET) 
    motor.close()