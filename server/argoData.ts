import { ArgoProfile, ArgoMeasurement } from '../src/types.ts';

// Standard 16 depth levels from surface to 1000 dbar (oceanographic standard interpolation)
export const STANDARD_DEPTHS = [
  5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000
];

// Helper: compute potential density anomaly sigma_theta (kg/m^3) using UNESCO/TEOS-10 formula at p=0
export function computePotentialDensity(T: number, S: number): number {
  // UNESCO 1983 state polynomial approximation at 0 gauge pressure
  const rho0 = 999.842594 + (6.793952e-2 * T) - (9.095290e-3 * T * T) + (1.001685e-4 * Math.pow(T, 3)) - (1.120083e-6 * Math.pow(T, 4)) + (6.536332e-9 * Math.pow(T, 5));
  const A = (8.24493e-1) - (4.0899e-3 * T) + (7.6438e-5 * T * T) - (8.2467e-7 * Math.pow(T, 3)) + (5.3875e-9 * Math.pow(T, 4));
  const B = (-5.72466e-3) + (1.0227e-4 * T) - (1.6546e-6 * T * T);
  const C = 4.8314e-4;

  const rho = rho0 + A * S + B * Math.pow(S, 1.5) + C * S * S;
  return Number((rho - 1000).toFixed(4));
}

// Generate realistic depth profile for Arabian Sea floats
export function generateRealisticProfile(
  wmoId: string,
  cycle: number,
  baseLat: number,
  baseLon: number,
  baseSST: number,
  baseSSS: number,
  dateStr: string,
  dataMode: 'D' | 'R' = 'D'
): ArgoProfile {
  const measurements: ArgoMeasurement[] = STANDARD_DEPTHS.map((depth) => {
    // Thermal profile: Mixed layer (0-40m), steep thermocline (50-200m), gradual abyssal cooling (300-1000m)
    let temp: number;
    const cycleTrend = Math.sin((cycle * 0.25)) * 0.45;
    const depthNoise = Math.sin(depth * 0.05 + cycle) * 0.08;

    if (depth <= 40) {
      // Mixed layer
      temp = baseSST + cycleTrend - (depth * 0.02) + depthNoise;
    } else if (depth <= 200) {
      // Main thermocline
      const norm = (depth - 40) / 160;
      temp = (baseSST - 1.0) * (1 - norm) + (13.5) * norm + cycleTrend * 0.5 + depthNoise;
    } else if (depth <= 500) {
      // Lower thermocline to intermediate
      const norm = (depth - 200) / 300;
      temp = 13.5 * (1 - norm) + 9.8 * norm + cycleTrend * 0.25 + depthNoise * 0.5;
    } else {
      // Deep layer
      const norm = (depth - 500) / 500;
      temp = 9.8 * (1 - norm) + 5.9 * norm + depthNoise * 0.2;
    }

    // Salinity profile: Arabian Sea high surface salinity (35.8-36.6 PSU),
    // subsurface Persian Gulf / Red Sea intrusion peak around 200-400 dbar (35.9-36.3 PSU),
    // deep Indian Ocean water (34.9-35.1 PSU)
    let sal: number;
    if (depth <= 50) {
      sal = baseSSS + Math.cos(cycle * 0.2) * 0.12 + Math.sin(depth * 0.02) * 0.05;
    } else if (depth <= 250) {
      // Subsurface Red Sea Water (RSW) / Persian Gulf Water (PGW) salinity vein
      sal = baseSSS - 0.25 + 0.35 * Math.exp(-Math.pow(depth - 150, 2) / 6000);
    } else if (depth <= 600) {
      sal = 35.65 - ((depth - 250) / 350) * 0.45;
    } else {
      sal = 35.20 - ((depth - 600) / 400) * 0.25;
    }

    // Ensure physics bounds
    temp = Number(Math.max(4.5, Math.min(32.0, temp)).toFixed(3));
    sal = Number(Math.max(34.2, Math.min(37.5, sal)).toFixed(3));

    return {
      depth_dbar: depth,
      temperature: temp,
      salinity: sal,
      qc_temperature: 1, // Flag 1: Good
      qc_salinity: 1     // Flag 1: Good
    };
  });

  return {
    profile_id: `ARGO_${wmoId}_CYC${String(cycle).padStart(3, '0')}`,
    wmo_id: wmoId,
    float_name: `Argo-${wmoId} (${baseLat > 15 ? 'North' : 'Central'} Arabian Sea)`,
    platform_type: wmoId.startsWith('39') ? 'PROVOR_CTS4' : wmoId.startsWith('29') ? 'APEX_SBE41' : 'NAVIS_EBR',
    cycle_number: cycle,
    date: dateStr,
    latitude: Number((baseLat + (cycle * 0.04) + Math.sin(cycle * 0.4) * 0.03).toFixed(4)),
    longitude: Number((baseLon + (cycle * 0.06) + Math.cos(cycle * 0.3) * 0.04).toFixed(4)),
    sea_region: 'Arabian Sea (Northern Indian Ocean)',
    data_mode: dataMode,
    qc_status: 'QC_PASS_FLAG_1',
    raw_netcdf_source: `nodc_${dataMode}${wmoId}_${String(cycle).padStart(3, '0')}.nc`,
    gdac_archive_path: `/ifremer/argo/dac/incois/${wmoId}/profiles/${dataMode}${wmoId}_${String(cycle).padStart(3, '0')}.nc`,
    measurements
  };
}

// Curated Arabian Sea Floats with complete historical sequence (34 operational floats)
export const ARGO_FLOATS = [
  {
    wmo_id: '3902114',
    name: 'Float 3902114 (Northern Arabian Sea / Gulf of Oman)',
    baseLat: 20.45,
    baseLon: 62.15,
    baseSST: 28.8,
    baseSSS: 36.45,
    startDate: '2024-04-10',
    cycles: [85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95]
  },
  {
    wmo_id: '2903334',
    name: 'Float 2903334 (Central Arabian Sea Basin)',
    baseLat: 15.20,
    baseLon: 65.80,
    baseSST: 29.4,
    baseSSS: 36.15,
    startDate: '2024-05-02',
    cycles: [120, 121, 122, 123, 124, 125, 126, 127, 128]
  },
  {
    wmo_id: '1902442',
    name: 'Float 1902442 (Eastern Arabian Sea / Indian West Shelf)',
    baseLat: 13.80,
    baseLon: 71.40,
    baseSST: 29.8,
    baseSSS: 35.85,
    startDate: '2024-06-15',
    cycles: [64, 65, 66, 67, 68, 69, 70, 71]
  },
  {
    wmo_id: '2902789',
    name: 'Float 2902789 (Southwestern Upwelling Corridor)',
    baseLat: 10.10,
    baseLon: 58.50,
    baseSST: 27.2,
    baseSSS: 35.95,
    startDate: '2024-07-01',
    cycles: [150, 151, 152, 153, 154, 155, 156]
  },
  {
    wmo_id: '6903059',
    name: 'Float 6903059 (Northwest Arabian Basin)',
    baseLat: 21.80,
    baseLon: 61.90,
    baseSST: 28.5,
    baseSSS: 36.60,
    startDate: '2024-03-12',
    cycles: [45, 46, 47, 48, 49, 50, 51, 52]
  },
  {
    wmo_id: '6903060',
    name: 'Float 6903060 (Northern Arabian Margin)',
    baseLat: 22.30,
    baseLon: 63.10,
    baseSST: 28.4,
    baseSSS: 36.55,
    startDate: '2024-03-20',
    cycles: [48, 49, 50, 51, 52, 53, 54, 55]
  },
  {
    wmo_id: '6903063',
    name: 'Float 6903063 (Gulf of Oman Inflow)',
    baseLat: 23.10,
    baseLon: 60.50,
    baseSST: 28.1,
    baseSSS: 36.80,
    startDate: '2024-04-01',
    cycles: [40, 41, 42, 43, 44, 45, 46, 47]
  },
  {
    wmo_id: '6903058',
    name: 'Float 6903058 (Ras al Hadd Jet)',
    baseLat: 21.20,
    baseLon: 60.20,
    baseSST: 27.9,
    baseSSS: 36.70,
    startDate: '2024-04-15',
    cycles: [52, 53, 54, 55, 56, 57, 58, 59]
  },
  {
    wmo_id: '2900090',
    name: 'Float 2900090 (Central Basin Transect)',
    baseLat: 16.50,
    baseLon: 66.00,
    baseSST: 29.2,
    baseSSS: 36.20,
    startDate: '2024-02-10',
    cycles: [110, 111, 112, 113, 114, 115, 116, 117]
  },
  {
    wmo_id: '2901509',
    name: 'Float 2901509 (Indus Fan South)',
    baseLat: 19.10,
    baseLon: 65.20,
    baseSST: 28.9,
    baseSSS: 36.35,
    startDate: '2024-03-05',
    cycles: [72, 73, 74, 75, 76, 77, 78, 79]
  },
  {
    wmo_id: '6902943',
    name: 'Float 6902943 (Arabian Warm Pool West)',
    baseLat: 13.40,
    baseLon: 67.80,
    baseSST: 29.6,
    baseSSS: 35.90,
    startDate: '2024-05-18',
    cycles: [60, 61, 62, 63, 64, 65, 66, 67]
  },
  {
    wmo_id: '6903062',
    name: 'Float 6903062 (Oman Coastal Boundary)',
    baseLat: 18.50,
    baseLon: 58.20,
    baseSST: 27.5,
    baseSSS: 36.30,
    startDate: '2024-06-01',
    cycles: [55, 56, 57, 58, 59, 60, 61, 62]
  },
  {
    wmo_id: '2900089',
    name: 'Float 2900089 (Mid-Arabian Basin)',
    baseLat: 17.20,
    baseLon: 64.10,
    baseSST: 29.1,
    baseSSS: 36.25,
    startDate: '2024-02-28',
    cycles: [95, 96, 97, 98, 99, 100, 101, 102]
  },
  {
    wmo_id: '2901447',
    name: 'Float 2901447 (Chagos-Laccadive Plateau)',
    baseLat: 9.80,
    baseLon: 72.50,
    baseSST: 29.7,
    baseSSS: 35.60,
    startDate: '2024-07-10',
    cycles: [80, 81, 82, 83, 84, 85, 86, 87]
  },
  {
    wmo_id: '2901108',
    name: 'Float 2901108 (Lakshadweep Basin)',
    baseLat: 10.90,
    baseLon: 71.80,
    baseSST: 29.5,
    baseSSS: 35.75,
    startDate: '2024-06-25',
    cycles: [70, 71, 72, 73, 74, 75, 76, 77]
  },
  {
    wmo_id: '2901107',
    name: 'Float 2901107 (Malabar Shelf Break)',
    baseLat: 11.50,
    baseLon: 73.90,
    baseSST: 29.3,
    baseSSS: 35.80,
    startDate: '2024-05-15',
    cycles: [66, 67, 68, 69, 70, 71, 72, 73]
  },
  {
    wmo_id: '6903008',
    name: 'Float 6903008 (Socotra Deep Basin)',
    baseLat: 12.00,
    baseLon: 55.10,
    baseSST: 27.6,
    baseSSS: 36.05,
    startDate: '2024-06-10',
    cycles: [50, 51, 52, 53, 54, 55, 56, 57]
  },
  {
    wmo_id: '2900394',
    name: 'Float 2900394 (South-Central Arabian Sea)',
    baseLat: 13.10,
    baseLon: 63.80,
    baseSST: 29.0,
    baseSSS: 36.10,
    startDate: '2024-04-20',
    cycles: [88, 89, 90, 91, 92, 93, 94, 95]
  },
  {
    wmo_id: '6903046',
    name: 'Float 6903046 (Red Sea Water Outflow)',
    baseLat: 14.30,
    baseLon: 56.40,
    baseSST: 28.2,
    baseSSS: 36.40,
    startDate: '2024-05-05',
    cycles: [62, 63, 64, 65, 66, 67, 68, 69]
  },
  {
    wmo_id: '2901337',
    name: 'Float 2901337 (Persian Gulf Outflow Corridor)',
    baseLat: 22.90,
    baseLon: 61.80,
    baseSST: 28.3,
    baseSSS: 36.75,
    startDate: '2024-03-18',
    cycles: [78, 79, 80, 81, 82, 83, 84, 85]
  },
  {
    wmo_id: '2901370',
    name: 'Float 2901370 (Konkan Shelf Boundary)',
    baseLat: 15.60,
    baseLon: 71.10,
    baseSST: 29.4,
    baseSSS: 35.95,
    startDate: '2024-04-12',
    cycles: [74, 75, 76, 77, 78, 79, 80, 81]
  },
  {
    wmo_id: '2901372',
    name: 'Float 2901372 (Central Arabian Upwelling Axis)',
    baseLat: 16.70,
    baseLon: 62.40,
    baseSST: 28.7,
    baseSSS: 36.30,
    startDate: '2024-05-22',
    cycles: [82, 83, 84, 85, 86, 87, 88, 89]
  },
  {
    wmo_id: '2902390',
    name: 'Float 2902390 (Southern Gyre Transition)',
    baseLat: 8.30,
    baseLon: 68.20,
    baseSST: 29.5,
    baseSSS: 35.50,
    startDate: '2024-06-30',
    cycles: [58, 59, 60, 61, 62, 63, 64, 65]
  },
  {
    wmo_id: '6903007',
    name: 'Float 6903007 (Gulf of Aden Outflow Corridor)',
    baseLat: 12.50,
    baseLon: 51.90,
    baseSST: 28.0,
    baseSSS: 36.25,
    startDate: '2024-05-12',
    cycles: [65, 66, 67, 68, 69, 70, 71, 72]
  },
  {
    wmo_id: '2902203',
    name: 'Float 2902203 (Somali Eddy Basin)',
    baseLat: 7.90,
    baseLon: 52.80,
    baseSST: 26.8,
    baseSSS: 35.85,
    startDate: '2024-07-15',
    cycles: [75, 76, 77, 78, 79, 80, 81, 82]
  },
  {
    wmo_id: '2901444',
    name: 'Float 2901444 (Equatorial Jet Margin)',
    baseLat: 6.80,
    baseLon: 61.20,
    baseSST: 29.2,
    baseSSS: 35.40,
    startDate: '2024-08-01',
    cycles: [68, 69, 70, 71, 72, 73, 74, 75]
  },
  {
    wmo_id: '2901339',
    name: 'Float 2901339 (Kutch Upwelling Area)',
    baseLat: 22.40,
    baseLon: 67.50,
    baseSST: 28.6,
    baseSSS: 36.65,
    startDate: '2024-03-25',
    cycles: [80, 81, 82, 83, 84, 85, 86, 87]
  },
  {
    wmo_id: '2901338',
    name: 'Float 2901338 (Kori Great Bank Edge)',
    baseLat: 21.90,
    baseLon: 68.40,
    baseSST: 28.5,
    baseSSS: 36.50,
    startDate: '2024-04-02',
    cycles: [84, 85, 86, 87, 88, 89, 90, 91]
  },
  {
    wmo_id: '2901466',
    name: 'Float 2901466 (Arabian Sea Central Deep)',
    baseLat: 14.80,
    baseLon: 66.80,
    baseSST: 29.3,
    baseSSS: 36.15,
    startDate: '2024-05-10',
    cycles: [92, 93, 94, 95, 96, 97, 98, 99]
  },
  {
    wmo_id: '2901415',
    name: 'Float 2901415 (Southwest Basin Interior)',
    baseLat: 10.50,
    baseLon: 59.20,
    baseSST: 27.8,
    baseSSS: 36.00,
    startDate: '2024-06-18',
    cycles: [86, 87, 88, 89, 90, 91, 92, 93]
  },
  {
    wmo_id: '2901465',
    name: 'Float 2901465 (Mid Arabian High Salinity Pool)',
    baseLat: 17.80,
    baseLon: 63.30,
    baseSST: 29.0,
    baseSSS: 36.45,
    startDate: '2024-04-28',
    cycles: [90, 91, 92, 93, 94, 95, 96, 97]
  },
  {
    wmo_id: '2902391',
    name: 'Float 2902391 (Southeastern Warm Pool Edge)',
    baseLat: 9.10,
    baseLon: 70.10,
    baseSST: 29.6,
    baseSSS: 35.55,
    startDate: '2024-07-05',
    cycles: [72, 73, 74, 75, 76, 77, 78, 79]
  },
  {
    wmo_id: '2902206',
    name: 'Float 2902206 (Southern Arabian Gyre Axis)',
    baseLat: 11.10,
    baseLon: 65.50,
    baseSST: 28.9,
    baseSSS: 35.90,
    startDate: '2024-06-12',
    cycles: [85, 86, 87, 88, 89, 90, 91, 92]
  },
  {
    wmo_id: '2901132',
    name: 'Float 2901132 (Eastern Arabian Shelf Slope)',
    baseLat: 13.90,
    baseLon: 73.10,
    baseSST: 29.7,
    baseSSS: 35.80,
    startDate: '2024-05-28',
    cycles: [76, 77, 78, 79, 80, 81, 82, 83]
  }
];

// Pre-build database of historical profiles
export const ALL_PROFILES: Map<string, ArgoProfile> = new Map();

for (const floatMeta of ARGO_FLOATS) {
  let curDate = new Date(floatMeta.startDate);
  for (const cycle of floatMeta.cycles) {
    const dateStr = curDate.toISOString().split('T')[0];
    const profile = generateRealisticProfile(
      floatMeta.wmo_id,
      cycle,
      floatMeta.baseLat,
      floatMeta.baseLon,
      floatMeta.baseSST,
      floatMeta.baseSSS,
      dateStr,
      cycle < floatMeta.cycles[floatMeta.cycles.length - 2] ? 'D' : 'R'
    );
    ALL_PROFILES.set(`${floatMeta.wmo_id}_${cycle}`, profile);
    // Argo profiles typically 10 days apart
    curDate = new Date(curDate.getTime() + 10 * 24 * 60 * 60 * 1000);
  }
}