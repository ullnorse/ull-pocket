//! State kept in RTC memory across deep sleep.

use crate::config::COOL_DOWN_MS;

/// The only thing one wake needs from the previous one.
///
/// 8 bytes in memory. The app stores it as `[u8; SavedState::ENCODED_LEN]`
/// (12 bytes) in RTC memory, because after a power-on that memory holds
/// garbage and a byte array is valid for any content; `decode` rejects
/// garbage and the app then uses `SavedState::default()`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct SavedState {
    /// RTC time until which temperature and humidity are marked unreliable
    /// after USB was unplugged. 0 means no cool-down.
    pub warm_until_ms: u64,
}

const MAGIC: [u8; 2] = *b"UP";
const FORMAT_VERSION: u8 = 1;

impl SavedState {
    /// Size of the encoded form: magic (2), format version (1), checksum (1),
    /// `warm_until_ms` little-endian (8).
    pub const ENCODED_LEN: usize = 12;

    pub fn encode(self) -> [u8; Self::ENCODED_LEN] {
        let payload = self.warm_until_ms.to_le_bytes();
        let mut bytes = [0; Self::ENCODED_LEN];
        bytes[0..2].copy_from_slice(&MAGIC);
        bytes[2] = FORMAT_VERSION;
        bytes[3] = checksum(&payload);
        bytes[4..12].copy_from_slice(&payload);
        bytes
    }

    /// `None` when the bytes are not a saved state of this format (first
    /// power-on, or a firmware with a different layout).
    pub fn decode(bytes: &[u8; Self::ENCODED_LEN]) -> Option<Self> {
        let mut payload = [0; 8];
        payload.copy_from_slice(&bytes[4..12]);
        let valid =
            bytes[0..2] == MAGIC && bytes[2] == FORMAT_VERSION && bytes[3] == checksum(&payload);
        valid.then(|| Self {
            warm_until_ms: u64::from_le_bytes(payload),
        })
    }

    /// Fixes a cool-down end that lies further ahead than a whole cool-down,
    /// which means the RTC clock restarted while RTC memory survived. The
    /// cool-down then restarts from now, the safe side.
    pub(crate) fn checked(self, now_ms: u64) -> Self {
        let latest = now_ms.saturating_add(COOL_DOWN_MS);
        Self {
            warm_until_ms: self.warm_until_ms.min(latest),
        }
    }
}

fn checksum(payload: &[u8; 8]) -> u8 {
    payload
        .iter()
        .fold(0xA5, |sum: u8, byte| sum.rotate_left(1) ^ byte)
}
