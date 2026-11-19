# Design input (owner, 2026-11-20 00:50), CP-11a

Owner's description of the kind of line they maintained (a master-slave PLC network, with a separate PLC on the auto-feed). The lab models a **generic plant of this kind**. Rules:
- **Secret:** real material names, recipe ratios and the company's name. Use "Material A–E" and invented ratios. Never name the company or the product type in this repo.
- Medium-scale plant. Make the logic realistic and accurate.

## The process

1. **Auto-feeding: 5 feeder silos**, each holding one raw material.
   - Each batch needs a set ratio of the materials (the recipe).
   - Each silo has **load cells (weighbridge sensors)**. The measured weight decides how far the silo's discharge gate (lid) opens, and when it closes.
   - Low material in a silo triggers an **alarm lamp and a sounder**.
2. **2 conveyor belts in series** carry the material a long way and up about 3 storeys (an incline).
3. **Rotary mixer**: the batch mixes for a set time.
   - Downstream, the real plant compresses into tablets and packs them. This is out of scope for the lab.
4. **2 HMIs:**
   - **Feeder HMI** at the auto-feeding system, for maintenance and troubleshooting: Manual, Semi-auto and Auto modes.
   - **Mixer HMI** for operators.

## Decisions so far

| # | Decision | Status |
|---|---|---|
| 1 | Own public repo `salbotics-plc-troubleshooting-lab`, linked from the PLC Learning Hub | owner yes |
| 2 | Model a generic auto-feed batching cell (now: 5-silo weigh batching → 2 inclined conveyors → rotary mixer) | owner yes, refined by this description |
| 3 | Faults: seven, one per owner task (sensor, module config, VFD, stepper/gate drive, output wiring, program edit, HMI tag), adapted to this plant | owner said "follow your recommendation": all seven |
| 4 | Runtime | Claude decides (recommendation) |
| 5 | Recordings | Claude decides (recommendation) |
