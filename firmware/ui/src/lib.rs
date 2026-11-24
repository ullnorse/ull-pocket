//! ull-pocket screens.
//!
//! [`draw`] turns a [`pocket_logic::View`] into pixels on any
//! embedded-graphics target with `BinaryColor` (`On` = black ink). [`Frame`]
//! is the 200x200 1-bit buffer in the SSD1681's RAM layout that the app sends
//! to the panel. Coordinates are as the user sees the screen; the panel
//! driver handles the panel's mounting rotation.

#![cfg_attr(not(test), no_std)]

mod format;
mod frame;
pub mod samples;
mod screens;

#[cfg(test)]
mod tests;

pub use frame::{Frame, HEIGHT, WIDTH};
pub use screens::{Drawn, Error, draw};
