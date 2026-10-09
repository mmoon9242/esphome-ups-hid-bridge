# Fork changes and validation

Based on upstream commit `39fe49e0ec2b0bc3aea7a02a15e7da395624bbc1`.
Modified on 2026-10-10. The upstream LICENSE remains unchanged: C++ runtime code is GPLv3; Python and other files are MIT as described there. This fork does not claim upstream authorship.

## Source changes

1. CyberPower battery voltage: preserve the high byte of little-endian decivolt reports when present; retain the existing two-byte report path. Apply the same decoding to nominal voltage.
2. NUT client timeout: sample millis() after acquiring clients_mutex_, preventing a newer last_activity from causing unsigned subtraction to underflow.
3. NUT GET DESC: implement authenticated variable-description queries, including UPS/variable/argument validation. Common fields have descriptions; others return the protocol-permitted Unavailable value.

These changes are independent commits. Powercom additions from samoswall/esphome-UPS-HID-NUT are not included; that fork was used during initial hardware bring-up.

## Hardware observations

ESP32-S3-WROOM-1-N16R8 with CyberPower CP1500PFCLCDa TW:

- Before voltage fix: 0x13 / 10 = 1.9 V (high byte lost).
- After voltage fix: HID report 0x0A, raw 0x0113 = 275, gives 27.5 V.
- Nominal voltage: HID report 0x09, raw 0x00F0 = 240, gives 24.0 V.
- GET DESC responses and errors for unknown UPS, unsupported variable and missing argument were verified on the deployed firmware.
- The timeout fix was exercised with 10 active NUT connections and 150 subsequent read-only queries before these fixes were transferred onto this upstream-based branch.

The upstream-based publication branch also compiled successfully with the environment below, using a private hardware configuration outside this repository. The read-only checker passed all 16 advertised variable descriptions and 3 invalid requests on the deployed firmware.

The voltage is a UPS-reported value, not independently measured. Width detection currently uses report length, matching the tested device; descriptor-driven decoding and validation on other CyberPower models remain future work. Two-byte reports retain the previous behavior but were not tested on additional physical devices.

No discharge, shutdown, battery self-test or UPS control tests were performed. Home Assistant NUT and TrueNAS end-to-end setup are not claimed as verified.

## Reproduce read-only NUT validation

With firmware built from this source, run:

```sh
python tools/check_nut_read_compat.py --host DEVICE_IP --ups UPS_NAME --username NUT_USER
```

The tool prompts for the password without echoing it. It checks all advertised variable descriptions and invalid requests, prints battery voltages, and sends no control commands. Credentials travel over the existing plain TCP NUT connection; use the tool on your trusted LAN.

## Build

Use upstream YAML examples with your own ignored secrets.yaml. The hardware validation used ESPHome 2025.7.5, ESP-IDF 5.4.2 and pioarduino 54.03.21. This is a tested combination, not a claim that newer versions are incompatible.

The repository does not include private credentials, network addresses, MAC addresses, device logs, build environments or firmware binaries. A 10-client limit is a deployment choice, not a changed default; configure max_clients and the ESP-IDF socket budget in your own YAML when needed.
