/* eslint-disable @typescript-eslint/no-explicit-any */
import type { ExplorableObject } from '../core/EurekaTypes'

export function generateFallbackObject(searchText: string, wikiTitle: string, wikiDesc: string): ExplorableObject {
  const q = searchText.toLowerCase()
  const isJetEngine = (q.includes('airplane') || q.includes('aircraft') || q.includes('jet') || q.includes('turbine')) && q.includes('engine')
  const isCarEngine = q.includes('car') && q.includes('engine') && !isJetEngine
  const isMicroscope = q.includes('microscope')
  const isRocket = q.includes('rocket') || q.includes('missile')
  const isDrone = q.includes('drone') || q.includes('quadcopter')

  let rootColor = '#4a4e69', rootSize: [number,number,number] = [1.8, 0.8, 1.2]
  let p1N = 'Primary Module', p1C = '#c0c5ce', p1G: Record<string,unknown> = { type: 'cylinder', radius: 0.3, depth: 0.6 }, p1P: [number,number,number] = [0, 0.6, 0]
  let p2N = 'Secondary Module', p2C = '#b87333', p2G: Record<string,unknown> = { type: 'sphere', radius: 0.22 }, p2P: [number,number,number] = [0.8, 0, 0]
  let p3N = 'Support Base', p3G: Record<string,unknown> = { type: 'box', size: [1.4, 0.15, 1.0] }, p3P: [number,number,number] = [0, -0.5, 0]

  if (isJetEngine) {
    rootColor = '#3d3d3d'; rootSize = [0.85, 0.85, 2.2]
    p1N = 'Turbofan Blades'; p1G = { type: 'fan', radius: 0.78, blades: 18, rotation: [1.57,0,0] }; p1P = [0,0,1.2]; p1C = '#c0c5ce'
    p2N = 'Combustion Chamber'; p2G = { type: 'cylinder', radius: 0.38, depth: 1.0, rotation: [1.57,0,0] }; p2P = [0,0,0]; p2C = '#b87333'
    p3N = 'Exhaust Nozzle'; p3G = { type: 'cone', radius: 0.42, depth: 0.7 }; p3P = [0,0,-1.3]
  } else if (isCarEngine) {
    rootColor = '#3d3d3d'; rootSize = [1.5, 0.7, 0.9]
    p1N = 'Cylinder Head'; p1G = { type: 'box', size: [1.5, 0.18, 0.85] }; p1P = [0,0.44,0]; p1C = '#c0c5ce'
    p2N = 'Crankshaft'; p2G = { type: 'cylinder', radius: 0.06, depth: 1.4 }; p2P = [0,-0.15,0]; p2C = '#71797e'
    p3N = 'Oil Pan'; p3G = { type: 'box', size: [1.4, 0.18, 0.85] }; p3P = [0,-0.44,0]
  } else if (isMicroscope) {
    rootColor = '#2c3e50'; rootSize = [0.4, 0.8, 0.5]
    p1N = 'Eyepiece Lens'; p1G = { type: 'cylinder', radius: 0.14, depth: 0.35 }; p1P = [0,1.1,0.1]; p1C = '#d4f1f9'
    p2N = 'Objective Lens'; p2G = { type: 'cylinder', radius: 0.1, depth: 0.3 }; p2P = [0,0.1,0.3]; p2C = '#b87333'
    p3N = 'Stage'; p3G = { type: 'box', size: [0.6, 0.05, 0.6] }; p3P = [0,0,0]
  } else if (isRocket) {
    rootColor = '#c0c5ce'; rootSize = [0.5, 2.5, 0.5]
    p1N = 'Nose Cone'; p1G = { type: 'cone', radius: 0.25, depth: 0.7 }; p1P = [0,1.6,0]; p1C = '#e8e8e8'
    p2N = 'Rocket Nozzle'; p2G = { type: 'cone', radius: 0.3, depth: 0.5 }; p2P = [0,-1.5,0]; p2C = '#b87333'
    p3N = 'Fin Assembly'; p3G = { type: 'box', size: [0.8, 0.5, 0.05] }; p3P = [0,-1.2,0.3]
  } else if (isDrone) {
    rootColor = '#2c2f33'; rootSize = [1.4, 0.12, 1.4]
    p1N = 'Front Motor'; p1G = { type: 'cylinder', radius: 0.08, depth: 0.22 }; p1P = [-0.7,0.15,0.7]; p1C = '#1a1a1a'
    p2N = 'Propeller'; p2G = { type: 'fan', radius: 0.35, blades: 2 }; p2P = [-0.7,0.28,0.7]; p2C = '#c0c5ce'
    p3N = 'Flight Controller'; p3G = { type: 'box', size: [0.3, 0.04, 0.3] }; p3P = [0,0.06,0]
  }

  const oid = searchText.toLowerCase().replace(/[^a-z0-9]+/g, '_')
  let fallbackComponents: ExplorableObject['components'] = []

  if (isJetEngine) {
    fallbackComponents = [
      {
        id: `${oid}_central_shaft`,
        name: "Central Shaft",
        parentId: null,
        scaleLevel: "component",
        function: "Central main shaft transmitting rotational torque from the turbines at the back to the fan and compressors at the front.",
        material: "Titanium Alloy",
        riskIfRemoved: "Total mechanical lock; compressor/fan cannot spin, leading to zero thrust and engine seizure.",
        position: [0, 0, 0],
        color: "#7f8c8d",
        geometry: { type: "cylinder", radius: 0.15, depth: 3.6, rotation: [0, 0, 1.5708] } as any,
        children: [`${oid}_intake_fan`, `${oid}_lp_compressor`, `${oid}_hp_compressor`, `${oid}_combustion_chamber`, `${oid}_hp_turbine`, `${oid}_lp_turbine`, `${oid}_exhaust_cone`, `${oid}_fan_casing`, `${oid}_engine_stand`],
        microLevels: []
      },
      {
        id: `${oid}_intake_fan`,
        name: "Titanium Intake Fan",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Large front fan drawing in massive volumes of air, providing the bulk of thrust through the bypass duct.",
        material: "Titanium Alloy",
        riskIfRemoved: "Total loss of bypass thrust (80%+ of engine power) and no airflow to core.",
        position: [-1.7, 0, 0],
        color: "#00b0ff",
        geometry: { type: "fan", radius: 1.4, blades: 24, rotation: [0, 0, 1.5708] } as any,
        children: [`${oid}_nose_cone`],
        microLevels: []
      },
      {
        id: `${oid}_nose_cone`,
        name: "Nose Cone Spinner",
        parentId: `${oid}_intake_fan`,
        scaleLevel: "subcomponent",
        function: "Aerodynamic nose cone that diverts incoming air smoothly into the fan and compressor, and sheds ice.",
        material: "Composite Materials",
        riskIfRemoved: "Extreme aerodynamic drag, ice accumulation, and air turbulence leading to engine surge.",
        position: [-1.85, 0, 0],
        color: "#1a1a1a",
        geometry: { type: "cone", radius: 0.35, depth: 0.6, rotation: [0, 0, -1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_lp_compressor`,
        name: "Low-Pressure Compressor",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "First compression stage raising air pressure and temperature before it enters the high-pressure section.",
        material: "Titanium",
        riskIfRemoved: "Loss of initial compression, leading to immediate stall and engine failure.",
        position: [-1.0, 0, 0],
        color: "#2ecc71",
        geometry: { type: "cylinder", radius: 0.8, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_hp_compressor`,
        name: "High-Pressure Compressor",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Final compressor stage compressing air to extremely high pressure before combustion.",
        material: "Nickel Alloy",
        riskIfRemoved: "Engine cannot maintain self-sustaining combustion due to lack of compression.",
        position: [-0.4, 0, 0],
        color: "#8eff1e",
        geometry: { type: "cylinder", radius: 0.65, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_combustion_chamber`,
        name: "Combustion Chamber",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Area where fuel is injected, mixed with compressed air, and ignited to create hot, high-velocity gas.",
        material: "Ceramic Matrix Composite",
        riskIfRemoved: "No combustion possible; engine produces zero energy and stops.",
        position: [0.2, 0, 0],
        color: "#e67e22",
        geometry: { type: "cylinder", radius: 0.7, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_hp_turbine`,
        name: "High-Pressure Turbine",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Extracts energy from hot gas flow to drive the high-pressure compressor stage via outer shaft.",
        material: "Single-Crystal Nickel Superalloy",
        riskIfRemoved: "High-pressure compressor stops rotating; engine ceases operation immediately.",
        position: [0.8, 0, 0],
        color: "#f1c40f",
        geometry: { type: "cylinder", radius: 0.75, depth: 0.4, rotation: [0, 0, 1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_lp_turbine`,
        name: "Low-Pressure Turbine",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Extracts remaining gas energy to drive the main intake fan and low-pressure compressor.",
        material: "Nickel Alloy",
        riskIfRemoved: "Intake fan stops spinning; engine loses virtually all thrust.",
        position: [1.3, 0, 0],
        color: "#e74c3c",
        geometry: { type: "cylinder", radius: 0.85, depth: 0.5, rotation: [0, 0, 1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_exhaust_cone`,
        name: "Exhaust Nozzle Cone",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Channels exhaust gas flow to maximize velocity and direct the thrust vector.",
        material: "Inconel Alloy",
        riskIfRemoved: "Thrust efficiency drops dramatically; exhaust gases disperse unevenly.",
        position: [1.75, 0, 0],
        color: "#d35400",
        geometry: { type: "cone", radius: 0.4, depth: 0.6, rotation: [0, 0, 1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_fan_casing`,
        name: "Outer Fan Casing",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Surrounds fan blades to contain blade fragments in case of failure and duct incoming air.",
        material: "Kevlar & Aluminum",
        riskIfRemoved: "Critical safety risk: fan blade out event would destroy the aircraft wing/fuselage.",
        position: [-1.2, 0, 0],
        color: "#3f51b5",
        geometry: { type: "torus", radius: 1.45, tube: 0.08, rotation: [0, 0, 1.5708] } as any,
        children: [],
        microLevels: []
      },
      {
        id: `${oid}_engine_stand`,
        name: "Structural Display Stand",
        parentId: `${oid}_central_shaft`,
        scaleLevel: "subcomponent",
        function: "Heavy display stand supporting the engine assembly for research and presentation.",
        material: "Structural Steel",
        riskIfRemoved: "Engine falls to the ground; cannot be operated or inspected.",
        position: [0, -1.2, 0],
        color: "#7f8c8d",
        geometry: { type: "box", size: [2.4, 0.2, 1.2] } as any,
        children: [],
        microLevels: []
      }
    ]
  } else {
    fallbackComponents = [
      { id: `${oid}_body`, name: `${wikiTitle} Body`, parentId: null, scaleLevel: 'component',
        function: `Main structural body of the ${wikiTitle}.`, material: 'Alloy',
        riskIfRemoved: 'Complete structural failure.', position: [0,0,0], color: rootColor,
        geometry: { type: 'box', size: rootSize } as ExplorableObject['components'][0]['geometry'],
        children: [`${oid}_p1`,`${oid}_p2`,`${oid}_p3`], microLevels: [] },
      { id: `${oid}_p1`, name: p1N, parentId: `${oid}_body`, scaleLevel: 'subcomponent',
        function: `Primary component of the ${wikiTitle}.`, material: 'Aluminum',
        riskIfRemoved: 'Primary function fails.', position: p1P, color: p1C,
        geometry: p1G as ExplorableObject['components'][0]['geometry'], children: [], microLevels: [] },
      { id: `${oid}_p2`, name: p2N, parentId: `${oid}_body`, scaleLevel: 'subcomponent',
        function: `Secondary component of the ${wikiTitle}.`, material: 'Steel',
        riskIfRemoved: 'Secondary function lost.', position: p2P, color: p2C,
        geometry: p2G as ExplorableObject['components'][0]['geometry'], children: [], microLevels: [] },
      { id: `${oid}_p3`, name: p3N, parentId: `${oid}_body`, scaleLevel: 'subcomponent',
        function: `Support structure for the ${wikiTitle}.`, material: 'Cast Iron',
        riskIfRemoved: 'Loses structural support.', position: p3P, color: '#4a4a4f',
        geometry: p3G as ExplorableObject['components'][0]['geometry'], children: [], microLevels: [] }
    ]
  }

  return {
    id: oid, name: wikiTitle, type: 'mechanical_system', summary: wikiDesc,
    defaultView: 'assembled', model: { kind: 'procedural', assetUrl: null },
    components: fallbackComponents
  }
}
