"""synth.py (T3.1): planted-truth simulation.

Simulate rocks with known mineral mixes and domain boundaries; apply
view-specific detectability masks and renormalisation to produce synthetic
SWIR and TIR views. TIR sees ~all minerals; SWIR sees only the configurable
SWIR-active set (hydroxyl-bearing minerals, carbonates, sulfates; NOT
anhydrous silicates). Chlorite appears in BOTH views. Includes the GSWA
97% quartz / 3% chlorite case. Adds noise, misidentification, aspectral/invalid.
"""
