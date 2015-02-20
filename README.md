# ble-dev-fixture-rn4020
A development and test fixture for working with the RN4020 module.

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
cuuid = [uuid.uuid4(), uuid.uuid4()]

# Set up the BLE with a standard device information and a custom service
ble.setup({
  'name': 'RasPi',
  'services': ['device_information'],
  'user_service': {
    'uuid':suuid,
    'characteristics': [
      { 'uuid': cuuid[0], 'properties': ['read','notify'], 'size': 2 },
      { 'uuid':cuuid[1], 'properties': ['read','write'] }
    ]
  }
})

# Update the value of the first characteristic
# Any client that turned on notify on this will be updated
ble.write_characteristic(cuuid[0], '0506')

# Read the second characteristic
# This one can be written by a client
ble.read_characteristic(cuuid[1])
```

All values are written and read as hexadecimal strings.  When writing, make sure to write the exact number of characters needed for the characteristic size!
