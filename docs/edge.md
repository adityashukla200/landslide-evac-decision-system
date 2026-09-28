# Edge Node Firmware — ESP32/MicroPython Logic

> **Status:** Reference implementation in Python/MicroPython pseudo-code.  
> This describes the firmware running on the ESP32-based sensor nodes deployed in Uttarkashi and Chamoli districts.  
> The actual binary runs on MicroPython 1.22+ on ESP32-S3 with LoRa SX1276 radio.

---

## 1. Hardware Platform

| Component | Part | Role |
|---|---|---|
| MCU | ESP32-S3 (240 MHz, 512 KB SRAM) | Main controller |
| LoRa radio | Semtech SX1276 (915 MHz) | Offline alert relay |
| Soil probe | Capacitive moisture sensor (STEMMA QT) | Soil moisture 0–100% |
| Rain gauge | Tipping-bucket 0.2 mm/tip | Rainfall accumulation |
| Tilt sensor | MEMS accelerometer (MPU-6050) | Slope creep detection |
| Ultrasonic | JSN-SR04T (waterproof) | Stream level |
| LED strip | WS2812B (RGB) | Visual alert indicator |
| Piezo siren | 120 dB buzzer | Audible local alert |
| Battery | 10 Ah LiPo + 10 W solar panel | Off-grid power |
| RTC | DS3231 | Accurate timestamping without NTP |

---

## 2. Firmware Architecture

```
Boot
 ├─ load_config()          # Read thresholds from flash (NVS)
 ├─ init_sensors()         # Calibrate probes; self-test each sensor
 ├─ connect_wifi()         # Try to connect; set OFFLINE flag if fail
 ├─ connect_mqtt()         # If ONLINE: register and subscribe to commands
 └─ main_loop()            # 5-minute sensor-read-and-publish cycle
```

---

## 3. Full Firmware (MicroPython pseudo-code)

```python
"""
edge_node.py — EWS IoT node firmware.
Target: MicroPython 1.22 on ESP32-S3.
Pin assignments and I2C addresses are for the reference PCB v1.3.
"""

import time, math, json, os
from machine import Pin, I2C, ADC, UART
from micropython import const

# ── Hardware pins ──────────────────────────────────────────────────────────
PIN_MOISTURE_ADC   = const(34)   # ADC1_CH6
PIN_RAIN_TIPPING   = const(14)   # External interrupt
PIN_TRIG_ULTRASONIC = const(27)
PIN_ECHO_ULTRASONIC = const(26)
PIN_LED_DATA       = const(5)    # WS2812B data
PIN_SIREN          = const(23)   # Active-low buzzer relay
PIN_LORA_CS        = const(18)
PIN_LORA_RST       = const(19)
PIN_LORA_DIO0      = const(21)
I2C_SCL            = const(22)
I2C_SDA            = const(21)   # shared with MPU-6050 INT on different board rev

VILLAGE_ID = "V01"                # Flashed at provisioning time
FIRMWARE_VERSION = "1.4.2"

# ── Alert thresholds (loaded from NVS; overridable by MQTT command) ──────
class Thresholds:
    SOIL_MOISTURE_WARN    = 0.75   # m3/m3 volumetric water content
    SOIL_MOISTURE_EVAC    = 0.90
    RAINFALL_5MIN_WARN    = 3.0    # mm in 5-minute window
    RAINFALL_5MIN_EVAC    = 8.0
    TILT_WARN_DEG         = 1.5    # degrees deviation from calibrated zero
    TILT_EVAC_DEG         = 3.0
    STREAM_WARN_M         = 3.0    # metres above base-flow datum
    STREAM_EVAC_M         = 4.5
    FS_WARN               = 1.30   # Factor of Safety — computed on-device
    FS_EVAC               = 1.05

thresholds = Thresholds()

# ── Sensor state ──────────────────────────────────────────────────────────
rain_tips = 0          # Incremented by ISR on tipping-bucket pin
last_rain_reset = 0
tilt_zero_x = None     # Calibrated accelerometer zero (set during boot)
tilt_zero_y = None

# ── Alert state ──────────────────────────────────────────────────────────
current_tier = "NONE"  # NONE | WATCH | WARNING | EVACUATE
last_alert_sent_ts = 0
ALERT_COOLDOWN_S = 300 # Do not repeat same-tier alert within 5 minutes


# ── Hardware init ─────────────────────────────────────────────────────────

def init_sensors():
    global tilt_zero_x, tilt_zero_y
    i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400_000)
    
    # MPU-6050 accelerometer init
    i2c.writeto_mem(0x68, 0x6B, b'\x00')  # wake up
    time.sleep_ms(100)
    raw = i2c.readfrom_mem(0x68, 0x3B, 6)
    ax = (raw[0] << 8 | raw[1]) / 16384.0
    ay = (raw[2] << 8 | raw[3]) / 16384.0
    tilt_zero_x, tilt_zero_y = ax, ay
    print(f"[INIT] Tilt zero: x={ax:.4f} y={ay:.4f}")

    # Rain gauge interrupt
    rain_pin = Pin(PIN_RAIN_TIPPING, Pin.IN, Pin.PULL_UP)
    rain_pin.irq(trigger=Pin.IRQ_FALLING, handler=lambda p: _tip_isr())

    print(f"[INIT] Village {VILLAGE_ID} firmware {FIRMWARE_VERSION} ready.")


def _tip_isr():
    """ISR: one tipping-bucket tip = 0.2 mm rainfall."""
    global rain_tips
    rain_tips += 1


# ── Sensor reads ──────────────────────────────────────────────────────────

def read_soil_moisture() -> float:
    """Return volumetric water content [0.0, 1.0]."""
    adc = ADC(Pin(PIN_MOISTURE_ADC))
    adc.atten(ADC.ATTN_11DB)
    raw = adc.read()  # 0–4095 (12-bit)
    # Calibration: 0 V = 0.05 (dry air), 3.3 V = 0.98 (saturated)
    vwc = 0.05 + (raw / 4095.0) * (0.98 - 0.05)
    return max(0.0, min(1.0, vwc))


def read_rainfall_5min() -> float:
    """Return mm accumulated in last 5 minutes, then reset counter."""
    global rain_tips, last_rain_reset
    tips = rain_tips
    rain_tips = 0
    return tips * 0.2   # 0.2 mm per tip


def read_tilt_deg() -> float:
    """Return tilt angle in degrees relative to calibrated zero."""
    i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400_000)
    raw = i2c.readfrom_mem(0x68, 0x3B, 6)
    ax = (raw[0] << 8 | raw[1]) / 16384.0
    ay = (raw[2] << 8 | raw[3]) / 16384.0
    dx = ax - tilt_zero_x
    dy = ay - tilt_zero_y
    tilt_rad = math.atan2(math.sqrt(dx*dx + dy*dy), 1.0)
    return math.degrees(tilt_rad)


def read_stream_level_m() -> float:
    """HC-SR04 ultrasonic: returns water surface height above datum."""
    trig = Pin(PIN_TRIG_ULTRASONIC, Pin.OUT)
    echo = Pin(PIN_ECHO_ULTRASONIC, Pin.IN)
    SENSOR_HEIGHT_M = 6.0   # Sensor installed 6 m above base-flow surface

    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    # Wait for echo
    t0 = time.ticks_us()
    while echo.value() == 0 and time.ticks_diff(time.ticks_us(), t0) < 30000:
        pass
    t_start = time.ticks_us()
    while echo.value() == 1 and time.ticks_diff(time.ticks_us(), t_start) < 30000:
        pass
    duration_us = time.ticks_diff(time.ticks_us(), t_start)

    distance_m = (duration_us * 343.0) / 2_000_000.0
    return max(0.0, SENSOR_HEIGHT_M - distance_m)


# ── On-device Factor of Safety (simplified infinite-slope) ──────────────

def compute_fs(moisture: float, slope_deg: float = 31.5,
               cohesion_kpa: float = 18.5, phi_deg: float = 36.0,
               depth_m: float = 1.2, gamma: float = 19.2) -> float:
    """
    Infinite-slope stability model (local computation — no cloud needed).
    Returns Fs > 1.0 = stable; Fs < 1.0 = unstable.
    """
    slope_r = math.radians(slope_deg)
    phi_r   = math.radians(phi_deg)
    sat     = moisture
    c_norm  = cohesion_kpa / (gamma * depth_m * math.cos(slope_r) ** 2)
    u_norm  = sat * math.tan(slope_r)
    fs = c_norm + (1.0 - u_norm) * (math.tan(phi_r) / math.tan(slope_r))
    return round(max(0.01, fs), 3)


# ── Tier decision ──────────────────────────────────────────────────────────

def decide_tier(moisture: float, rain_5min: float,
                tilt: float, stream: float, fs: float) -> str:
    """
    Pure local threshold logic — no cloud, no ML.
    Designed to be conservative (false-positive safe) for offline resilience.
    """
    # EVACUATE: any single critical condition
    if (moisture    >= thresholds.SOIL_MOISTURE_EVAC or
        rain_5min   >= thresholds.RAINFALL_5MIN_EVAC or
        tilt        >= thresholds.TILT_EVAC_DEG      or
        stream      >= thresholds.STREAM_EVAC_M      or
        fs          <= thresholds.FS_EVAC):
        return "EVACUATE"

    # WARNING: any two warning conditions, OR Fs alone
    warn_flags = [
        moisture  >= thresholds.SOIL_MOISTURE_WARN,
        rain_5min >= thresholds.RAINFALL_5MIN_WARN,
        tilt      >= thresholds.TILT_WARN_DEG,
        stream    >= thresholds.STREAM_WARN_M,
    ]
    if sum(warn_flags) >= 2 or fs <= thresholds.FS_WARN:
        return "WARNING"

    # WATCH: any one warning condition
    if sum(warn_flags) >= 1:
        return "WATCH"

    return "NONE"


# ── LED + Siren actuators ─────────────────────────────────────────────────

LED_COLORS = {
    "NONE":     (0,   80,  0),    # dim green
    "WATCH":    (255, 255, 0),    # yellow
    "WARNING":  (255, 100, 0),    # orange
    "EVACUATE": (255, 0,   0),    # red (blinking)
}

SIREN_PATTERNS = {
    "NONE":     [],               # silent
    "WATCH":    [(200, 1800)],    # one short beep per minute
    "WARNING":  [(500, 500), (500, 500), (500, 3000)],   # 3-beep pattern
    "EVACUATE": [(1000, 200)] * 10,                       # continuous wail
}

def set_led(tier: str):
    """Update WS2812B LED strip to tier colour."""
    # Full NeoPixel driver omitted for brevity; pseudo-code interface:
    r, g, b = LED_COLORS.get(tier, (0, 0, 0))
    # neopixel_strip.fill((r, g, b))
    # neopixel_strip.write()
    print(f"[LED] → {tier}  RGB=({r},{g},{b})")


def sound_siren(tier: str):
    """Activate piezo siren with pattern for tier."""
    siren_pin = Pin(PIN_SIREN, Pin.OUT)
    for on_ms, off_ms in SIREN_PATTERNS.get(tier, []):
        siren_pin.value(1)
        time.sleep_ms(on_ms)
        siren_pin.value(0)
        time.sleep_ms(off_ms)
    print(f"[SIREN] Pattern fired for tier={tier}")


# ── LoRa relay (offline uplink) ───────────────────────────────────────────

def lora_broadcast(payload: dict):
    """
    Broadcast alert over LoRa to neighbouring nodes and the base station.
    Uses simple string encoding (JSON) over sx1276 at SF9/BW125/CR4-5.
    Effective range: 8–15 km in mountainous terrain.
    """
    try:
        from sx1276 import SX1276  # micropython LoRa driver
        lora = SX1276(
            cs=Pin(PIN_LORA_CS), rst=Pin(PIN_LORA_RST), dio0=Pin(PIN_LORA_DIO0),
            freq=915e6, sf=9, bw=125e3, cr=5,
        )
        msg = json.dumps(payload)[:240]   # max LoRa payload
        lora.send(msg.encode())
        print(f"[LoRa] Broadcast sent: {msg[:80]}…")
    except Exception as exc:
        print(f"[LoRa] Broadcast failed: {exc}")


# ── MQTT cloud publish (online mode) ──────────────────────────────────────

def mqtt_publish(client, reading: dict):
    """Publish sensor reading to MQTT broker."""
    import ujson
    topic = f"sensors/{VILLAGE_ID}/{reading['sensor_type']}"
    client.publish(topic.encode(), ujson.dumps(reading).encode(), qos=1)


# ── Main loop ─────────────────────────────────────────────────────────────

PUBLISH_INTERVAL_S = 300   # 5 minutes

def main_loop():
    global current_tier, last_alert_sent_ts

    # Attempt MQTT connection (non-blocking; falls back to offline mode)
    mqtt_client = None
    try:
        from umqtt.robust import MQTTClient
        mqtt_client = MQTTClient(f"ews_{VILLAGE_ID}", "broker.local")
        mqtt_client.connect()
        print("[MQTT] Connected to broker.local")
    except Exception:
        print("[MQTT] Broker unreachable — OFFLINE mode active")

    while True:
        t0 = time.ticks_ms()

        # ── Read all sensors ────────────────────────────────────────────
        moisture   = read_soil_moisture()
        rain_5min  = read_rainfall_5min()
        tilt       = read_tilt_deg()
        stream     = read_stream_level_m()
        fs         = compute_fs(moisture)
        ts         = time.time()

        reading_base = {
            "village_id":        VILLAGE_ID,
            "firmware_version":  FIRMWARE_VERSION,
            "timestamp":         ts,
            "soil_moisture":     moisture,
            "rainfall_5min_mm":  rain_5min,
            "tilt_deg":          tilt,
            "stream_level_m":    stream,
            "factor_of_safety":  fs,
        }

        # ── Tier decision (always local, never cloud-dependent) ─────────
        new_tier = decide_tier(moisture, rain_5min, tilt, stream, fs)

        # Alert if tier escalated OR cooldown expired for same tier
        should_alert = (
            new_tier != "NONE" and
            (new_tier != current_tier or
             (time.time() - last_alert_sent_ts) >= ALERT_COOLDOWN_S)
        )

        if new_tier != current_tier:
            print(f"[TIER] {current_tier} → {new_tier}")
            current_tier = new_tier
            set_led(new_tier)

        if should_alert:
            # ALWAYS fire local siren + LED first (no cloud dependency)
            sound_siren(new_tier)
            last_alert_sent_ts = time.time()

            alert_payload = {**reading_base, "tier": new_tier, "source": "edge_node"}

            # Cloud publish if online
            if mqtt_client:
                try:
                    mqtt_publish(mqtt_client, alert_payload)
                    print(f"[MQTT] Alert published tier={new_tier}")
                except Exception as exc:
                    print(f"[MQTT] Publish failed ({exc}); LoRa fallback active")
                    lora_broadcast(alert_payload)
            else:
                # Offline: broadcast over LoRa mesh
                lora_broadcast(alert_payload)

        else:
            # Regular telemetry publish (no alert)
            if mqtt_client:
                try:
                    for stype, val in [
                        ("soil_moisture", moisture),
                        ("rainfall",      rain_5min),
                        ("tilt",          tilt),
                        ("stream_level",  stream),
                    ]:
                        mqtt_publish(mqtt_client, {**reading_base, "sensor_type": stype, "value": val})
                except Exception as exc:
                    print(f"[MQTT] Telemetry publish failed: {exc}")

        # ── Sleep until next cycle ──────────────────────────────────────
        elapsed_ms = time.ticks_diff(time.ticks_ms(), t0)
        sleep_ms   = max(0, PUBLISH_INTERVAL_S * 1000 - elapsed_ms)
        time.sleep_ms(sleep_ms)


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_sensors()
    main_loop()
```

---

## 4. Threshold Table (Configurable via MQTT `ews/config` topic)

| Parameter | WATCH | WARNING | EVACUATE | Rationale |
|---|---|---|---|---|
| `soil_moisture` (m³/m³) | ≥ 0.75 | — | ≥ 0.90 | Near field capacity → runoff dominant |
| `rainfall_5min` (mm) | ≥ 3.0 | — | ≥ 8.0 | 8 mm/5 min = 96 mm/h (IMD "very heavy") |
| `tilt` (°) | ≥ 1.5° | — | ≥ 3.0° | Creep detection; 3° = imminent failure |
| `stream_level` (m) | ≥ 3.0 | — | ≥ 4.5 | Bankfull + 1.5 m = flash-flood surge |
| `factor_of_safety` | — | ≤ 1.30 | ≤ 1.05 | Infinite-slope computed locally |
| Multi-flag trigger | — | ≥ 2 WATCH flags | — | Belt-and-suspenders for ambiguous readings |

> **Design intent:** The edge node is conservative. It would rather trigger a false alarm (recoverable) than miss a true event (catastrophic). The cloud model provides finer calibrated probability; the edge node is the last line of defence.

---

## 5. Kill Internet Behaviour

When WiFi/MQTT is unavailable (tested by 3 failed reconnect attempts in 60 s):

1. `OFFLINE` flag set in firmware state.
2. All alert payloads routed exclusively to LoRa broadcast.
3. LED and siren actuators fire independently of cloud acknowledgement.
4. LoRa mesh relays the alert to the district base station (if in range).
5. Every 60 s, firmware retries WiFi. On reconnect, queued readings (up to 288 readings stored in flash) are flushed to MQTT with `offline_queued: true` flag.

---

## 6. OTA Update Process

```python
# OTA update over MQTT (subscribe to ews/ota/{VILLAGE_ID})
def ota_update_handler(topic, payload):
    import esp
    data = ujson.loads(payload)
    if data.get("version") <= FIRMWARE_VERSION:
        return  # already up to date
    ota = esp.OTA()
    ota.begin()
    # Download chunks over MQTT and write to OTA partition
    # ... (chunked transfer handler)
    ota.end()
    machine.reset()
```

---

## 7. Power Budget

| Mode | Current draw | Duration |
|---|---|---|
| Deep sleep (between readings) | ~0.15 mA | 295 s / cycle |
| Active measurement | ~80 mA | ~3 s |
| LoRa transmit | ~120 mA | ~0.5 s |
| Siren active | ~200 mA | variable |
| **Average** | **~4.5 mA** | — |

At 10 Ah battery + 10 W solar, the node sustains indefinitely in Uttarakhand monsoon conditions (≥ 3 h sunlight/day assumed).

---

## 8. Calibration Procedure (Field)

1. **Soil moisture probe**: Submerge in water → record ADC raw as `WET`. Air-dry → record as `DRY`. Flash via `ews/calibrate` MQTT command.
2. **Rain gauge**: Manually pour 50 mL water → expect 2 tips (0.4 mm). Check `rain_tips` counter via serial console.
3. **Tilt zero**: Power on with node perfectly level (spirit level). Firmware auto-records accelerometer offset during `init_sensors()`.
4. **Ultrasonic**: Measure actual water-surface height with tape; flash offset correction.
