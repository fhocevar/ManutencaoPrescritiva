NORMAL_STATES = frozenset({"normal", "baseline", "teste", "acelerando", "motor_desligado"})

SENSOR_FEATURES = (
    "z_rms_velocity_in_s",
    "z_rms_velocity_mm_s",
    "temperature_f",
    "temperature_c",
    "x_rms_velocity_in_s",
    "x_rms_velocity_mm_s",
    "z_peak_acceleration_g",
    "x_peak_acceleration_g",
    "z_peak_vel_comp_freq_hz",
    "x_peak_vel_comp_freq_hz",
    "z_rms_acceleration_g",
    "x_rms_acceleration_g",
    "z_kurtosis",
    "x_kurtosis",
    "z_crest_factor",
    "x_crest_factor",
    "z_peak_velocity_in_s",
    "z_peak_velocity_mm_s",
    "x_peak_velocity_in_s",
    "x_peak_velocity_mm_s",
    "z_high_freq_rms_accel_g",
    "x_high_freq_rms_accel_g",
    "rpm",
)

SENSOR_VECTOR_DIMENSION = len(SENSOR_FEATURES)
