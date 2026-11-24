//! Inputs and outputs of the logic.

use crate::SavedState;

/// Why the chip is running. The app reads it from the reset reason and the
/// ext1 wake status (IO0-IO5).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WakeCause {
    /// Power-on, brown-out, watchdog or software reset: not a deep-sleep wake.
    Reset,
    /// UP button (IO2).
    ButtonUp,
    /// OK button (IO5).
    ButtonOk,
    /// LIS2DW12 wake-up interrupt (IO3).
    Shake,
    /// USB_PGOOD_N (IO1) went low.
    UsbPlugged,
    /// MAX17048 alert (IO0), set up as the low-voltage alert.
    BatteryAlert,
}

/// Everything the logic needs at the start of a wake.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Wake {
    pub cause: WakeCause,
    /// RTC time now, in milliseconds. It keeps counting through deep sleep.
    pub now_ms: u64,
    /// USB_PGOOD_N is low right now.
    pub usb_present: bool,
    /// State from RTC memory, or `SavedState::default()` when it was not valid.
    pub saved: SavedState,
    /// Firmware version string for the device-info screen.
    pub firmware: &'static str,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Button {
    Up,
    Ok,
    Down,
}

/// SHT40 result.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Climate {
    /// `21562` means 21.562 degC.
    pub temperature_millicelsius: i32,
    /// `4512` means 45.12 %RH.
    pub humidity_hundredths: u16,
}

/// MAX17048 result.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Battery {
    pub millivolts: u16,
    /// State of charge. The gauge can report slightly over 100; the UI clamps.
    pub percent: u8,
}

/// One round of sensor reads. `None` means that sensor failed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Readings {
    pub climate: Option<Climate>,
    /// BMP580 pressure in pascals.
    pub pressure_pa: Option<u32>,
    pub battery: Option<Battery>,
}

/// Things that happen while awake.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Event {
    Button(Button),
    /// The result of the read asked for by `Output::read_sensors`.
    Readings(Readings),
    /// USB_PGOOD_N changed. `true` means USB is now plugged in.
    UsbChanged(bool),
    /// The time in `Next::Wait::until_ms` was reached.
    Timeout,
}

/// Which GPIOs may wake the chip from deep sleep.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WakeSources {
    pub button_up: bool,
    pub button_ok: bool,
    pub shake: bool,
    pub usb_plug: bool,
    pub battery_alert: bool,
}

impl WakeSources {
    /// Normal sleep: any deliberate action, USB, or the low-voltage alert.
    pub const NORMAL: Self = Self {
        button_up: true,
        button_ok: true,
        shake: true,
        usb_plug: true,
        battery_alert: true,
    };

    /// Normal sleep without the battery alert: used after an alert wake that
    /// found the cell above the cut-off, so a lingering alert can't wake the
    /// chip again and again.
    pub const NORMAL_NO_ALERT: Self = Self {
        battery_alert: false,
        ..Self::NORMAL
    };

    /// Battery too low: only plugging in USB wakes the chip.
    pub const USB_ONLY: Self = Self {
        button_up: false,
        button_ok: false,
        shake: false,
        usb_plug: true,
        battery_alert: false,
    };
}

/// What the app does after the current step.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Next {
    /// Stay awake and wait for an event. When `until_ms` is set and nothing
    /// else happens first, send `Event::Timeout` at that time. `None` means
    /// wait for an event with no deadline (USB present, screen blank).
    Wait { until_ms: Option<u64> },
    /// Prepare the pins for sleep and enter deep sleep with these sources.
    Sleep(WakeSources),
}

/// Actions for the app, done in field order: read the sensors (and send the
/// result back as `Event::Readings`), draw `show`, then follow `next`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Output {
    pub read_sensors: bool,
    /// Draw this view and refresh the panel. `None` means leave it as it is.
    pub show: Option<View>,
    pub next: Next,
}

/// Whether temperature and humidity can be trusted right now.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TempStatus {
    Reliable,
    /// USB present: the charger and regulator heat the board.
    Charging,
    /// USB was unplugged less than `config::COOL_DOWN_MS` ago.
    CoolingDown {
        minutes_left: u16,
    },
}

/// The two pages UP and DN switch between.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Page {
    Main,
    Info,
}

/// Main screen: the readings.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MainView {
    pub readings: Readings,
    pub temp_status: TempStatus,
}

/// Device-info screen.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InfoView {
    pub readings: Readings,
    pub temp_status: TempStatus,
    pub usb: bool,
    pub wake_cause: WakeCause,
    pub firmware: &'static str,
}

/// A screen to draw. The UI crate turns each into pixels.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum View {
    Main(MainView),
    Info(InfoView),
    /// Battery below the cut-off. Stays on the panel while the device sleeps.
    ChargeMe {
        millivolts: u16,
    },
    /// All white, so stale values are never left on the panel.
    Blank,
}
