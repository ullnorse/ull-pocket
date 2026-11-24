//! The 1-bit frame buffer.

use core::convert::Infallible;

use embedded_graphics::pixelcolor::BinaryColor;
use embedded_graphics::prelude::{DrawTarget, OriginDimensions, Pixel, Size};

/// Panel width in pixels (GDEY0154D67).
pub const WIDTH: u32 = 200;
/// Panel height in pixels.
pub const HEIGHT: u32 = 200;

const BYTES_PER_ROW: usize = WIDTH as usize / 8;
const LEN: usize = BYTES_PER_ROW * HEIGHT as usize;

/// 200x200 pixels, 1 bit each: 5000 bytes, rows top to bottom, 8 pixels per
/// byte with the leftmost pixel in the most significant bit. A set bit is
/// white, as in the SSD1681's black/white RAM, so the bytes go to the panel
/// unchanged.
#[derive(Clone, PartialEq, Eq)]
pub struct Frame {
    bytes: [u8; LEN],
}

impl Frame {
    /// Size of the buffer in bytes.
    pub const LEN: usize = LEN;

    /// An all-white frame.
    pub const fn new() -> Self {
        Self { bytes: [0xFF; LEN] }
    }

    /// The bytes for the panel's RAM.
    pub fn as_bytes(&self) -> &[u8; LEN] {
        &self.bytes
    }

    /// `true` when the pixel is black. Out-of-range pixels read as white.
    pub fn is_black(&self, x: u32, y: u32) -> bool {
        if x >= WIDTH || y >= HEIGHT {
            return false;
        }
        let (index, mask) = locate(x, y);
        self.bytes[index] & mask == 0
    }

    fn set(&mut self, x: u32, y: u32, black: bool) {
        let (index, mask) = locate(x, y);
        if black {
            self.bytes[index] &= !mask;
        } else {
            self.bytes[index] |= mask;
        }
    }
}

impl Default for Frame {
    fn default() -> Self {
        Self::new()
    }
}

impl core::fmt::Debug for Frame {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.debug_struct("Frame").finish_non_exhaustive()
    }
}

fn locate(x: u32, y: u32) -> (usize, u8) {
    let index = y as usize * BYTES_PER_ROW + x as usize / 8;
    let mask = 0x80 >> (x % 8);
    (index, mask)
}

impl OriginDimensions for Frame {
    fn size(&self) -> Size {
        Size::new(WIDTH, HEIGHT)
    }
}

impl DrawTarget for Frame {
    type Color = BinaryColor;
    type Error = Infallible;

    fn draw_iter<I>(&mut self, pixels: I) -> Result<(), Self::Error>
    where
        I: IntoIterator<Item = Pixel<Self::Color>>,
    {
        for Pixel(point, color) in pixels {
            let (Ok(x), Ok(y)) = (u32::try_from(point.x), u32::try_from(point.y)) else {
                continue;
            };
            if x < WIDTH && y < HEIGHT {
                self.set(x, y, color.is_on());
            }
        }
        Ok(())
    }

    fn clear(&mut self, color: Self::Color) -> Result<(), Self::Error> {
        let fill = if color.is_on() { 0x00 } else { 0xFF };
        self.bytes = [fill; LEN];
        Ok(())
    }
}
