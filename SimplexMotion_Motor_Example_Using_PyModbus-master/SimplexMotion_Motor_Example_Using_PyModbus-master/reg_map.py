# Register map for Simplex Motor Controller (SC series)

# ==========================================
#  Register Addresses 
# ==========================================
MOTOR_POSTITION             = 199        
MOTOR_SPEED                 = 201
MOTOR_TORQUE                = 202
MOTOR_TORQUE_MAX            = 203
MOTOR_TORQUE_STOP           = 204
MOTOR_OPTIONS               = 211
ADDRESS                     = 49
REG_KP                      = 299
REG_KI                      = 300
REG_KD                      = 301
REG_OUTPUT                  = 309
RAMP_SPEED                  = 349
RAMP_SPEED_MAX              = 350
RAMP_ACC_MAX                = 352
RAMP_DEC_MAX                = 353
MODE                        = 399
TARGET_INPUT                = 449
TARGET_SELECT               = 451
TARGET_FILTER               = 460
TARGET_PRESENT              = 461

# Speed and ramp-speed units in the manual are based on 4096 positions/rev.
SPEED_COUNTS_PER_REV        = 4096

# ==========================================
#  Register Values 
# ==========================================
# Mode Register (400) options
MODE_OFF                    =   0           # Stop / Disable
MODE_RESET                  =   1
MODE_SHUTDOWN               =   4
MODE_QUICKSTOP              =   5
MODE_FIRMWARE               =   6
MODE_FACTORY                =   7
MODE_RELOAD                 =   8
MODE_STORE                  =   9
MODE_PWM                    =  10
MODE_FREEWHEEL              =  19           # Open Loop
MODE_POSITION               =  20           # Closed Loop Position Control, no ramp [WARNING!] Too large target position changes can cause damage
MODE_POSITION_RAMP          =  21
MODE_ROTARY                 =  23
MODE_SPEED                  =  32
MODE_SPEED_RAMP             =  33
MODE_SPEED_LOW              =  34
MODE_SPEED_LOW_RAMP         =  35
MODE_TORQUE                 =  40
MODE_SEQ_POS                =  51
MODE_SEQ_POS_INT            =  52
MODE_SEQ_POS_FIN            =  54
MODE_SEQ_SPEED              =  55
MODE_SEQ_SPEED_INT          =  56
MODE_SEQ_SPEED_FIN          =  59
MODE_BEEP                   =  60
MODE_HOMING                 =  70
MODE_DEMO_ON                = 200
MODE_DEMO_OFF               = 201
