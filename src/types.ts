export interface ArgoMeasurement {
  depth_dbar: number; // Pressure / depth in dbar
  temperature: number; // in °C
  salinity: number; // in PSU
  qc_temperature: number; // 1 = good, 2 = probably good
  qc_salinity: number;
}

export interface ArgoProfile {
  profile_id: string;
  wmo_id: string;
  float_name: string;
  platform_type: string;
  cycle_number: number;
  date: string;
  latitude: number;
  longitude: number;
  sea_region: string;
  data_mode: 'D' | 'R'; // Delayed-mode vs Real-time
  qc_status: 'QC_PASS_FLAG_1' | 'QC_PASS_FLAG_2' | 'QC_SUSPECT';
  raw_netcdf_source: string;
  gdac_archive_path: string;
  measurements: ArgoMeasurement[];
}

export interface UncertaintyBound {
  depth_dbar: number;
  mean_temp: number;
  std_temp: number;
  ci90_temp_lower: number;
  ci90_temp_upper: number;
  ci95_temp_lower: number;
  ci95_temp_upper: number;

  mean_sal: number;
  std_sal: number;
  ci90_sal_lower: number;
  ci90_sal_upper: number;
  ci95_sal_lower: number;
  ci95_sal_upper: number;
}

export interface EvidenceCitation {
  citation_id: string;
  wmo_id: string;
  cycle_number: number;
  date: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  similarity_score: number; // 0 to 1
  cosine_profile_sim: number;
  spatial_temporal_weight: number;
  qc_flag: number;
  raw_netcdf_file: string;
  gdac_archive_path?: string;
  provenance_chain: {
    origin: string;
    archive_gdac: string;
    qc_step: string;
    standardized_grid: string;
  };
  key_feature_relevance: string;
  measurements: ArgoMeasurement[];
}

export interface PhysicalDiagnostics {
  is_gravitationally_stable: boolean;
  min_density_gradient: number; // d(sigma)/dz >= 0
  mixed_layer_depth_m: number;
  max_thermocline_gradient: number; // °C / dbar
  thermocline_depth_m: number;
  halocline_depth_m: number;
  surface_potential_density: number; // kg/m^3
  deep_potential_density: number; // kg/m^3
  stability_violation_count: number;
  density_profile: {
    depth_dbar: number;
    sigma_theta: number; // kg/m^3
    buoyancy_frequency_n2: number; // s^-2
  }[];
}

export interface XAIAttribution {
  temporal_attribution: {
    cycle_offset: number; // -3, -2, -1
    cycle_label: string;
    importance_score: number; // 0 to 1
    interpretation: string;
  }[];
  depth_attribution_matrix: {
    input_depth: number;
    output_depth: number;
    saliency_weight: number;
  }[];
  key_depth_influences: {
    target_zone: string;
    dominant_input_depth: string;
    attribution_percentage: number;
    scientific_driver: string;
  }[];
}

export interface ForecastResult {
  forecast_id: string;
  target_float_id: string;
  target_cycle: number;
  predicted_cycle: number;
  forecast_date: string;
  latitude: number;
  longitude: number;
  input_sequence_cycles: number[];
  profiles: {
    depth_dbar: number;
    temperature_forecast: number;
    salinity_forecast: number;
    persistence_temperature: number;
    persistence_salinity: number;
    gradient_boosting_temperature: number;
    gradient_boosting_salinity: number;
  }[];
  uncertainty_bounds: UncertaintyBound[];
  physical_diagnostics: PhysicalDiagnostics;
  xai_attribution: XAIAttribution;
  evidence_citations: EvidenceCitation[];
  metrics_comparison: {
    model: string;
    profile_rmse: number;
    profile_mae: number;
    thermocline_rmse: number;
    deep_rmse: number;
    physical_violation_rate: number;
  }[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  content: string;
  forecast_context?: ForecastResult;
  grounding_verified?: boolean;
  cited_floats?: string[];
  suggested_queries?: string[];
}
