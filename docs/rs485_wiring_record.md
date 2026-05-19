# Simplex Motion RS485 Wiring Record

Date: 2026-05-17

## Goal

Use the SC/SM-Comboard USB-to-RS485 interface to control one or more Simplex Motion motors from Python over Modbus RTU.

## First Test: One Motor

For the first single-motor test, the required connections are:

| Signal | Connect From | Connect To Motor |
| --- | --- | --- |
| RS485 A | Comboard RS485 A | Pin 7, RS485A |
| RS485 B | Comboard RS485 B | Pin 8, RS485B |
| +24 V power | DC power supply +V | Pin 13 and/or Pin 14, +12 V to +48 V |
| GND | DC power supply 0 V/GND | Pin 11 and/or Pin 12, GND |

Short answer: yes, for Modbus RS485 control each motor mainly needs A, B, motor supply voltage, and GND.

Important: the RS485 interface is not isolated, so the Comboard/USB-RS485 side and the motor power supply must share the same ground potential. Do not let the RS485 reference float.

## Wire Size Note

Dupont jumper wires are acceptable for RS485 A/B signal testing, but should not be used as the main 24 V/GND motor power wiring except for a very brief, current-limited bench test with no load.

The motor power wires can carry several amps during acceleration or stall. Thin Dupont jumpers and their crimp contacts can heat up, drop voltage, reset the motor, or become unreliable. Use thicker wire and proper terminals for motor power.

Practical recommendation:

| Connection | Recommended Wire |
| --- | --- |
| RS485 A/B | Twisted pair, Dupont acceptable for short bench test |
| Signal/common reference GND | Dupont acceptable only as a signal reference |
| 24 V motor power and power GND | Use proper power wire, typically 20 AWG or thicker for small tests, 18 AWG or thicker for higher current |

Use a current-limited bench power supply for the first test if available. Start with a low current limit and increase only after communication and basic motion are verified.

## Where To Feed Motor Power

For a single motor using the Simplex Motion demo panel / Comboard, feed 24 V into the board through one of its power inputs:

- The blue 2-pin screw terminal marked 24 V / GND.
- Or the round DC barrel jack, if the plug polarity and voltage match the board requirement.

Then connect the motor using the proper motor connector/cable. The board routes motor power and communication to the motor connector.

If the motor cable is broken out manually instead of using the original connector/cable, power should come directly from the DC power supply or a proper terminal block:

```text
Power supply +24 V ---- Motor +V, pin 13/14
Power supply GND  ----- Motor GND, pin 11/12
Power supply GND  ----- Comboard GND/reference
Comboard RS485 A ------ Motor RS485A, pin 7
Comboard RS485 B ------ Motor RS485B, pin 8
```

Do not use a breadboard as the 24 V motor power distribution path. A breadboard is acceptable for temporary low-current signals, but motor power should use screw terminals, WAGO/terminal blocks, or direct crimped/soldered leads.

For multiple motors, distribute 24 V/GND from the DC supply through a proper power distribution terminal block. Do not rely on the Comboard traces or a breadboard as the power bus for all motors.

## Motor Connector Pins

Simplex Motion SE/SC style 14-pin motor connector communication and power pins:

| Pin | Name | Purpose |
| --- | --- | --- |
| 7 | IN7 / RS485A | RS485 Modbus signal A |
| 8 | IN8 / RS485B | RS485 Modbus signal B |
| 9 | GND | I/O ground reference |
| 11 | GND | Power supply ground |
| 12 | GND | Power supply ground |
| 13 | +12 V to +48 V | Motor power input |
| 14 | +12 V to +48 V | Motor power input |

Use the motor model's technical data sheet to confirm the exact connector orientation before applying power.

## Single-Motor Bring-Up Checklist

1. Power off the DC supply before wiring.
2. Connect RS485 A to motor pin 7.
3. Connect RS485 B to motor pin 8.
4. Connect +24 V to motor pin 13 and/or pin 14.
5. Connect power GND to motor pin 11 and/or pin 12.
6. Make sure the Comboard ground and motor power ground are common.
7. Connect USB from PC to Comboard.
8. Apply motor power.
9. Confirm Windows shows the Comboard as a COM port.
10. Test communication using default Modbus settings:
    - Baud rate: 57600
    - Parity: even
    - Stop bits: 1
    - Data bits: 8
    - Default motor address: 1

If there is no response, first verify COM port, power, address, and baud rate. If those are correct, try swapping A and B because RS485 A/B naming is not always consistent across devices.

## Expanding To Multiple Motors

RS485 should be wired as a bus/daisy chain:

```text
Comboard A ---- Motor 1 A ---- Motor 2 A ---- Motor 3 A
Comboard B ---- Motor 1 B ---- Motor 2 B ---- Motor 3 B
GND common ---- Motor 1 GND -- Motor 2 GND -- Motor 3 GND
Power +24 V --- Motor 1 +V --- Motor 2 +V --- Motor 3 +V
```

Avoid star wiring for RS485. Use one main twisted pair for A/B and keep stubs short.

Each motor on the same RS485 bus must have a unique Modbus address. The default address is 1, so configure motors one at a time before connecting them all together.

Suggested addresses:

| Motor | Modbus Address |
| --- | --- |
| Motor 1 | 1 |
| Motor 2 | 2 |
| Motor 3 | 3 |
| Motor 4 | 4 |

The address is register 50, named `<Address>`. After changing it, store settings to non-volatile memory by setting `<Mode>` register 400 to `9` (`Store`), then reset or power cycle.

## Termination And Bus Notes

- For short cables at 57600 baud, start without termination.
- For long cables or higher baud rates, add one 100-120 ohm resistor across A/B at each end of the bus only.
- Do not add a termination resistor at every motor.
- Strong bus polarization should only be enabled on one device if needed.
- The motor manual recommends termination especially for high baud rates above 57600 and long cable runs over 50 m.

## Safety Notes

- Do not hot-plug power, logic, or communication while the motor is powered.
- USB does not power the motor. External motor power is required for motion.
- Size the DC supply for total motor current, including acceleration peaks.
- During braking, the motor can push energy back into the supply and raise the bus voltage. Use conservative deceleration while testing.
- Confirm connector orientation carefully before applying 24 V.

## References Used

- `Reference/TechnicalDataSM-Comboard_01c.pdf`
- `Reference/SimplexMotionTechnicalDataSE.pdf`
- `SimplexMotion_Motor_Example_Using_PyModbus-master/.../Simplex motion motor manual.pdf`
