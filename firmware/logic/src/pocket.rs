//! The state machine for one wake.

use crate::config::{COOL_DOWN_MS, IDLE_TIMEOUT_MS, LOW_BATTERY_MV};
use crate::types::Page;
use crate::{
    Button, Event, InfoView, MainView, Next, Output, Readings, SavedState, TempStatus, View, Wake,
    WakeCause, WakeSources,
};

/// Logic state for one wake, from wake-up to deep sleep.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Pocket {
    saved: SavedState,
    wake_cause: WakeCause,
    firmware: &'static str,
    usb: bool,
    /// Page shown, or shown once the pending readings arrive.
    page: Page,
    /// Readings or a page are on the panel. `false` means blank (or still
    /// waiting for the first readings of this wake).
    showing: bool,
    /// A read was asked for and its result has not arrived yet.
    reading_pending: bool,
    /// Woken by the battery alert only: check the battery, show nothing
    /// unless it is low, and go back to sleep.
    battery_check_only: bool,
    readings: Readings,
    /// When the screen is blanked if nothing happens. `None` while the
    /// screen is blank on USB (nothing to time out).
    idle_deadline_ms: Option<u64>,
}

impl Pocket {
    /// Starts a wake. The first output always asks for a sensor read.
    pub fn wake(wake: Wake) -> (Self, Output) {
        let mut saved = wake.saved.checked(wake.now_ms);
        if wake.cause == WakeCause::UsbPlugged && !wake.usb_present {
            // Plugged in and pulled out again before we got here: the board
            // may still have warmed up.
            saved.warm_until_ms = wake.now_ms + COOL_DOWN_MS;
        }
        let mut pocket = Self {
            saved,
            wake_cause: wake.cause,
            firmware: wake.firmware,
            usb: wake.usb_present,
            page: Page::Main,
            showing: false,
            reading_pending: false,
            battery_check_only: wake.cause == WakeCause::BatteryAlert && !wake.usb_present,
            readings: Readings::default(),
            idle_deadline_ms: None,
        };
        let output = pocket.start_reading(wake.now_ms);
        (pocket, output)
    }

    /// Handles one event at RTC time `now_ms`.
    pub fn handle(&mut self, event: Event, now_ms: u64) -> Output {
        match event {
            Event::Button(button) => self.on_button(button, now_ms),
            Event::Readings(readings) => self.on_readings(readings, now_ms),
            Event::UsbChanged(present) => self.on_usb(present, now_ms),
            Event::Timeout => self.on_timeout(now_ms),
        }
    }

    /// State to store in RTC memory before deep sleep.
    pub fn saved_state(&self) -> SavedState {
        self.saved
    }

    /// Whether temperature and humidity can be trusted at `now_ms`.
    pub fn temp_status(&self, now_ms: u64) -> TempStatus {
        if self.usb {
            return TempStatus::Charging;
        }
        if now_ms >= self.saved.warm_until_ms {
            return TempStatus::Reliable;
        }
        let left_ms = self.saved.warm_until_ms - now_ms;
        let minutes_left = left_ms.div_ceil(60_000);
        TempStatus::CoolingDown {
            minutes_left: u16::try_from(minutes_left).unwrap_or(u16::MAX),
        }
    }

    fn on_button(&mut self, button: Button, now_ms: u64) -> Output {
        self.battery_check_only = false;
        if self.reading_pending {
            // The readings will draw the page; just keep the device awake.
            self.idle_deadline_ms = Some(now_ms + IDLE_TIMEOUT_MS);
            return self.wait();
        }
        if !self.showing {
            // Blank on USB: any button wakes the screen with a fresh read.
            self.page = Page::Main;
            return self.start_reading(now_ms);
        }
        match button {
            Button::Ok => self.start_reading(now_ms),
            Button::Up | Button::Down => {
                self.page = match self.page {
                    Page::Main => Page::Info,
                    Page::Info => Page::Main,
                };
                self.idle_deadline_ms = Some(now_ms + IDLE_TIMEOUT_MS);
                Output {
                    read_sensors: false,
                    show: Some(self.view(now_ms)),
                    next: self.next_wait(),
                }
            }
        }
    }

    fn on_readings(&mut self, readings: Readings, now_ms: u64) -> Output {
        self.reading_pending = false;
        self.readings = readings;

        if let Some(battery) = readings.battery
            && !self.usb
            && battery.millivolts < LOW_BATTERY_MV
        {
            return Output {
                read_sensors: false,
                show: Some(View::ChargeMe {
                    millivolts: battery.millivolts,
                }),
                next: Next::Sleep(WakeSources::USB_ONLY),
            };
        }

        if self.battery_check_only {
            // The screen is already blank from the last sleep.
            return Output {
                read_sensors: false,
                show: None,
                next: Next::Sleep(WakeSources::NORMAL_NO_ALERT),
            };
        }

        self.showing = true;
        Output {
            read_sensors: false,
            show: Some(self.view(now_ms)),
            next: self.next_wait(),
        }
    }

    fn on_usb(&mut self, present: bool, now_ms: u64) -> Output {
        if present == self.usb {
            return self.wait();
        }
        self.usb = present;
        if !present {
            self.saved.warm_until_ms = now_ms + COOL_DOWN_MS;
        }
        // Plugging or unplugging is a deliberate action: show fresh values
        // (battery and the temperature marker change).
        self.battery_check_only = false;
        if !self.showing {
            self.page = Page::Main;
        }
        self.start_reading(now_ms)
    }

    fn on_timeout(&mut self, now_ms: u64) -> Output {
        let Some(deadline) = self.idle_deadline_ms else {
            return self.wait();
        };
        if now_ms < deadline {
            return self.wait();
        }
        self.showing = false;
        self.page = Page::Main;
        self.idle_deadline_ms = None;
        let next = if self.usb {
            Next::Wait { until_ms: None }
        } else {
            Next::Sleep(WakeSources::NORMAL)
        };
        Output {
            read_sensors: false,
            show: Some(View::Blank),
            next,
        }
    }

    fn start_reading(&mut self, now_ms: u64) -> Output {
        self.reading_pending = true;
        self.idle_deadline_ms = Some(now_ms + IDLE_TIMEOUT_MS);
        Output {
            read_sensors: true,
            show: None,
            next: self.next_wait(),
        }
    }

    fn view(&self, now_ms: u64) -> View {
        let temp_status = self.temp_status(now_ms);
        match self.page {
            Page::Main => View::Main(MainView {
                readings: self.readings,
                temp_status,
            }),
            Page::Info => View::Info(InfoView {
                readings: self.readings,
                temp_status,
                usb: self.usb,
                wake_cause: self.wake_cause,
                firmware: self.firmware,
            }),
        }
    }

    fn next_wait(&self) -> Next {
        Next::Wait {
            until_ms: self.idle_deadline_ms,
        }
    }

    /// Nothing to do: keep waiting as before.
    fn wait(&self) -> Output {
        Output {
            read_sensors: false,
            show: None,
            next: self.next_wait(),
        }
    }
}
