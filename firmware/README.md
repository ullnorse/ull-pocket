# ull-pocket firmware

Stage 1: the parts that need no hardware. The ESP32-C6 app crate comes after the SSD1681 panel driver.

| Crate | What it is |
|---|---|
| `logic/` (`pocket-logic`) | `no_std`, no dependencies. Wake cause + saved state + events in, actions out. |
| `ui/` (`pocket-ui`) | `no_std`. Draws each screen into a 200x200 1-bit `Frame` (5000 bytes) with embedded-graphics 0.8 and u8g2-fonts. |
| `render/` (`pocket-render`) | Host tool. Renders every sample screen to `renders/*.png`. |

## v1 behaviour

The device does nothing while asleep. It wakes on UP, OK, a firm shake (LIS2DW12 wake-up), USB plug-in or the MAX17048 low-voltage alert. It reads the sensors and shows the main screen; UP/DN switch between the main and device-info screens; OK takes a fresh reading. After 30 s with no input it blanks the panel and sleeps. With USB present it never sleeps; after 30 s idle it blanks the panel and waits for a button or USB change. Below 3.4 V on battery it shows "Charge me" and sleeps with only USB as a wake source. Temperature and humidity are marked unreliable while USB is present and for 20 min after unplugging.

The constants are in `logic/src/config.rs`: idle timeout, cool-down, low-battery cut-off, shake threshold. The cool-down and shake threshold are guesses until the first board is measured.

## logic

- `Pocket::wake(Wake)` starts a wake: cause, RTC time, USB present, saved state, firmware version.
- `Pocket::handle(Event, now_ms)` takes `Button(Up|Ok|Down)`, `Readings`, `UsbChanged(bool)` or `Timeout`.
- Both return an `Output`, done in field order:
  - `read_sensors`: read SHT40, BMP580, MAX17048 and send back `Event::Readings` (`None` per failed sensor);
  - `show`: draw this `View` (`Main`, `Info`, `ChargeMe`, `Blank`) and refresh the panel;
  - `next`: `Wait { until_ms }` (wait for a button/USB edge, or send `Timeout` at `until_ms`; `None` = no deadline) or `Sleep(WakeSources)`.
- The logic never reads a clock and never loops: the app passes the RTC time (it keeps counting in deep sleep) and waits for interrupts or the deadline.
- `SavedState` is the only thing carried across deep sleep: the time until which temperature/humidity are still warm from charging. 8 bytes in memory; stored as a 12-byte array (`encode`/`decode`, with magic, version and checksum) so garbage RTC memory after power-on is rejected and no `unsafe` is needed.

## How the app will use it

One pass per wake:

1. Read the wake cause: reset reason, then the ext1 status (IO0 battery alert, IO1 USB, IO2 UP, IO3 shake, IO5 OK).
2. Load the saved state: `SavedState::decode` on the RTC-memory bytes, `SavedState::default()` if it fails.
3. `Pocket::wake(...)`, then loop: do the actions in each `Output`, feed back the next event. While waiting, DN (IO9) is not an LP GPIO: use a normal GPIO interrupt while awake.
4. On `Next::Sleep(sources)`: store `pocket.saved_state().encode()` in RTC memory.
5. Prepare pins for sleep (PARTS.md firmware rules): put the panel into deep sleep, hold DC/SCK/MOSI, never leave I2C low, CHG_DIS low or input, clear the MAX17048 alert, enable the BMP580 INT, set LIS2DW12 INT1 active-low with the wake-up threshold from `config::SHAKE_THRESHOLD_MG`.
6. Arm ext1 with the pins in `sources` and enter deep sleep. The battery alert pin is left out when `battery_alert` is false.

Later additions (Wi-Fi upload, Home Assistant, OTA) fit in as new `Event`s and `Output` fields, and new `SavedState` fields under a new format version.

## Run

From `firmware/`:

```sh
cargo test                                   # logic and UI tests on the PC
cargo run -p pocket-render                   # writes renders/*.png
cargo fmt
cargo clippy --all-targets -- -D warnings
cargo build -p pocket-logic -p pocket-ui --target riscv32imac-unknown-none-elf   # no_std check for the C6
```

## Renders

`renders/*.png` are drawn at 3x: 600x600 pixels for the panel's true 200x200 (1.54", about 7 px per mm, so the PNG at 100 % is roughly 3x the real size). Samples are in `ui/src/samples.rs`: normal, charging, cooling down, failed sensors, low battery, and extreme values (-20.5 and -45.0 °C, 125.0 °C, 0 and 100 % RH, 300, 1100 and 1250 hPa).

The `Frame` bytes use the SSD1681 black/white RAM layout: rows top to bottom, MSB = leftmost pixel, 1 = white. Screen coordinates are as the user sees the panel; the driver handles the mounting rotation.

Fonts come from U8g2 through the u8g2-fonts crate (logisoso, fub, helvR/helvB). Each font has its own licence; see the U8g2 LICENSE file.
