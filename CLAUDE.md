# Shadows of the Fallen

## World Authority

The authoritative world definition is:

00_WORLD_MASTER/coordinates/world_master.json

Never invent coordinates that contradict this file.

## Coordinate System

Units: meters
Up: +Z
North: +Y
East: +X
Origin: [0,0,0]

## Pipeline

world_master.json
    ↓
Blender world generation
    ↓
macro terrain
    ↓
hydrology
    ↓
biomes
    ↓
infrastructure
    ↓
locations
    ↓
assets
    ↓
Unity

## Rules

- Do not modify world coordinates without explicit instruction.
- Do not hard-code coordinates into Blender scripts.
- Blender scripts must read world_master.json.
- Keep generated objects organized into collections.
- Prefer procedural generation over manually duplicated geometry.
- Keep source data separate from generated output.
- Every generator should be repeatable.
- Never destroy existing user work without explicit instruction.
