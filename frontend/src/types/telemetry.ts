// Espejo de backend/schemas/output.py::EnrichedFrameOutput -- mantener en
// sync manual con ese archivo (fuente de verdad real es el backend).

export type Detection = {
  class: string;
  confidence: number | null;
  bbox: number[];
};

export type FallInfo = {
  hay_alerta: boolean;
  hay_critica: boolean;
  n_personas: number;
};

export type EppInfo = {
  n_victims: number;
  n_rescuer: number;
  n_epp: number;
};

export type FusionInfo = {
  n_rubble_victims: number;
  n_fall_rubble: number;
  n_risk_zones: number;
  n_civilians: number;
  n_routes: number;
};

export type AudioState = {
  vol_l: number | null;
  vol_r: number | null;
  stale: boolean;
};

export type GpsFix = {
  lat: number | null;
  lon: number | null;
};

export type GasLevels = {
  mq1: number | null;
  mq2: number | null;
};

export type ClimateReading = {
  temp_c: number | null;
  pressure_hpa: number | null;
  humidity_pct: number | null;
};

export type EnvState = {
  gps: GpsFix | null;
  gas: GasLevels | null;
  pir_detected: boolean | null;
  climate: ClimateReading | null;
  stale: boolean;
};

export type EnrichedFrameOutput = {
  frame_id: number;
  timestamp: string;
  image_b64: string;
  detections: Detection[];
  fall: FallInfo;
  epp: EppInfo;
  fusion: FusionInfo;
  audio: AudioState;
  env: EnvState;
};
