//! Number formatting for the screens, integer-only (the ESP32-C6 has no FPU).

use core::fmt::Write;

use heapless::String;

/// Short text for one value. Every formatted value here fits easily.
pub type Text = String<32>;

/// Placeholder for a value whose sensor failed.
pub const MISSING: &str = "--";

/// `21562` millidegrees -> `"21.6"`. Rounds half away from zero and never
/// prints `"-0.0"`.
pub fn temperature(millicelsius: i32) -> Text {
    let tenths = round_div(i64::from(millicelsius), 100);
    let sign = if tenths < 0 { "-" } else { "" };
    let abs = tenths.unsigned_abs();
    let mut text = Text::new();
    let _ = write!(text, "{sign}{}.{}", abs / 10, abs % 10);
    text
}

/// `4512` hundredths -> 45 (%), clamped to 0..=100.
pub fn humidity_percent(hundredths: u16) -> u16 {
    ((u32::from(hundredths) + 50) / 100).min(100) as u16
}

/// Pascals -> whole hectopascals, rounded.
pub fn pressure_hpa(pa: u32) -> u32 {
    pa.saturating_add(50) / 100
}

/// Millivolts -> `"3.92"` volts, rounded to 10 mV.
pub fn volts(millivolts: u16) -> Text {
    let hundredths = (u32::from(millivolts) + 5) / 10;
    let mut text = Text::new();
    let _ = write!(text, "{}.{:02}", hundredths / 100, hundredths % 100);
    text
}

/// Gauge percentage clamped to 100 (the MAX17048 can report a bit more).
pub fn battery_percent(percent: u8) -> u8 {
    percent.min(100)
}

/// Formats `"{value}{unit}"`, or `"--{unit}"` when the value is missing.
pub fn with_unit(value: Option<impl core::fmt::Display>, unit: &str) -> Text {
    let mut text = Text::new();
    let _ = match value {
        Some(value) => write!(text, "{value}{unit}"),
        None => write!(text, "{MISSING}{unit}"),
    };
    text
}

fn round_div(value: i64, divisor: i64) -> i64 {
    let half = divisor / 2;
    if value >= 0 {
        (value + half) / divisor
    } else {
        -((-value + half) / divisor)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn temperature_rounds_to_one_decimal() {
        assert_eq!(temperature(21_562), "21.6");
        assert_eq!(temperature(21_549), "21.5");
        assert_eq!(temperature(21_550), "21.6");
        assert_eq!(temperature(0), "0.0");
        assert_eq!(temperature(-20_500), "-20.5");
        assert_eq!(temperature(-20_550), "-20.6");
        assert_eq!(temperature(-49), "0.0");
        assert_eq!(temperature(-50), "-0.1");
        assert_eq!(temperature(125_000), "125.0");
        assert_eq!(temperature(-45_000), "-45.0");
        assert_eq!(temperature(i32::MIN), "-2147483.6");
    }

    #[test]
    fn humidity_rounds_and_clamps() {
        assert_eq!(humidity_percent(4_512), 45);
        assert_eq!(humidity_percent(4_550), 46);
        assert_eq!(humidity_percent(0), 0);
        assert_eq!(humidity_percent(10_000), 100);
        assert_eq!(humidity_percent(u16::MAX), 100);
    }

    #[test]
    fn pressure_rounds_to_hpa() {
        assert_eq!(pressure_hpa(101_325), 1013);
        assert_eq!(pressure_hpa(101_350), 1014);
        assert_eq!(pressure_hpa(110_000), 1100);
        assert_eq!(pressure_hpa(u32::MAX), 42_949_672);
    }

    #[test]
    fn volts_have_two_decimals() {
        assert_eq!(volts(3_920), "3.92");
        assert_eq!(volts(3_404), "3.40");
        assert_eq!(volts(3_405), "3.41");
        assert_eq!(volts(4_200), "4.20");
        assert_eq!(volts(0), "0.00");
    }

    #[test]
    fn missing_values_use_dashes() {
        assert_eq!(with_unit(None::<u8>, " %"), "-- %");
        assert_eq!(with_unit(Some(45), " %"), "45 %");
        assert_eq!(battery_percent(103), 100);
    }
}
