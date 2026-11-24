//! The four screens: main, device info, charge-me and blank.

use core::fmt::Write;

use embedded_graphics::Drawable;
use embedded_graphics::pixelcolor::BinaryColor;
use embedded_graphics::prelude::{DrawTarget, Point, Primitive, Size};
use embedded_graphics::primitives::{PrimitiveStyle, Rectangle};
use heapless::Vec;
use pocket_logic::{Battery, InfoView, MainView, TempStatus, View, WakeCause};
use u8g2_fonts::types::{FontColor, HorizontalAlignment, VerticalPosition};
use u8g2_fonts::{FontRenderer, fonts};

use crate::format::{self, Text};
use crate::frame::WIDTH;

const MARGIN: i32 = 8;
const LEFT: i32 = MARGIN;
const RIGHT: i32 = WIDTH as i32 - MARGIN;
const CENTER: i32 = WIDTH as i32 / 2;

/// Temperature digits: 50 px tall, digits, '-' and '.' only.
pub(crate) const TEMP_FONT: FontRenderer = FontRenderer::new::<fonts::u8g2_font_logisoso50_tn>();
/// "°C" next to the temperature.
pub(crate) const UNIT_FONT: FontRenderer = FontRenderer::new::<fonts::u8g2_font_fub20_tf>();
/// Values on the main screen rows.
pub(crate) const VALUE_FONT: FontRenderer = FontRenderer::new::<fonts::u8g2_font_fub17_tr>();
/// Row labels.
pub(crate) const LABEL_FONT: FontRenderer = FontRenderer::new::<fonts::u8g2_font_helvR12_tr>();
/// Values on the info screen and the status bar.
pub(crate) const BOLD_FONT: FontRenderer = FontRenderer::new::<fonts::u8g2_font_helvB12_tr>();
/// Title of the info screen and the lines under "Charge me".
pub(crate) const TITLE_FONT: FontRenderer = FontRenderer::new::<fonts::u8g2_font_helvB14_tr>();
/// "Charge me".
pub(crate) const BIG_FONT: FontRenderer = FontRenderer::new::<fonts::u8g2_font_fub25_tr>();

// Main screen, top to bottom.
const TEMP_TOP: i32 = MARGIN;
const UNIT_GAP: i32 = 4;
const STATUS_BAR: Rectangle = Rectangle::new(Point::new(0, 68), Size::new(WIDTH, 24));
const MAIN_RULE_Y: i32 = 100;
const MAIN_ROW_BASELINES: [i32; 3] = [132, 162, 192];

// Info screen.
const INFO_TITLE_TOP: i32 = MARGIN;
const INFO_RULE_Y: i32 = 30;
const INFO_FIRST_BASELINE: i32 = 54;
const INFO_ROW_STEP: i32 = 22;

// Charge-me screen.
const CHARGE_BASELINES: [i32; 3] = [86, 128, 154];

/// Drawing failed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error<E> {
    /// The draw target reported an error.
    Display(E),
    /// A font lacks a character the screen needed (a bug in this crate).
    MissingGlyph(char),
    /// Text with a background colour was asked of a font without one (a bug
    /// in this crate: all text here is drawn transparent).
    BackgroundNotSupported,
}

impl<E> From<u8g2_fonts::Error<E>> for Error<E> {
    fn from(error: u8g2_fonts::Error<E>) -> Self {
        match error {
            u8g2_fonts::Error::DisplayError(error) => Self::Display(error),
            u8g2_fonts::Error::GlyphNotFound(c) => Self::MissingGlyph(c),
            u8g2_fonts::Error::BackgroundColorNotSupported => Self::BackgroundNotSupported,
        }
    }
}

impl<E: core::fmt::Debug> core::fmt::Display for Error<E> {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            Self::Display(error) => write!(f, "display error: {error:?}"),
            Self::MissingGlyph(c) => write!(f, "font has no glyph for {c:?}"),
            Self::BackgroundNotSupported => write!(f, "font does not support a background colour"),
        }
    }
}

impl<E: core::fmt::Debug> core::error::Error for Error<E> {}

/// Bounding boxes of everything a screen drew, for layout checks.
#[derive(Debug, Clone, Default)]
pub struct Drawn {
    boxes: Vec<Rectangle, 24>,
}

impl Drawn {
    /// One box per text, bar or rule, in drawing order.
    pub fn boxes(&self) -> &[Rectangle] {
        &self.boxes
    }

    fn add(&mut self, area: Rectangle) {
        // 24 is more than any screen draws; a full list only loses checks.
        let _ = self.boxes.push(area);
    }
}

/// Clears the target and draws `view` on it.
pub fn draw<D>(view: &View, target: &mut D) -> Result<Drawn, Error<D::Error>>
where
    D: DrawTarget<Color = BinaryColor>,
{
    target.clear(BinaryColor::Off).map_err(Error::Display)?;
    let mut painter = Painter {
        target,
        drawn: Drawn::default(),
    };
    match view {
        View::Main(main) => draw_main(&mut painter, main)?,
        View::Info(info) => draw_info(&mut painter, info)?,
        View::ChargeMe { millivolts } => draw_charge_me(&mut painter, *millivolts)?,
        View::Blank => {}
    }
    Ok(painter.drawn)
}

fn draw_main<D>(p: &mut Painter<'_, D>, view: &MainView) -> Result<(), Error<D::Error>>
where
    D: DrawTarget<Color = BinaryColor>,
{
    let readings = &view.readings;

    // Temperature: digits right-aligned against the unit, so the decimal
    // point stays put whatever the value.
    let unit_width = text_width(&UNIT_FONT, "°C")?;
    let unit_left = RIGHT - unit_width;
    p.text(
        &UNIT_FONT,
        "°C",
        Point::new(unit_left, TEMP_TOP),
        VerticalPosition::Top,
        HorizontalAlignment::Left,
    )?;
    let temperature = match readings.climate {
        Some(climate) => format::temperature(climate.temperature_millicelsius),
        None => Text::try_from("--.-").unwrap_or_default(),
    };
    p.text(
        &TEMP_FONT,
        temperature.as_str(),
        Point::new(unit_left - UNIT_GAP, TEMP_TOP),
        VerticalPosition::Top,
        HorizontalAlignment::Right,
    )?;

    if let Some(status) = status_text(view.temp_status) {
        p.fill(STATUS_BAR)?;
        BOLD_FONT.render_aligned(
            status.as_str(),
            STATUS_BAR.center(),
            VerticalPosition::Center,
            HorizontalAlignment::Center,
            FontColor::Transparent(BinaryColor::Off),
            p.target,
        )?;
    }

    p.rule(MAIN_RULE_Y)?;

    let humidity = readings
        .climate
        .map(|c| format::humidity_percent(c.humidity_hundredths));
    let pressure = readings.pressure_pa.map(format::pressure_hpa);
    let battery = readings.battery.map(|b| format::battery_percent(b.percent));
    let rows = [
        ("Humidity", format::with_unit(humidity, " %")),
        ("Pressure", format::with_unit(pressure, " hPa")),
        ("Battery", format::with_unit(battery, " %")),
    ];
    for ((label, value), baseline) in rows.iter().zip(MAIN_ROW_BASELINES) {
        p.row(label, &VALUE_FONT, value, baseline)?;
    }
    Ok(())
}

fn draw_info<D>(p: &mut Painter<'_, D>, view: &InfoView) -> Result<(), Error<D::Error>>
where
    D: DrawTarget<Color = BinaryColor>,
{
    p.text(
        &TITLE_FONT,
        "Device info",
        Point::new(LEFT, INFO_TITLE_TOP),
        VerticalPosition::Top,
        HorizontalAlignment::Left,
    )?;
    p.rule(INFO_RULE_Y)?;

    let readings = &view.readings;
    let rows: [(&str, Text); 7] = [
        ("Battery", battery_text(readings.battery)),
        ("Charging", charging_text(view.usb, readings.battery)),
        ("T/RH", temp_status_short(view.temp_status)),
        ("SHT40", ok_text(readings.climate.is_some())),
        ("BMP580", ok_text(readings.pressure_pa.is_some())),
        (
            "Woke by",
            Text::try_from(wake_cause_text(view.wake_cause)).unwrap_or_default(),
        ),
        ("Version", truncated(view.firmware)),
    ];
    let mut baseline = INFO_FIRST_BASELINE;
    for (label, value) in &rows {
        p.row(label, &BOLD_FONT, value, baseline)?;
        baseline += INFO_ROW_STEP;
    }
    Ok(())
}

fn draw_charge_me<D>(p: &mut Painter<'_, D>, millivolts: u16) -> Result<(), Error<D::Error>>
where
    D: DrawTarget<Color = BinaryColor>,
{
    let mut battery = Text::new();
    let _ = write!(battery, "Battery {} V", format::volts(millivolts));
    let lines: [(&FontRenderer, &str); 3] = [
        (&BIG_FONT, "Charge me"),
        (&TITLE_FONT, battery.as_str()),
        (&TITLE_FONT, "Plug in USB-C"),
    ];
    for ((font, text), baseline) in lines.iter().zip(CHARGE_BASELINES) {
        p.text(
            font,
            text,
            Point::new(CENTER, baseline),
            VerticalPosition::Baseline,
            HorizontalAlignment::Center,
        )?;
    }
    Ok(())
}

/// Text for the bar under the temperature, `None` when the values are fine.
pub(crate) fn status_text(status: TempStatus) -> Option<Text> {
    let mut text = Text::new();
    match status {
        TempStatus::Reliable => return None,
        TempStatus::Charging => {
            let _ = write!(text, "T/RH unreliable: USB");
        }
        TempStatus::CoolingDown { minutes_left } => {
            let _ = write!(
                text,
                "T/RH unreliable: {} min",
                minutes_left.min(MAX_MINUTES_SHOWN)
            );
        }
    }
    Some(text)
}

fn temp_status_short(status: TempStatus) -> Text {
    let mut text = Text::new();
    let _ = match status {
        TempStatus::Reliable => write!(text, "ok"),
        TempStatus::Charging => write!(text, "USB heat"),
        TempStatus::CoolingDown { minutes_left } => {
            write!(text, "cooling {} min", minutes_left.min(MAX_MINUTES_SHOWN))
        }
    };
    text
}

fn battery_text(battery: Option<Battery>) -> Text {
    let mut text = Text::new();
    let _ = match battery {
        Some(b) => write!(
            text,
            "{} %  {} V",
            format::battery_percent(b.percent),
            format::volts(b.millivolts)
        ),
        None => write!(text, "{}", format::MISSING),
    };
    text
}

/// The board has no charge-status GPIO, so "charging" means USB present and
/// the gauge below 100 %.
fn charging_text(usb: bool, battery: Option<Battery>) -> Text {
    let full = battery.is_some_and(|b| b.percent >= 100);
    let text = match (usb, full) {
        (false, _) => "no",
        (true, false) => "yes",
        (true, true) => "full",
    };
    Text::try_from(text).unwrap_or_default()
}

fn ok_text(ok: bool) -> Text {
    Text::try_from(if ok { "ok" } else { "failed" }).unwrap_or_default()
}

fn wake_cause_text(cause: WakeCause) -> &'static str {
    match cause {
        WakeCause::Reset => "reset",
        WakeCause::ButtonUp => "UP button",
        WakeCause::ButtonOk => "OK button",
        WakeCause::Shake => "shake",
        WakeCause::UsbPlugged => "USB",
        WakeCause::BatteryAlert => "battery alert",
    }
}

/// Firmware versions longer than this are cut to fit the row.
pub(crate) const FIRMWARE_MAX_CHARS: usize = 10;

/// Cool-down minutes are shown up to this; the real cool-down is ~20 min.
const MAX_MINUTES_SHOWN: u16 = 99;

fn truncated(text: &str) -> Text {
    let mut out = Text::new();
    for c in text.chars().take(FIRMWARE_MAX_CHARS) {
        let _ = out.push(c);
    }
    out
}

pub(crate) fn text_width<E>(font: &FontRenderer, text: &str) -> Result<i32, Error<E>> {
    let area = font
        .get_rendered_dimensions(text, Point::zero(), VerticalPosition::Baseline)
        .map_err(|u8g2_fonts::LookupError::GlyphNotFound(c)| Error::MissingGlyph(c))?;
    Ok(area.advance.x)
}

/// Draws onto the target and records what went where.
struct Painter<'a, D> {
    target: &'a mut D,
    drawn: Drawn,
}

impl<D> Painter<'_, D>
where
    D: DrawTarget<Color = BinaryColor>,
{
    fn text(
        &mut self,
        font: &FontRenderer,
        text: &str,
        at: Point,
        vertical: VerticalPosition,
        horizontal: HorizontalAlignment,
    ) -> Result<(), Error<D::Error>> {
        let area = font.render_aligned(
            text,
            at,
            vertical,
            horizontal,
            FontColor::Transparent(BinaryColor::On),
            self.target,
        )?;
        if let Some(area) = area {
            self.drawn.add(area);
        }
        Ok(())
    }

    /// Label on the left margin, value right-aligned on the right margin.
    fn row(
        &mut self,
        label: &str,
        value_font: &FontRenderer,
        value: &str,
        baseline: i32,
    ) -> Result<(), Error<D::Error>> {
        self.text(
            &LABEL_FONT,
            label,
            Point::new(LEFT, baseline),
            VerticalPosition::Baseline,
            HorizontalAlignment::Left,
        )?;
        self.text(
            value_font,
            value,
            Point::new(RIGHT, baseline),
            VerticalPosition::Baseline,
            HorizontalAlignment::Right,
        )
    }

    fn fill(&mut self, area: Rectangle) -> Result<(), Error<D::Error>> {
        area.into_styled(PrimitiveStyle::with_fill(BinaryColor::On))
            .draw(self.target)
            .map_err(Error::Display)?;
        self.drawn.add(area);
        Ok(())
    }

    /// A 2 px horizontal rule between the margins, `y` its top row.
    fn rule(&mut self, y: i32) -> Result<(), Error<D::Error>> {
        let area = Rectangle::new(Point::new(LEFT, y), Size::new((RIGHT - LEFT) as u32, 2));
        self.fill(area)
    }
}
