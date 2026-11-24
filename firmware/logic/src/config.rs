//! Tuning constants. The ones marked "measure" are guesses until the first
//! board is built.

/// Time with no input before the screen is blanked and the device sleeps.
pub const IDLE_TIMEOUT_MS: u64 = 30_000;

/// How long temperature and humidity stay marked unreliable after USB is
/// unplugged (board heat from charging). Measure on the first board.
pub const COOL_DOWN_MS: u64 = 20 * 60_000;

/// Below this cell voltage (MAX17048 reading, on battery) the device shows
/// "charge me" and sleeps with only USB as a wake source. The app should set
/// the MAX17048 voltage alert (VALRT.MIN) to the same value.
pub const LOW_BATTERY_MV: u16 = 3_400;

/// LIS2DW12 wake-up threshold for a firm shake, in milli-g. Measure on the
/// board so walking with the device in a pocket does not wake it. The app
/// converts it to WAKE_THS units for the full scale it picks (at +-4 g one
/// LSB is 62.5 mg, so 2000 mg = 32).
pub const SHAKE_THRESHOLD_MG: u16 = 2_000;
