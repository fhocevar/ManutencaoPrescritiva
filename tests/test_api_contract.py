from app.presentation.api.schemas import EventRequest


def test_event_request_accepts_sample_dict():
    payload = {
        "id": 1,
        "created_at": "2026-06-01T21:32:53.911176+00:00",
        "fault": "normal",
        "z_rms_velocity_in_s": 0.1,
        "z_rms_velocity_mm_s": 0.1,
        "temperature_f": 70,
        "temperature_c": 21,
        "x_rms_velocity_in_s": 0.1,
        "x_rms_velocity_mm_s": 0.1,
        "z_peak_acceleration_g": 0.1,
        "x_peak_acceleration_g": 0.1,
        "z_peak_vel_comp_freq_hz": 60,
        "x_peak_vel_comp_freq_hz": 60,
        "z_rms_acceleration_g": 0.1,
        "x_rms_acceleration_g": 0.1,
        "z_kurtosis": 2,
        "x_kurtosis": 2,
        "z_crest_factor": 3,
        "x_crest_factor": 3,
        "z_peak_velocity_in_s": 0.1,
        "z_peak_velocity_mm_s": 0.1,
        "x_peak_velocity_in_s": 0.1,
        "x_peak_velocity_mm_s": 0.1,
        "z_high_freq_rms_accel_g": 0.1,
        "x_high_freq_rms_accel_g": 0.1,
        "rpm": 1000,
    }
    assert EventRequest(**payload).to_domain().fault == "normal"
