use crate::config::{COOL_DOWN_MS, IDLE_TIMEOUT_MS, LOW_BATTERY_MV};
use crate::*;

const FW: &str = "0.1.0";
const T0: u64 = 1_000_000;

fn good_readings() -> Readings {
    Readings {
        climate: Some(Climate {
            temperature_millicelsius: 21_560,
            humidity_hundredths: 4_512,
        }),
        pressure_pa: Some(101_325),
        battery: Some(Battery {
            millivolts: 3_900,
            percent: 80,
        }),
    }
}

fn readings_with_battery(millivolts: u16) -> Readings {
    Readings {
        battery: Some(Battery {
            millivolts,
            percent: 5,
        }),
        ..good_readings()
    }
}

fn wake_with(cause: WakeCause, usb_present: bool, saved: SavedState) -> (Pocket, Output) {
    Pocket::wake(Wake {
        cause,
        now_ms: T0,
        usb_present,
        saved,
        firmware: FW,
    })
}

fn wake(cause: WakeCause) -> (Pocket, Output) {
    wake_with(cause, false, SavedState::default())
}

/// Wakes and delivers good readings at `T0`; returns the output of the readings.
fn awake_showing_main(cause: WakeCause, usb_present: bool) -> (Pocket, Output) {
    let (mut pocket, _) = wake_with(cause, usb_present, SavedState::default());
    let out = pocket.handle(Event::Readings(good_readings()), T0);
    (pocket, out)
}

fn reading_request(until_ms: u64) -> Output {
    Output {
        read_sensors: true,
        show: None,
        next: Next::Wait {
            until_ms: Some(until_ms),
        },
    }
}

fn shown(out: Output) -> View {
    out.show.expect("expected a view to draw")
}

fn is_main(view: View) -> bool {
    matches!(view, View::Main(_))
}

fn is_info(view: View) -> bool {
    matches!(view, View::Info(_))
}

fn main_view(out: Output) -> MainView {
    match shown(out) {
        View::Main(main) => main,
        other => panic!("expected main view, got {other:?}"),
    }
}

// ---- Wake causes ----

#[test]
fn every_wake_cause_starts_with_a_sensor_read() {
    for cause in [
        WakeCause::Reset,
        WakeCause::ButtonUp,
        WakeCause::ButtonOk,
        WakeCause::Shake,
        WakeCause::UsbPlugged,
        WakeCause::BatteryAlert,
    ] {
        let (_, out) = wake(cause);
        assert_eq!(out, reading_request(T0 + IDLE_TIMEOUT_MS), "{cause:?}");
    }
}

#[test]
fn deliberate_wakes_show_main_screen_after_readings() {
    for cause in [
        WakeCause::Reset,
        WakeCause::ButtonUp,
        WakeCause::ButtonOk,
        WakeCause::Shake,
    ] {
        let (_, out) = awake_showing_main(cause, false);
        let main = main_view(out);
        assert_eq!(main.readings, good_readings());
        assert_eq!(main.temp_status, TempStatus::Reliable);
        assert_eq!(
            out.next,
            Next::Wait {
                until_ms: Some(T0 + IDLE_TIMEOUT_MS)
            }
        );
    }
}

#[test]
fn usb_wake_shows_main_screen_marked_charging() {
    let (_, out) = awake_showing_main(WakeCause::UsbPlugged, true);
    assert_eq!(main_view(out).temp_status, TempStatus::Charging);
}

#[test]
fn usb_wake_with_usb_already_gone_starts_cool_down() {
    let (mut pocket, _) = wake_with(WakeCause::UsbPlugged, false, SavedState::default());
    let out = pocket.handle(Event::Readings(good_readings()), T0);
    assert_eq!(
        main_view(out).temp_status,
        TempStatus::CoolingDown { minutes_left: 20 }
    );
    assert_eq!(pocket.saved_state().warm_until_ms, T0 + COOL_DOWN_MS);
}

#[test]
fn battery_alert_wake_with_good_battery_sleeps_without_drawing() {
    let (mut pocket, _) = wake(WakeCause::BatteryAlert);
    let out = pocket.handle(Event::Readings(good_readings()), T0 + 20);
    assert_eq!(
        out,
        Output {
            read_sensors: false,
            show: None,
            next: Next::Sleep(WakeSources::NORMAL_NO_ALERT),
        }
    );
    let expected = WakeSources {
        battery_alert: false,
        ..WakeSources::NORMAL
    };
    assert_eq!(WakeSources::NORMAL_NO_ALERT, expected);
}

#[test]
fn battery_alert_wake_with_failed_gauge_sleeps_without_alert() {
    let (mut pocket, _) = wake(WakeCause::BatteryAlert);
    let readings = Readings {
        battery: None,
        ..good_readings()
    };
    let out = pocket.handle(Event::Readings(readings), T0 + 20);
    assert_eq!(out.show, None);
    assert_eq!(out.next, Next::Sleep(WakeSources::NORMAL_NO_ALERT));
}

#[test]
fn battery_alert_wake_with_low_battery_shows_charge_me() {
    let (mut pocket, _) = wake(WakeCause::BatteryAlert);
    let out = pocket.handle(Event::Readings(readings_with_battery(3_350)), T0 + 20);
    assert_eq!(out.show, Some(View::ChargeMe { millivolts: 3_350 }));
    assert_eq!(out.next, Next::Sleep(WakeSources::USB_ONLY));
}

#[test]
fn battery_alert_wake_becomes_normal_when_a_button_is_pressed() {
    let (mut pocket, _) = wake(WakeCause::BatteryAlert);
    pocket.handle(Event::Button(Button::Ok), T0 + 5);
    let out = pocket.handle(Event::Readings(good_readings()), T0 + 20);
    assert!(is_main(shown(out)));
}

#[test]
fn battery_alert_wake_on_usb_shows_main_screen() {
    let (_, out) = awake_showing_main(WakeCause::BatteryAlert, true);
    assert!(is_main(shown(out)));
}

// ---- Buttons ----

#[test]
fn up_and_down_toggle_between_main_and_info_without_reading() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);

    let out = pocket.handle(Event::Button(Button::Up), T0 + 1_000);
    assert!(!out.read_sensors);
    assert!(is_info(shown(out)));

    let out = pocket.handle(Event::Button(Button::Up), T0 + 2_000);
    assert!(is_main(shown(out)));

    let out = pocket.handle(Event::Button(Button::Down), T0 + 3_000);
    assert!(is_info(shown(out)));

    let out = pocket.handle(Event::Button(Button::Down), T0 + 4_000);
    assert!(is_main(shown(out)));
}

#[test]
fn info_view_carries_device_details() {
    let (mut pocket, _) = awake_showing_main(WakeCause::Shake, false);
    let out = pocket.handle(Event::Button(Button::Down), T0 + 1_000);
    assert_eq!(
        shown(out),
        View::Info(InfoView {
            readings: good_readings(),
            temp_status: TempStatus::Reliable,
            usb: false,
            wake_cause: WakeCause::Shake,
            firmware: FW,
        })
    );
}

#[test]
fn ok_takes_a_fresh_reading_and_keeps_the_page() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    pocket.handle(Event::Button(Button::Up), T0 + 1_000);

    let out = pocket.handle(Event::Button(Button::Ok), T0 + 2_000);
    assert_eq!(out, reading_request(T0 + 2_000 + IDLE_TIMEOUT_MS));

    let fresh = readings_with_battery(3_700);
    let out = pocket.handle(Event::Readings(fresh), T0 + 2_050);
    match shown(out) {
        View::Info(info) => assert_eq!(info.readings, fresh),
        other => panic!("expected info, got {other:?}"),
    }
}

#[test]
fn ok_on_main_shows_fresh_values() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    pocket.handle(Event::Button(Button::Ok), T0 + 1_000);
    let fresh = Readings {
        pressure_pa: Some(99_000),
        ..good_readings()
    };
    let out = pocket.handle(Event::Readings(fresh), T0 + 1_050);
    assert_eq!(main_view(out).readings.pressure_pa, Some(99_000));
}

#[test]
fn buttons_while_a_read_is_pending_only_extend_the_deadline() {
    let (mut pocket, _) = wake(WakeCause::ButtonUp);
    let out = pocket.handle(Event::Button(Button::Up), T0 + 10);
    assert_eq!(
        out,
        Output {
            read_sensors: false,
            show: None,
            next: Next::Wait {
                until_ms: Some(T0 + 10 + IDLE_TIMEOUT_MS)
            },
        }
    );
    // The readings then draw the main page, not info.
    let out = pocket.handle(Event::Readings(good_readings()), T0 + 20);
    assert!(is_main(shown(out)));
}

#[test]
fn every_button_press_restarts_the_idle_timer() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    let t1 = T0 + 25_000;
    let out = pocket.handle(Event::Button(Button::Up), t1);
    assert_eq!(
        out.next,
        Next::Wait {
            until_ms: Some(t1 + IDLE_TIMEOUT_MS)
        }
    );
    // The old deadline passing does nothing.
    let out = pocket.handle(Event::Timeout, T0 + IDLE_TIMEOUT_MS);
    assert_eq!(out.show, None);
    assert_eq!(
        out.next,
        Next::Wait {
            until_ms: Some(t1 + IDLE_TIMEOUT_MS)
        }
    );
}

// ---- Idle timeout ----

#[test]
fn idle_timeout_on_battery_blanks_and_sleeps() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    let out = pocket.handle(Event::Timeout, T0 + IDLE_TIMEOUT_MS);
    assert_eq!(
        out,
        Output {
            read_sensors: false,
            show: Some(View::Blank),
            next: Next::Sleep(WakeSources::NORMAL),
        }
    );
}

#[test]
fn idle_timeout_from_info_page_also_blanks_and_sleeps() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    pocket.handle(Event::Button(Button::Down), T0 + 1_000);
    let out = pocket.handle(Event::Timeout, T0 + 1_000 + IDLE_TIMEOUT_MS);
    assert_eq!(out.show, Some(View::Blank));
    assert_eq!(out.next, Next::Sleep(WakeSources::NORMAL));
}

#[test]
fn early_timeout_is_ignored() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    let out = pocket.handle(Event::Timeout, T0 + IDLE_TIMEOUT_MS - 1);
    assert_eq!(out.show, None);
    assert_eq!(
        out.next,
        Next::Wait {
            until_ms: Some(T0 + IDLE_TIMEOUT_MS)
        }
    );
}

#[test]
fn readings_that_never_arrive_still_end_in_blank_and_sleep() {
    let (mut pocket, _) = wake(WakeCause::ButtonOk);
    let out = pocket.handle(Event::Timeout, T0 + IDLE_TIMEOUT_MS);
    assert_eq!(out.show, Some(View::Blank));
    assert_eq!(out.next, Next::Sleep(WakeSources::NORMAL));
}

#[test]
fn idle_timeout_on_usb_blanks_but_stays_awake_without_deadline() {
    let (mut pocket, _) = awake_showing_main(WakeCause::UsbPlugged, true);
    let out = pocket.handle(Event::Timeout, T0 + IDLE_TIMEOUT_MS);
    assert_eq!(
        out,
        Output {
            read_sensors: false,
            show: Some(View::Blank),
            next: Next::Wait { until_ms: None },
        }
    );
    // A spurious second timeout does nothing.
    let out = pocket.handle(Event::Timeout, T0 + 10 * IDLE_TIMEOUT_MS);
    assert_eq!(out.show, None);
    assert_eq!(out.next, Next::Wait { until_ms: None });
}

#[test]
fn any_button_on_blank_usb_screen_reads_and_shows_main() {
    for button in [Button::Up, Button::Ok, Button::Down] {
        let (mut pocket, _) = awake_showing_main(WakeCause::UsbPlugged, true);
        pocket.handle(Event::Button(Button::Down), T0 + 1_000); // go to info
        pocket.handle(Event::Timeout, T0 + 1_000 + IDLE_TIMEOUT_MS);

        let t = T0 + 600_000;
        let out = pocket.handle(Event::Button(button), t);
        assert_eq!(out, reading_request(t + IDLE_TIMEOUT_MS), "{button:?}");
        let out = pocket.handle(Event::Readings(good_readings()), t + 30);
        assert!(is_main(shown(out)), "{button:?}");
    }
}

// ---- USB while awake ----

#[test]
fn usb_plug_in_while_awake_reads_and_marks_charging() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    let t = T0 + 5_000;
    let out = pocket.handle(Event::UsbChanged(true), t);
    assert_eq!(out, reading_request(t + IDLE_TIMEOUT_MS));
    let out = pocket.handle(Event::Readings(good_readings()), t + 30);
    assert_eq!(main_view(out).temp_status, TempStatus::Charging);
    // And it no longer sleeps on timeout.
    let out = pocket.handle(Event::Timeout, t + IDLE_TIMEOUT_MS);
    assert_eq!(out.next, Next::Wait { until_ms: None });
}

#[test]
fn usb_unplug_while_awake_starts_cool_down_and_sleep_returns() {
    let (mut pocket, _) = awake_showing_main(WakeCause::UsbPlugged, true);
    let t = T0 + 3_600_000;
    let out = pocket.handle(Event::UsbChanged(false), t);
    assert_eq!(out, reading_request(t + IDLE_TIMEOUT_MS));
    assert_eq!(pocket.saved_state().warm_until_ms, t + COOL_DOWN_MS);

    let out = pocket.handle(Event::Readings(good_readings()), t + 30);
    assert_eq!(
        main_view(out).temp_status,
        TempStatus::CoolingDown { minutes_left: 20 }
    );
    let out = pocket.handle(Event::Timeout, t + IDLE_TIMEOUT_MS);
    assert_eq!(out.show, Some(View::Blank));
    assert_eq!(out.next, Next::Sleep(WakeSources::NORMAL));
}

#[test]
fn usb_unplug_while_blank_on_usb_reads_and_shows_main() {
    let (mut pocket, _) = awake_showing_main(WakeCause::UsbPlugged, true);
    pocket.handle(Event::Timeout, T0 + IDLE_TIMEOUT_MS);
    let t = T0 + 100_000;
    let out = pocket.handle(Event::UsbChanged(false), t);
    assert!(out.read_sensors);
    let out = pocket.handle(Event::Readings(good_readings()), t + 30);
    assert!(is_main(shown(out)));
}

#[test]
fn repeated_usb_state_is_ignored() {
    let (mut pocket, _) = awake_showing_main(WakeCause::UsbPlugged, true);
    let out = pocket.handle(Event::UsbChanged(true), T0 + 1_000);
    assert!(!out.read_sensors);
    assert_eq!(out.show, None);
    assert_eq!(pocket.saved_state(), SavedState::default());
}

#[test]
fn usb_bounce_restarts_cool_down_from_last_unplug() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    pocket.handle(Event::UsbChanged(true), T0 + 1_000);
    pocket.handle(Event::UsbChanged(false), T0 + 2_000);
    pocket.handle(Event::UsbChanged(true), T0 + 3_000);
    pocket.handle(Event::UsbChanged(false), T0 + 4_000);
    assert_eq!(
        pocket.saved_state().warm_until_ms,
        T0 + 4_000 + COOL_DOWN_MS
    );
}

// ---- Cool-down across sleeps ----

#[test]
fn cool_down_carries_over_deep_sleep_and_counts_down() {
    let unplugged = T0;
    let saved = SavedState {
        warm_until_ms: unplugged + COOL_DOWN_MS,
    };
    let cases = [
        (unplugged + 1, TempStatus::CoolingDown { minutes_left: 20 }),
        (
            unplugged + 60_000,
            TempStatus::CoolingDown { minutes_left: 19 },
        ),
        (
            unplugged + 60_001,
            TempStatus::CoolingDown { minutes_left: 19 },
        ),
        (
            unplugged + COOL_DOWN_MS - 1,
            TempStatus::CoolingDown { minutes_left: 1 },
        ),
        (unplugged + COOL_DOWN_MS, TempStatus::Reliable),
        (unplugged + 10 * COOL_DOWN_MS, TempStatus::Reliable),
    ];
    for (now_ms, expected) in cases {
        let (mut pocket, _) = Pocket::wake(Wake {
            cause: WakeCause::ButtonUp,
            now_ms,
            usb_present: false,
            saved,
            firmware: FW,
        });
        let out = pocket.handle(Event::Readings(good_readings()), now_ms);
        assert_eq!(main_view(out).temp_status, expected, "at {now_ms}");
    }
}

#[test]
fn cool_down_ends_while_awake() {
    let saved = SavedState {
        warm_until_ms: T0 + 10_000,
    };
    let (mut pocket, _) = wake_with(WakeCause::ButtonOk, false, saved);
    let out = pocket.handle(Event::Readings(good_readings()), T0 + 10);
    assert_eq!(
        main_view(out).temp_status,
        TempStatus::CoolingDown { minutes_left: 1 }
    );
    pocket.handle(Event::Button(Button::Ok), T0 + 15_000);
    let out = pocket.handle(Event::Readings(good_readings()), T0 + 15_050);
    assert_eq!(main_view(out).temp_status, TempStatus::Reliable);
}

#[test]
fn saved_cool_down_beyond_one_period_is_clamped_after_a_clock_restart() {
    // RTC memory survived but the clock restarted near zero.
    let saved = SavedState {
        warm_until_ms: 50 * COOL_DOWN_MS,
    };
    let (pocket, _) = Pocket::wake(Wake {
        cause: WakeCause::Reset,
        now_ms: 5_000,
        usb_present: false,
        saved,
        firmware: FW,
    });
    assert_eq!(pocket.saved_state().warm_until_ms, 5_000 + COOL_DOWN_MS);
}

#[test]
fn usb_present_overrides_cool_down() {
    let saved = SavedState {
        warm_until_ms: T0 + 60_000,
    };
    let (mut pocket, _) = wake_with(WakeCause::UsbPlugged, true, saved);
    let out = pocket.handle(Event::Readings(good_readings()), T0);
    assert_eq!(main_view(out).temp_status, TempStatus::Charging);
}

// ---- Low battery ----

#[test]
fn low_battery_on_wake_shows_charge_me_and_sleeps_usb_only() {
    let (mut pocket, _) = wake(WakeCause::ButtonUp);
    let out = pocket.handle(
        Event::Readings(readings_with_battery(LOW_BATTERY_MV - 1)),
        T0,
    );
    assert_eq!(
        out,
        Output {
            read_sensors: false,
            show: Some(View::ChargeMe {
                millivolts: LOW_BATTERY_MV - 1
            }),
            next: Next::Sleep(WakeSources::USB_ONLY),
        }
    );
    let usb_only = WakeSources::USB_ONLY;
    assert!(usb_only.usb_plug);
    assert!(!usb_only.button_up && !usb_only.button_ok && !usb_only.shake);
    assert!(!usb_only.battery_alert);
}

#[test]
fn battery_exactly_at_cut_off_is_still_usable() {
    let (mut pocket, _) = wake(WakeCause::ButtonUp);
    let out = pocket.handle(Event::Readings(readings_with_battery(LOW_BATTERY_MV)), T0);
    assert!(is_main(shown(out)));
}

#[test]
fn low_battery_found_by_ok_refresh_shows_charge_me() {
    let (mut pocket, _) = awake_showing_main(WakeCause::ButtonOk, false);
    pocket.handle(Event::Button(Button::Ok), T0 + 1_000);
    let out = pocket.handle(Event::Readings(readings_with_battery(3_300)), T0 + 1_050);
    assert_eq!(out.show, Some(View::ChargeMe { millivolts: 3_300 }));
    assert_eq!(out.next, Next::Sleep(WakeSources::USB_ONLY));
}

#[test]
fn low_voltage_reading_on_usb_does_not_lock_out() {
    let (mut pocket, _) = wake_with(WakeCause::UsbPlugged, true, SavedState::default());
    let out = pocket.handle(Event::Readings(readings_with_battery(3_200)), T0);
    assert!(is_main(shown(out)));
}

#[test]
fn low_battery_after_unplug_shows_charge_me() {
    let (mut pocket, _) = awake_showing_main(WakeCause::UsbPlugged, true);
    pocket.handle(Event::UsbChanged(false), T0 + 1_000);
    let out = pocket.handle(Event::Readings(readings_with_battery(3_350)), T0 + 1_050);
    assert_eq!(out.next, Next::Sleep(WakeSources::USB_ONLY));
}

// ---- Sensor failures ----

#[test]
fn failed_sensors_still_show_main_screen_with_gaps() {
    let (mut pocket, _) = wake(WakeCause::ButtonOk);
    let out = pocket.handle(Event::Readings(Readings::default()), T0);
    let main = main_view(out);
    assert_eq!(main.readings, Readings::default());
    assert_eq!(
        out.next,
        Next::Wait {
            until_ms: Some(T0 + IDLE_TIMEOUT_MS)
        }
    );
}

#[test]
fn failed_gauge_never_triggers_charge_me() {
    let (mut pocket, _) = wake(WakeCause::ButtonOk);
    let readings = Readings {
        battery: None,
        ..good_readings()
    };
    let out = pocket.handle(Event::Readings(readings), T0);
    assert!(is_main(shown(out)));
}

#[test]
fn one_failed_sensor_keeps_the_others() {
    let (mut pocket, _) = wake(WakeCause::ButtonOk);
    let readings = Readings {
        climate: None,
        ..good_readings()
    };
    let out = pocket.handle(Event::Readings(readings), T0);
    let main = main_view(out);
    assert_eq!(main.readings.climate, None);
    assert_eq!(main.readings.pressure_pa, Some(101_325));
}

// ---- Saved state ----

#[test]
fn saved_state_round_trips_through_bytes() {
    for warm_until_ms in [0, 1, T0 + COOL_DOWN_MS, u64::MAX] {
        let state = SavedState { warm_until_ms };
        assert_eq!(SavedState::decode(&state.encode()), Some(state));
    }
}

#[test]
fn saved_state_rejects_garbage() {
    assert_eq!(SavedState::decode(&[0; SavedState::ENCODED_LEN]), None);
    assert_eq!(SavedState::decode(&[0xFF; SavedState::ENCODED_LEN]), None);

    let good = SavedState {
        warm_until_ms: 1234,
    }
    .encode();
    for index in 0..SavedState::ENCODED_LEN {
        let mut bad = good;
        bad[index] ^= 0x01;
        assert_eq!(SavedState::decode(&bad), None, "flipped byte {index}");
    }
}

#[test]
fn saved_state_is_small() {
    assert_eq!(core::mem::size_of::<SavedState>(), 8);
    assert_eq!(SavedState::ENCODED_LEN, 12);
}

#[test]
fn wake_does_not_change_saved_state_by_itself() {
    let saved = SavedState {
        warm_until_ms: T0 + 1_000,
    };
    let (pocket, _) = wake_with(WakeCause::ButtonOk, false, saved);
    assert_eq!(pocket.saved_state(), saved);
}
