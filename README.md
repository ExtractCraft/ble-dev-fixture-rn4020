# ble-dev-fixture-rn4020

[RN4020]: http://www.microchip.com/wwwproducts/Devices.aspx?product=RN4020

A development and test fixture for working with the Microchip [RN4020] module.

## Hardware

When no sleep or hibernate functionality is needed, the only hardware connections required are `TXD` and `RXD`.  `WAKE_HW` and `CMD/MLDP` should be low, `WAKE_SW` should be high.  If sleep is required, the module activates when `WAKE_SW` is high and goes to sleep when low.  When waking, the module will send `CMD` and when put to sleep it will send `END`.

## rn4020.py: RN4020P class

This module provides an interface to set up a RN4020 module as a peripheral data server.  Here is a simple example of how to use it:

```python
# Import the module
import rn4020
# We'll need some UUIDs
import uuid

# Create the object, use the built-in serial port of a Raspberry Pi
ble = rn4020.RN4020P('/dev/ttyAMA0')

# Generate UUIDs for a user service with two characteristics
suuid = uuid.uuid4()
cuuid = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]

# Set up the BLE with a standard device information and a custom service
ble.setup({
  'name': 'RasPi',
  'serialize_name': True,
  'device_information': {
    'manufacturer': 'Hacker',
    'model': 'Widget',
    'hardware': '1.0',
    'software': '0.1'
  },
  'services': ['device_information', 'user'],
  'user_service': {
    'uuid':suuid,
    'characteristics': [
      { 'uuid': cuuid[0], 'properties': ['read', 'notify'], 'size': 2 },
      { 'uuid': cuuid[1], 'properties': ['read', 'write'], 'size': 4 },
      { 'uuid': cuuid[2], 'properties': ['read'], 'size': 6 }
    ]
  }
})
```

This is enough to set up the module and make it visible to clients.
Methods are provides to allow reading and writing of characteristic values:

```python
# Update the value of the first characteristic
# Any client that turned on notify on this will be updated
success = ble.write_characteristic(cuuid[0], '0506')

# Read the second characteristic
# This one can be written by a client
# strval will contain a hexadecimal string
strval = ble.read_characteristic(cuuid[1])
```

All values are written and read as hexadecimal strings.  When writing, make sure to write the exact number of characters needed for the characteristic size (twice the number of bytes)!

Methods are provided that allow reading and writing of integers, and will take care of the conversion from and to hexadecimal strings:

```python
# Update the value of the first characteristic
# Any client that turned on notify on this will be updated
# The last parameter is the number of bytes!
success = ble.write_characteristic_int(cuuid[0], 1286, 2)

# Read the second characteristic
# This one can be written by a client
# val will contain an integer value
val = ble.read_characteristic_int(cuuid[1])
```

Conversion to and from hexadecimal is done using the `int_to_hex` and `hex_to_int` methods.  Conversion is done in little-endian format: the LSB is the first byte, the MSB is the last byte.
It is possible to use these functions directly to build compound characteristic values, made up of multiple integers:

```python
# This will send 3 16-bit accelerometer values
s = ble.int_to_hex(accel.X, 2)
s += ble.int_to_hex(accel.Y, 2)
s += ble.int_to_hex(accel.Z, 2)
success = ble.write_characteristic(cuuid[2], s)
```

A callback system is implemented so the program can be notified when something happens:

```python
def connect_cb(status):
  """Connect callback will be called with True when a client connects and
  False when a client disconnects"""
  print "CONNECT" if status else "DISCONNECT"

def write_cb():
  """Write callback will be called when a client updated a characteristic
  value, this callback can read and update the local copy"""
  print "CLIENT WRITE"

# Set the callbacks
ble.set_callbacks(connect_cb, write_cb)
```

For this to work, and for the input buffer not to overflow with status messages from the BLE module, it is important to regularly (in a main loop or from a timer) call the input processing function:

```python
from time import sleep

while True:
  ble.process_input()
  sleep(0.1)
```
