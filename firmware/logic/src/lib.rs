//! Wake and decision logic for ull-pocket.
//!
//! The firmware runs one pass per wake: it builds a [`Pocket`] from the wake
//! cause and the [`SavedState`] kept in RTC memory, then feeds it [`Event`]s
//! (button presses, sensor results, USB changes, timeouts). Every call returns
//! an [`Output`]: whether to read the sensors, what to draw, and whether to
//! wait for the next event (and until when) or go to deep sleep with which
//! wake sources.
//!
//! Nothing here touches hardware or reads a clock: the caller passes the RTC
//! time in milliseconds with every call. So the crate is `no_std`, has no
//! dependencies and is tested on the PC.

#![cfg_attr(not(test), no_std)]

pub mod config;
mod pocket;
mod saved;
mod types;

#[cfg(test)]
mod tests;

pub use pocket::Pocket;
pub use saved::SavedState;
pub use types::{
    Battery, Button, Climate, Event, InfoView, MainView, Next, Output, Readings, TempStatus, View,
    Wake, WakeCause, WakeSources,
};
