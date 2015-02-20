# RN4020 BLE module peripheral mode

import serial


class RN4020P: 
  """RN4020 BLE module as a peripheral server"""

  def __init__(self, port):
    """Constructor"""
    # Create a serial object we'll use to access the BLE module
    self.serial = serial.Serial(port, baudrate=115200, timeout=0, writeTimeout=0)
    # Read buffer to deal with incomplete lines
    self.read_buffer = ''
    # Make sure we start with sync'ed communication
    self._write_cmd('V')

  def _write_line(self, data):
    """Low level write line to BLE module"""
    self.serial.write(data + '\n')

  def _read_line(self):
    """Low level read line from BLE module (if there is one)"""
    # Read any new bytes
    self.read_buffer += self.serial.read(self.serial.inWaiting())
    # Split on newline
    parts = self.read_buffer.split('\r\n', 1)
    # Found a newline?
    if len(parts) > 1:
      # Save the remainder of the read buffer
      self.read_buffer = parts[1]
      # Return the line
      return parts[0]
    else:
      return None

  def _write_cmd(self, cmd):
    """Write a command and wait for response"""
    print ">" + cmd
    self._write_line(cmd);
    resp = None
    while resp == None:
      resp = self._read_line()
    print "<" + resp
    return resp

  def _read_lines(self):
    """Read all full lines received"""
    d = ""
    while True:
      l = self._read_line()
      if l != None:
        d += l + '\n'
      else:
        break
    return d

  def _discard_input(self):
    """Throw away any input in the buffer"""
    self.read_buffer = ''
    self.serial.read(self.serial.inWaiting())

  def _build_bitmap(self, dictionary, key, defined):
    """Build a bitmap value from a list in a dictionary and another
    dictionary that defines bit masks for valid list values"""
    bitmap = 0
    if key in dictionary and hasattr(dictionary[key], '__iter__'):
      for item in dictionary[key]:
        if item in defined:
          bitmap |= defined[item]
    return bitmap

  def setup(self, cfg):
    """Set up the BLE module with the provided config"""
    # Clear old stuff from the buffer
    self._discard_input()
    # Set device name
    if 'name' in cfg:
      if 'serialize_name' in cfg and cfg['serialize_name']:
        self._write_cmd('S-,' + cfg['name'][:15].replace(' ', '_'))
      else:
        self._write_cmd('SN,' + cfg['name'][:20].replace(' ', '_'))
    # Set data for Device Information Service if specified
    if 'device_information' in cfg:
      devinfo = cfg['device_information']
      if 'firmware' in devinfo:
        self._write_cmd('SDF,' + devinfo['firmware'][:20])
      if 'hardware' in devinfo:
        self._write_cmd('SDH,' + devinfo['hardware'][:20])
      if 'model' in devinfo:
        self._write_cmd('SDM,' + devinfo['model'][:20])
      if 'manufacturer' in devinfo:
        self._write_cmd('SDN,' + devinfo['manufacturer'][:20])
      if 'software' in devinfo:
        self._write_cmd('SDR,' + devinfo['software'][:20])
    # Set up for peripheral use
    # Auto advertise, server only, ensure iOS compatibility
    self._write_cmd('SR,20006000')
    # Build services bitmap
    defservices = {
      'device_information':     0x80000000,
      'battery':                0x40000000,
      'heart_rate':             0x20000000,
      'health_thermometer':     0x10000000,
      'glucose':                0x08000000,
      'blood_pressure':         0x04000000,
      'running_speed_cadence':  0x02000000,
      'cycling_speed_cadence':  0x01000000,
      'current_time':           0x00800000,
      'next_dst_change':        0x00400000,
      'reference_time_update':  0x00200000,
      'link_loss':              0x00100000,
      'immediate_alert':        0x00080000,
      'tx_power':               0x00040000,
      'alert_notification':     0x00020000,
      'phone_alert_status':     0x00010000,
      'scan_parameters':        0x00004000,
      'user':                   0x00000001
    }
    services = self._build_bitmap(cfg, 'services', defservices)
    if 'user_service' in cfg:
      services |= defservices['user']
    # Enable selected services
    self._write_cmd('SS,%08X' % services)
    # Configure timing if specified
    if 'timing' in cfg:
      # Defaults for iOS compatibility
      interval = 16
      latency = 2
      timeout = 100
      # Override with specified values
      if 'interval' in cfg['timing']:
        interval = cfg['timing']['interval']
      if 'latency' in cfg['timing']:
        latency = cfg['timing']['latency']
      if 'timeout' in cfg['timing']:
        timeout = cfg['timing']['timeout']
      # Send timing config
      self._write_cmd('ST,%04X,%04X,%04X' % (interval, latency, timeout))
    # Configure user service if specified
    if 'user_service' in cfg and 'uuid' in cfg['user_service']:
      # Clear previous user service
      self._write_cmd('PZ')
      # Set the user service UUID
      self._write_cmd('PS,%032X' % cfg['user_service']['uuid'])
      # Check if characteristics specified
      if 'characteristics' in cfg['user_service'] and \
          hasattr(cfg['user_service']['characteristics'], '__iter__'):
        # Add all specified characteristics
        for characteristic in cfg['user_service']['characteristics']:
          # Does it have a UUID?
          if 'uuid' in characteristic:
            # Default size
            csize = 20
            # Build properties bitmap
            defproperties = {
              'extended_property':      0x80,
              'authenticated_write':    0x40,
              'indicate':               0x20,
              'notify':                 0x10,
              'write':                  0x08,
              'write_without_response': 0x04,
              'read':                   0x02,
              'broadcast':              0x01
            }
            cproperties = self._build_bitmap(characteristic, 'properties', defproperties)
            # Set size if specified
            if 'size' in characteristic:
              csize = characteristic['size']
              if csize > 20: size = 20
            # Create the characteristic
            self._write_cmd('PC,%032X,%02X,%02X' % (characteristic['uuid'],
                              cproperties, csize))
    # Now reset to apply the configuration
    self._write_cmd('R,1')

  def read_characteristic(self, uuid):
    """Read the characteristic with the specified UUID
    Data will be returned as a HEX string"""
    # Throw away old crap
    self._discard_input()
    # Choose format based on 16-bit or 128-bit UUID
    if uuid > 0xFFFF:
      return self._write_cmd('SUR,%032X' % uuid)
    else:
      return self._write_cmd('SUR,%04X' % uuid)

  def write_characteristic(self, uuid, data):
    """Write the characteristic with the specified UUID
    Data needs to be provided as a HEX string on the right length"""
    # Choose format based on 16-bit or 128-bit UUID
    if uuid > 0xFFFF:
      self._write_cmd('SUW,%032X,%s' % (uuid, data))
    else:
      self._write_cmd('SUW,%04X,%s' % (uuid, data))
