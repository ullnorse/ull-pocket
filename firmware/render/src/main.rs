//! Renders every sample screen to `renders/<name>.png` at 3x scale.
//!
//! Run from `firmware/`: `cargo run -p pocket-render`. An optional argument
//! sets the output directory.

use std::fs::File;
use std::io::BufWriter;
use std::path::{Path, PathBuf};

use pocket_ui::{Frame, HEIGHT, WIDTH, draw, samples};

/// Each panel pixel becomes a SCALE x SCALE block.
const SCALE: u32 = 3;

fn main() -> Result<(), Box<dyn core::error::Error>> {
    let out_dir = std::env::args()
        .nth(1)
        .map(PathBuf::from)
        .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")).join("../renders"));
    std::fs::create_dir_all(&out_dir)?;

    for (name, view) in samples::ALL {
        let mut frame = Frame::new();
        draw(&view, &mut frame).map_err(|error| format!("{name}: {error}"))?;
        let path = out_dir.join(format!("{name}.png"));
        write_png(&frame, &path)?;
        println!("{}", path.display());
    }
    Ok(())
}

/// Writes the frame as an 8-bit greyscale PNG, black ink on white.
fn write_png(frame: &Frame, path: &Path) -> Result<(), Box<dyn core::error::Error>> {
    let width = WIDTH * SCALE;
    let height = HEIGHT * SCALE;
    let mut pixels = Vec::with_capacity((width * height) as usize);
    for y in 0..height {
        for x in 0..width {
            let black = frame.is_black(x / SCALE, y / SCALE);
            pixels.push(if black { 0 } else { 255 });
        }
    }

    let mut encoder = png::Encoder::new(BufWriter::new(File::create(path)?), width, height);
    encoder.set_color(png::ColorType::Grayscale);
    encoder.set_depth(png::BitDepth::Eight);
    encoder.write_header()?.write_image_data(&pixels)?;
    Ok(())
}
