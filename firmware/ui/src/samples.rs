//! Sample views for renders and tests: normal use, charging, sensor
//! failures, low battery and extreme values.

use pocket_logic::{Battery, Climate, InfoView, MainView, Readings, TempStatus, View, WakeCause};

const FIRMWARE: &str = "0.1.0";

const NORMAL: Readings = Readings {
    climate: Some(Climate {
        temperature_millicelsius: 21_562,
        humidity_hundredths: 4_512,
    }),
    pressure_pa: Some(101_325),
    battery: Some(Battery {
        millivolts: 3_920,
        percent: 78,
    }),
};

const COLD_WET_HIGH: Readings = Readings {
    climate: Some(Climate {
        temperature_millicelsius: -20_500,
        humidity_hundredths: 10_000,
    }),
    pressure_pa: Some(110_000),
    battery: Some(Battery {
        millivolts: 4_200,
        percent: 100,
    }),
};

/// The widest values the sensors can report: SHT40 -45..125 degC, BMP580
/// 300..1250 hPa.
const WIDEST: Readings = Readings {
    climate: Some(Climate {
        temperature_millicelsius: -45_000,
        humidity_hundredths: 10_000,
    }),
    pressure_pa: Some(125_000),
    battery: Some(Battery {
        millivolts: 4_400,
        percent: 103,
    }),
};

const HOT: Readings = Readings {
    climate: Some(Climate {
        temperature_millicelsius: 125_000,
        humidity_hundredths: 0,
    }),
    pressure_pa: Some(30_000),
    battery: Some(Battery {
        millivolts: 3_400,
        percent: 0,
    }),
};

const ALL_FAILED: Readings = Readings {
    climate: None,
    pressure_pa: None,
    battery: None,
};

const CLIMATE_FAILED: Readings = Readings {
    climate: None,
    ..NORMAL
};

const fn main(readings: Readings, temp_status: TempStatus) -> View {
    View::Main(MainView {
        readings,
        temp_status,
    })
}

const fn info(
    readings: Readings,
    temp_status: TempStatus,
    usb: bool,
    wake_cause: WakeCause,
) -> View {
    View::Info(InfoView {
        readings,
        temp_status,
        usb,
        wake_cause,
        firmware: FIRMWARE,
    })
}

/// Every sample with a file-friendly name.
pub const ALL: [(&str, View); 16] = [
    ("main-normal", main(NORMAL, TempStatus::Reliable)),
    ("main-charging", main(NORMAL, TempStatus::Charging)),
    (
        "main-cooling",
        main(NORMAL, TempStatus::CoolingDown { minutes_left: 12 }),
    ),
    (
        "main-climate-failed",
        main(CLIMATE_FAILED, TempStatus::Reliable),
    ),
    ("main-all-failed", main(ALL_FAILED, TempStatus::Reliable)),
    (
        "main-cold-wet-1100hpa",
        main(COLD_WET_HIGH, TempStatus::Reliable),
    ),
    (
        "main-widest",
        main(WIDEST, TempStatus::CoolingDown { minutes_left: 20 }),
    ),
    ("main-hot", main(HOT, TempStatus::Reliable)),
    (
        "info-normal",
        info(NORMAL, TempStatus::Reliable, false, WakeCause::ButtonUp),
    ),
    (
        "info-charging",
        info(NORMAL, TempStatus::Charging, true, WakeCause::UsbPlugged),
    ),
    (
        "info-full",
        info(
            COLD_WET_HIGH,
            TempStatus::Charging,
            true,
            WakeCause::UsbPlugged,
        ),
    ),
    (
        "info-cooling",
        info(
            NORMAL,
            TempStatus::CoolingDown { minutes_left: 12 },
            false,
            WakeCause::Shake,
        ),
    ),
    (
        "info-all-failed",
        info(
            ALL_FAILED,
            TempStatus::Reliable,
            false,
            WakeCause::BatteryAlert,
        ),
    ),
    ("charge-me", View::ChargeMe { millivolts: 3_380 }),
    ("charge-me-empty", View::ChargeMe { millivolts: 2_995 }),
    ("blank", View::Blank),
];
