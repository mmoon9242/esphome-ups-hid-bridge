# ESPHome UPS HID Bridge

A fork of [bullshit/esphome-components](https://github.com/bullshit/esphome-components), preserving the original project history and license. This fork adds focused NUT interoperability and CyberPower voltage fixes for ESP32-S3.

See [changes and validation](docs/fork-changes.md). The original project documentation follows below.

---

# ESPHome Components Collection

A collection of ESPHome components for various hardware integrations and monitoring solutions.

## Compatibility Fixes: WinNUT GET DESC, CyberPower Battery Voltage, and NUT Connections

This fork preserves the original [bullshit/esphome-components](https://github.com/bullshit/esphome-components) project history and LICENSE. The changes below were made by mmoon9242 on October 10, 2026, based on upstream commit `39fe49e`. They address three independent issues in the ESPHome USB HID UPS bridge for ESP32-S3.

### WinNUT: ERR INVALID-ARGUMENT on GET DESC

**Symptom:** WinNUT can display live UPS values but reports an error when requesting variable descriptions, for example:

```text
GET DESC CyberPower1500VA ups.mfr
ERR INVALID-ARGUMENT
```

**Cause:** The NUT server dispatched `GET VAR` but did not implement the standard `GET DESC` subcommand. Updating an older WinNUT client resolved a separate client-version interoperability problem, but description requests still exposed this missing server feature.

**Fix:** Add authenticated `GET DESC` handling with argument, UPS-name, and variable validation. Common variables have human-readable descriptions; other supported variables return `Unavailable`, as permitted by the [NUT network protocol](https://networkupstools.org/docs/developer-guide.chunked/ar01s09.html). A successful response now looks like:

```text
DESC CyberPower1500VA ups.mfr "UPS manufacturer"
```

### CyberPower CP1500PFCLCDa TW: Battery Voltage Shows 1.9 V Instead of 27.5 V

**Symptom:** Both ESPHome and NUT reported `battery.voltage` as 1.9 V, while `battery.voltage.nominal` was 24.0 V.

**Cause:** The CyberPower parser read only the low byte of the voltage payload. On the tested device, HID report `0x0A` contained a 16-bit little-endian decivolt value, `0x0113` (275). Truncating it to `0x13` (19), then dividing by 10, produced the incorrect 1.9 V.

**Fix:** Preserve the high byte when the report includes it, and retain the existing two-byte report path. Apply the same decoding to nominal battery voltage. The tested device now reports 27.5 V from `0x0113`, and nominal voltage remains 24.0 V from `0x00F0`.

These are UPS-reported values, not independent electrical measurements. Report width is currently inferred from payload length; descriptor-driven decoding and validation on additional CyberPower models remain future work.

### NUT Server: Active Connections Can Be Incorrectly Timed Out

**Symptom:** Active NUT connections could disconnect during concurrent read-only client testing.

**Cause:** Cleanup sampled `millis()` before acquiring the client mutex. Another task could update `last_activity` to a later timestamp before cleanup acquired the lock. Unsigned `now - last_activity` then underflowed, making a recent connection appear to have exceeded the timeout.

**Fix:** Sample the clock after acquiring `clients_mutex_`, keeping the timeout comparison consistent with the protected client timestamps.

### Validation and Scope

- Hardware: ESP32-S3-WROOM-1-N16R8 and CyberPower CP1500PFCLCDa TW.
- Build environment: ESPHome 2025.7.5, ESP-IDF 5.4.2, and pioarduino 54.03.21.
- Deployed firmware verified corrected battery values, successful `GET DESC` responses, and error responses for invalid arguments, unknown UPS names, and unsupported variables.
- The timeout fix was exercised with 10 active NUT connections and 150 subsequent read-only queries. This used a deployment-specific client/socket configuration; the repository defaults were not increased.
- No UPS shutdown, discharge, battery self-test, or control tests were performed. Home Assistant NUT and TrueNAS end-to-end integration are not claimed as verified.

For reproducible read-only checks and limitations, see [fork changes and validation](docs/fork-changes.md). Each source fix has its own Git commit to make upstream review and reuse straightforward.

---

## Available Components

### 🔋 UPS HID Component (`ups_hid`)

Monitor UPS devices via direct USB connection on ESP32-S3. Supports APC, CyberPower, and generic HID UPS devices with real-time monitoring of battery status, power conditions, and device information.

**Key Features:**
- **Real-time UPS monitoring**: Battery, voltage, load, runtime, and 15+ sensors
- **Multi-protocol support**: APC HID, CyberPower HID, Generic HID with auto-detection
- **UPS Control**: Beeper control (enable/disable/mute/test) and battery testing
- ⏱️ **Delay configuration**: Configure UPS shutdown, start, and reboot delays via USB HID
- **Home Assistant integration**: Full device discovery and management
- **Developer-friendly**: Simulation mode, comprehensive logging

[📖 Full Documentation](components/ups_hid/README.md)

### 💡 UPS Status LED Component (`ups_status_led`)

Smart LED status indicator for UPS monitoring with automatic pattern management and night mode. Provides visual status indication using solid colors with thread-safe runtime configuration.

**Key Features:**
- **7 solid color patterns**: Critical (red), Battery (orange), Charging (yellow), Normal (green), Offline (blue), No Data (purple), Error (white)
- **Night mode**: Time-based brightness dimming with color compensation for WS2812 LEDs
- **Home Assistant controls**: Enable/disable, brightness, night mode settings via web UI
- **Thread-safe operation**: Safe concurrent access from web UI and main loop
- **Minimum brightness logic**: 20% minimum ensures meaningful enable/disable distinction

[📖 Full Documentation](components/ups_status_led/README.md)

### 🌐 NUT Server Component (`nut_server`)

Network UPS Tools (NUT) protocol TCP server for exposing UPS data to standard monitoring tools. Provides NUT v1.3 compliant server for integration with existing infrastructure.

**Key Features:**
- **Standard NUT Protocol**: v1.3 compliant TCP server on port 3493
- **Multi-client support**: Up to 4 simultaneous monitoring connections
- **Full protocol implementation**: LIST UPS/VAR/CMD/CLIENT, INSTCMD, NETVER
- **Dynamic UPS detection**: Automatically exposes connected UPS manufacturer/model
- **Authentication support**: Optional username/password protection
- **Data Provider Pattern**: Direct access to UPS data without sensor overhead

[📖 Full Documentation](components/nut_server/README.md)

## 📦 Configuration Management

Modular, maintainable ESPHome configuration system using packages. Build configurations by combining reusable components instead of maintaining large monolithic files.

**Key Features:**
- **Modular packages**: Core, sensors, controls, device-specific optimizations
- **Grouped organization**: Optional entity grouping for cleaner web interface
- **Example configurations**: Production-ready configs for APC, CyberPower, and rack UPS
- **Regional defaults**: Voltage/frequency presets for different regions
- **Smart LED integration**: Automatic visual status indication

[📖 Configuration Guide](configs/README.md)

## Development

### Project Structure

```
components/
├── ups_hid/                 # UPS HID monitoring component
│   ├── README.md           # Component-specific documentation
│   ├── __init__.py         # Component configuration
│   ├── ups_hid.h           # Main component header
│   ├── ups_hid.cpp         # Main component implementation
│   ├── sensor.py           # Sensor platform
│   ├── binary_sensor.py    # Binary sensor platform
│   ├── text_sensor.py      # Text sensor platform
│   └── ...                 # Protocol implementations
├── ups_status_led/         # Smart LED status indicator component
│   ├── README.md           # Component documentation
│   ├── __init__.py         # Component configuration
│   ├── ups_status_led.h    # Component header
│   └── ups_status_led.cpp  # Component implementation
├── nut_server/             # Network UPS Tools (NUT) TCP server component
│   ├── README.md           # Component documentation
│   ├── __init__.py         # Component configuration
│   ├── nut_server.h        # Component header
│   └── nut_server.cpp      # Component implementation
└── ...

configs/
├── README.md               # Configuration management documentation
├── base_ups.yaml           # Core UPS configuration
├── essential_sensors.yaml  # Essential monitoring sensors
├── extended_sensors.yaml   # Extended monitoring sensors
├── ups_controls.yaml       # UPS control buttons
├── nut_server.yaml         # NUT server configuration
├── examples/               # Example device configurations
│   ├── apc-ups-monitor.yaml
│   ├── cyberpower-ups-monitor.yaml
│   └── rack-ups-monitor.yaml
└── ...                     # Additional modular packages

tools/
├── scan-usb.sh             # USB device scanning utility
└── README.md               # Tools documentation

.vscode/
├── tasks.json              # VSCode development tasks
```

### Development Tools

- **Scan USB Devices**: `bash tools/scan-usb.sh`
  - Lists connected ESP32, UPS, and serial devices
- **VSCode Tasks**: Integrated development tasks via Command Palette

### Adding New Components

1. Create component directory: `components/your_component/`
2. Implement core files:
   - `__init__.py` - Component configuration and validation
   - `your_component.h` - Component header
   - `your_component.cpp` - Component implementation
   - Platform files (`sensor.py`, etc.) as needed
3. Add component documentation: `components/your_component/README.md`
4. Update this main README with component description
5. Test with both real hardware and simulation where applicable

### Coding Guidelines

- Follow ESPHome coding standards and patterns
- Don't use exceptions (ESPHome disables them)
- Include comprehensive logging with appropriate levels
- Implement thread-safe code where necessary
- Provide simulation modes for testing
- Include detailed documentation and examples

## Hardware Requirements

Component-specific requirements are documented in each component's README:

- **UPS HID**: ESP32-S3-DevKitC-1 v1.1 with USB OTG support
- **UPS Status LED**: WS2812 LED strip (1 LED), requires time component for night mode
- **Future components**: Requirements will be listed here

## License

This project follows the ESPHome dual-license model:

- **C++ Runtime Code** (`.c`, `.cpp`, `.h`, `.hpp`, `.tcc`, `.ino`): Licensed under [GNU GPLv3](LICENSE)
- **Python Code** (`.py`) and other files: Licensed under [MIT License](LICENSE)

See the [LICENSE](LICENSE) file for complete license text.

### Third-Party Components

This project is built as ESPHome external components and follows ESPHome's licensing structure. The components are designed to work within the ESPHome ecosystem.
