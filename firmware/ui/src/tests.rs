use core::convert::Infallible;

use embedded_graphics::pixelcolor::BinaryColor;
use embedded_graphics::prelude::{DrawTarget, OriginDimensions, Pixel, Point, Size};
use embedded_graphics::primitives::Rectangle;
use pocket_logic::{InfoView, MainView, Readings, TempStatus, View, WakeCause};

use crate::screens::{BOLD_FONT, FIRMWARE_MAX_CHARS, status_text, text_width};
use crate::{Frame, HEIGHT, WIDTH, draw, samples};

/// A 200x200 target that remembers pixels drawn outside the screen and the
/// bounding box of the black ones.
#[derive(Default)]
struct Recorder {
    outside: usize,
    min: Option<Point>,
    max: Option<Point>,
}

impl OriginDimensions for Recorder {
    fn size(&self) -> Size {
        Size::new(WIDTH, HEIGHT)
    }
}

impl DrawTarget for Recorder {
    type Color = BinaryColor;
    type Error = Infallible;

    fn draw_iter<I>(&mut self, pixels: I) -> Result<(), Infallible>
    where
        I: IntoIterator<Item = Pixel<BinaryColor>>,
    {
        for Pixel(p, color) in pixels {
            if p.x < 0 || p.y < 0 || p.x >= WIDTH as i32 || p.y >= HEIGHT as i32 {
                self.outside += 1;
            }
            if color.is_on() {
                self.min = Some(
                    self.min
                        .map_or(p, |m| Point::new(m.x.min(p.x), m.y.min(p.y))),
                );
                self.max = Some(
                    self.max
                        .map_or(p, |m| Point::new(m.x.max(p.x), m.y.max(p.y))),
                );
            }
        }
        Ok(())
    }

    fn clear(&mut self, _color: BinaryColor) -> Result<(), Infallible> {
        Ok(())
    }
}

/// Content must keep this far from the edges (bezel, and so nothing touches it).
const EDGE: i32 = 4;

fn inside_screen(area: &Rectangle) -> bool {
    let Some(bottom_right) = area.bottom_right() else {
        return true;
    };
    area.top_left.x >= EDGE
        && area.top_left.y >= EDGE
        && bottom_right.x < WIDTH as i32 - EDGE
        && bottom_right.y < HEIGHT as i32 - EDGE
}

/// Minimum horizontal space between a label and its value.
const GAP: i32 = 6;

/// Boxes overlap, or sit closer than `GAP` side by side.
fn overlaps(a: &Rectangle, b: &Rectangle) -> bool {
    let widened = Rectangle::new(
        a.top_left - Point::new(GAP, 0),
        a.size + Size::new(2 * GAP as u32, 0),
    );
    !widened.intersection(b).is_zero_sized()
}

#[test]
fn frame_is_5000_bytes_and_starts_white() {
    let frame = Frame::new();
    assert_eq!(Frame::LEN, 5000);
    assert_eq!(frame.as_bytes().len(), 5000);
    assert!(frame.as_bytes().iter().all(|&b| b == 0xFF));
}

#[test]
fn frame_bit_layout_matches_ssd1681_ram() {
    let mut frame = Frame::new();
    frame
        .draw_iter([
            Pixel(Point::new(0, 0), BinaryColor::On),
            Pixel(Point::new(9, 0), BinaryColor::On),
            Pixel(Point::new(199, 199), BinaryColor::On),
            Pixel(Point::new(-1, 5), BinaryColor::On),
            Pixel(Point::new(200, 5), BinaryColor::On),
        ])
        .unwrap();
    let bytes = frame.as_bytes();
    assert_eq!(bytes[0], 0x7F); // x = 0 is the most significant bit
    assert_eq!(bytes[1], 0xBF); // x = 9 is bit 6 of byte 1
    assert_eq!(bytes[4999], 0xFE);
    assert_eq!(bytes.iter().filter(|&&b| b != 0xFF).count(), 3);
    assert!(frame.is_black(9, 0));
    assert!(!frame.is_black(10, 0));
}

#[test]
fn blank_view_is_all_white() {
    let mut frame = Frame::new();
    frame.clear(BinaryColor::On).unwrap();
    let drawn = draw(&View::Blank, &mut frame).unwrap();
    assert!(drawn.boxes().is_empty());
    assert_eq!(frame, Frame::new());
}

#[test]
fn every_sample_draws_without_errors() {
    for (name, view) in samples::ALL {
        let mut frame = Frame::new();
        let drawn = draw(&view, &mut frame);
        assert!(drawn.is_ok(), "{name}: {drawn:?}");
        let black = frame.as_bytes().iter().any(|&b| b != 0xFF);
        assert_eq!(black, view != View::Blank, "{name}");
    }
}

#[test]
fn nothing_is_drawn_outside_or_near_the_edge() {
    for (name, view) in samples::ALL {
        let mut recorder = Recorder::default();
        draw(&view, &mut recorder).unwrap();
        assert_eq!(recorder.outside, 0, "{name}: pixels outside the screen");
        if let (Some(min), Some(max)) = (recorder.min, recorder.max) {
            // Full-width bars may touch the sides, nothing may touch top or bottom.
            assert!(
                min.y >= EDGE && max.y < HEIGHT as i32 - EDGE,
                "{name}: {min:?}..{max:?}"
            );
        }
    }
}

#[test]
fn texts_fit_inside_margins_and_do_not_overlap() {
    for (name, view) in samples::ALL {
        let mut frame = Frame::new();
        let drawn = draw(&view, &mut frame).unwrap();
        let boxes = drawn.boxes();
        for (i, a) in boxes.iter().enumerate() {
            let full_width_bar = a.size.width == WIDTH;
            assert!(
                full_width_bar || inside_screen(a),
                "{name}: box {i} {a:?} too close to an edge"
            );
            for (j, b) in boxes.iter().enumerate().skip(i + 1) {
                assert!(
                    !overlaps(a, b),
                    "{name}: box {i} {a:?} overlaps box {j} {b:?}"
                );
            }
        }
    }
}

#[test]
fn status_bar_text_fits_for_any_cool_down() {
    let widest = status_text(TempStatus::CoolingDown {
        minutes_left: u16::MAX,
    })
    .unwrap();
    let width = text_width::<Infallible>(&BOLD_FONT, &widest).unwrap();
    assert!(width <= WIDTH as i32 - 2 * EDGE, "{widest}: {width} px");
    assert!(status_text(TempStatus::Reliable).is_none());
}

#[test]
fn long_firmware_version_is_cut_to_fit() {
    let view = View::Info(InfoView {
        readings: samples::ALL[0].1.readings(),
        temp_status: TempStatus::CoolingDown {
            minutes_left: u16::MAX,
        },
        usb: true,
        wake_cause: WakeCause::BatteryAlert,
        firmware: "0.10.100-rc.12+g1234567",
    });
    let mut frame = Frame::new();
    let drawn = draw(&view, &mut frame).unwrap();
    for (i, a) in drawn.boxes().iter().enumerate() {
        assert!(inside_screen(a), "box {i} {a:?}");
        for b in &drawn.boxes()[i + 1..] {
            assert!(!overlaps(a, b), "{a:?} overlaps {b:?}");
        }
    }
    assert_eq!(FIRMWARE_MAX_CHARS, 10);
}

#[test]
fn failed_sensors_show_dashes_not_zeros() {
    let failed = View::Main(MainView {
        readings: Readings::default(),
        temp_status: TempStatus::Reliable,
    });
    let zero = View::Main(MainView {
        readings: Readings {
            climate: Some(pocket_logic::Climate {
                temperature_millicelsius: 0,
                humidity_hundredths: 0,
            }),
            pressure_pa: Some(0),
            battery: Some(pocket_logic::Battery {
                millivolts: 0,
                percent: 0,
            }),
        },
        temp_status: TempStatus::Reliable,
    });
    let mut a = Frame::new();
    let mut b = Frame::new();
    draw(&failed, &mut a).unwrap();
    draw(&zero, &mut b).unwrap();
    assert_ne!(a, b);
}

/// Test helper: the readings inside a main or info sample.
trait SampleReadings {
    fn readings(&self) -> Readings;
}

impl SampleReadings for View {
    fn readings(&self) -> Readings {
        match self {
            View::Main(main) => main.readings,
            View::Info(info) => info.readings,
            _ => Readings::default(),
        }
    }
}
