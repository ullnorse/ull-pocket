# Hardware best-practices checklist

Collected 2026-11-03 for this 4-layer board. Sources marked [F] were fetched and read; [R] were not fetched: verify before relying on them.
Where sources disagree it is flagged "DISAGREE".

## 1. Schematic readability

1. Flow signals left to right: inputs/connectors left, outputs right. Power symbols point up (+3V3, VBUS), ground points down. [R] KiCad docs https://docs.kicad.org/ ; Phil's Lab reviews https://fedevel.com/blog/design-review-schematic-pcb-phils-lab-70
2. One function per sheet or block (USB-C + charger, 3V3 LDO + fuel gauge, MCU, sensors, display/UI). Name the sheets by function; hierarchical labels on sheet pins match the net names.
3. Short direct wires inside a block; net labels (not long wires) between blocks. Never run a wire across unrelated blocks.
4. Junction dot only where wires truly connect (T). Never make a 4-way crossing junction; offset two T's instead. Pins that touch the wire end are connected; confirm with ERC "pin not connected" = 0.
5. Every net that matters gets a meaningful label: VBUS, VBAT, 3V3, I2C_SDA, EPD_BUSY. Avoid auto names like Net-(U1-Pad3).
6. Decoupling caps drawn next to the IC pin they serve, not in a pile. Value + voltage rating in the Value field (e.g. 10uF 10V X5R); show the package in a field for passives.
7. Refdes: keep the KiCad prefix standard (R C L D U J SW TP LED Q). Annotate top-to-bottom, left-to-right so refdes order matches position. Refdes in a small consistent font, not touching wires.
8. Values: use SI and no decimal point ("4k7", "2u2", "100n"), or use one style consistently. Do not leave default "R" or "C" values.
9. Put design notes on the schematic: strapping-pin purpose, I2C addresses (SHT40 0x44, BMP580 0x46, LIS2DW12 0x19, MAX17048 0x36), charger ISET/ILIM resistor math, battery protection assumptions. Phil's Lab: put key component info as comments in the schematic (Hackaday write-up: https://hackaday.com/2022/01/03/the-benefits-of-critiquing-your-own-pcb-designs ).
10. Title block on every sheet: title, rev, date, author, company, license. Bump rev every time Gerbers are sent. Tag the git commit with the same rev.
11. Mark DNP parts explicitly (DNP attribute, not a deleted symbol) and make PCBA BOM exclude them.
12. Run ERC to zero errors; justify every remaining warning with an ERC exclusion + comment. Add PWR_FLAG only where ERC needs it (USB VBUS, battery).
13. Add a LCSC part number field (e.g. "LCSC") to every symbol so BOM export maps 1:1 to JLC.
14. Draw connectors with pin names, not only numbers; add a text box listing pinout of J-connectors (JST-PH polarity: pin 1 = +? Check the pack. Wrong JST polarity kills batteries; this is the top hobbyist failure).
15. Espressif schematic rules (apply to the MINI-1 module): CHIP_PU/EN needs RC (start 10k + 1uF) and must not float; GPIO9 pull-up, no big cap on GPIO9; strapping pins GPIO8/9/15, MTMS, MTDI must stay stable 3 ms after EN rises; >=500 mA 3.3 V supply; reserve 22/33 ohm series R on USB D+/D- (GPIO13/GPIO12). [F] https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/schematic-checklist.html
   - MINI-1 already contains crystal, flash, matching network; the chip-level crystal/matching items do not apply. Module decoupling still needs a 10 uF + 0.1 uF at the 3V3 pin (module datasheet, check).

## 2. PCB layout and routing

1. Layer plan 4-layer: L1 signal+parts, L2 solid GND, L3 power/some signals, L4 few signals. Keep L2 unbroken, no signal traces on it. [F] Espressif https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/pcb-layout-design.html
2. Decoupling: cap placed between the via/source and the IC pin, <=5 mm from the pin (KiCad wiki, [R] https://michael-vl.github.io/learning-wiki/kicad/best-practices/ ). Put the GND via right at the cap GND pad (Espressif says the same). Smallest cap closest to the pin.
3. Return paths: current returns under the signal on the nearest reference plane. Never route a fast or analog signal across a gap/slot in the plane. Rick Hartley: "return current flows directly under the trace"; no plane splits, keep one solid GND. [R] https://www.youtube.com/results?search_query=rick+hartley+grounding+and+signal+return
4. Do not split GND into analog/digital for this board; one plane, place noisy parts (charger inductor-less linear BQ24073, LDO) apart from sensors by placement, not splits.
5. Via stitching: GND vias around the board edge every ~3-5 mm (about lambda/20 at 2.4 GHz is ~6 mm; 3-5 mm is common). Dense GND vias near the antenna feed (Espressif). Do not stitch into the antenna keep-out.
6. Trace widths (IPC-2221, 1 oz external, 10 C rise): 0.25 mm ~ 0.8 A, 0.5 mm ~ 1.4 A, 1 mm ~ 2.3 A. USB charge path VBUS->BQ24073->VSYS at up to 1.5 A: use >=0.5 mm, prefer pour; inner layers carry ~half current for same width. Use a calculator, do not guess. [R] https://www.4pcb.com/trace-width-calculator.html
   - Espressif minimums: main 3.3 V >=25 mil (0.64 mm), VDDA3P3 >=20 mil, other power >=10 mil. These are for the bare chip; for a module, 0.3-0.5 mm is typical. [F]
7. Power vias: >=2 vias if a power trace changes layer; via drill >= trace width rule is Espressif's own heuristic. [F]
8. USB 2.0 FS/HS: route D+/D- as a pair, 90 ohm differential +-10%, matched length, continuous GND reference, minimal vias, GND via pair at each layer change, GND copper alongside. For FS-only on a 40 mm board the length is short; the priority is no stubs, no plane gaps, ESD diode close to the connector. [F] Espressif page above.
   - JLC 4-layer JLC04161H-7628 stackup gives about 90 ohm with 0.2 mm trace/0.15 mm gap on L1 over L2; use the JLCPCB impedance calculator https://cms.jlcpcb.com/pcb-impedance-calculator and select the real stackup. [R]
9. Antenna: put the MINI-1 antenna end at/over the board edge (feed near edge). Cut away base board on both sides and below the antenna; do not center the module with clearance on all four sides. No copper on any layer, no parts, no vias, no traces under or beside the antenna region as drawn in the MINI-1 datasheet Figure 3-1/10-1 keep-out zone. Keep >=15 mm clear in the enclosure in all directions. Battery, display and metal shield away from antenna. [F] Espressif guide above; module datasheet https://documentation.espressif.com/esp32-c6-mini-1_mini-1u_datasheet_en.html (no mm keep-out in text; take dimensions from its footprint drawing and the KiCad footprint/Espressif library).
   - Note: the 15 mm number is for enclosure clearance; the on-PCB keep-out is only drawn in a figure. Open the datasheet figure and match it.
10. Module EPAD (pin 49): connect to GND plane; datasheet says soldering "not a must" but helps thermals; avoid excess paste (gap). Use a windowed/reduced paste pattern. [F] datasheet above.
11. Crystal rules (2.4 mm from pin, no vias, ground around) apply to the chip, not the module. Skip.
12. Charger loop (BQ24073 is linear; no switching inductor): input cap (1 uF per datasheet) and output caps as close as possible to IN/OUT pins; short copper to the thermal pad; thermal pad to GND with several vias (datasheet shows multiple vias under pad) and a copper pour; follow TI QFN/SON PCB attachment note (SLUA271). [partly F] https://www.ti.com/document-viewer/ja-jp/BQ24073/datasheet/GUID-5B6FD4E0-80F5-488D-A76B-547F16D4FA7B ; similar TI guidance for a switcher: input cap closest to power pins, thermal vias directly under IC (BQ25618E datasheet).
   - Charger dissipates (VIN-VBAT)*I_chg; at 5 V, 3.7 V, 1 A = 1.3 W. Budget thermal copper or lower ICHG. Thermal regulation will throttle instead of failing, but the enclosure gets warm.
13. LDO (RT9080): input and output caps at the pins, GND return straight to the plane via; check the datasheet for the exact cap value/ESR window.
14. Sensor placement: SHT40 and BMP580 away from heat (charger, LDO, MCU, battery); add a slot/milled isolation cutout around SHT40 to cut thermal conduction; vent hole through enclosure. [R] Sensirion app note "SHT3x PCB Design Guide" HT_AN_SHTxx_Design-Guide (search sensirion.com). SHT4x reads high when it is near a warm part.
15. Track-to-pad entry: enter chip pads along the pad axis, centered; no wide trace hitting a small pad off-center. Teardrops on vias and thin-trace-to-pad joints (KiCad: Edit > Teardrops). Neck down to pad width only inside ~1 pad width.
16. Avoid acute (<90 deg) angles: they create acid traps and pour slivers. Use 45 deg bends, never 90 deg for RF/USB; run bends as 45 or arcs. Remove dead-end stubs and tiny floating copper islands (KiCad: "Remove islands").
17. Keep copper-to-edge >= 0.2 mm (routed), pours with a 0.3-0.5 mm edge inset. [F] JLC capabilities https://jlcpcb.com/capabilities/Capabilities
18. Thermal pads: connect to plane with relief spokes on hand-solder pads; use solid on large exposed pads for heat. Thermal relief spokes >= 0.25 mm.
19. Net classes: Power 0.4-0.5 mm, Default 0.2 mm, USB 0.2 mm + diff pair rule. Run DRC with "Schematic parity" ON. Keep the existing ull-pocket.kicad_dru in sync with the JLC values below.

## 3. DFM / DFA for JLCPCB (4-layer, 1 oz outer)

All values [F] https://jlcpcb.com/capabilities/Capabilities unless noted.

1. Trace/space: absolute min 0.09/0.09 mm (3.5 mil) multilayer 1 oz; design at >=0.127 mm to be safe and cheap.
2. Via: min 0.15 mm hole / 0.25 mm pad multilayer; preferred 0.2 mm hole / 0.4 mm pad (hole >= 0.2, pad >= hole+0.15). 0.1/0.2 only on <=1 mm boards with ENIG/OSP, costs more.
3. Annular ring: recommended 0.20 mm; absolute 0.15 mm multilayer 1 oz.
4. Via-in-pad: needs "filled and capped" epoxy/copper (extra cost; default only on 6-layer+). Otherwise keep vias off pads. Plugged mask vias <=0.5 mm, >=0.35 mm from other mask openings. For BQ24073 thermal pad use many vias with via-in-pad filled, or place vias around the pad / accept solder wicking with tented vias. DISAGREE: some say 0.3 mm vias in pad are fine for QFN thermal pads without fill (solder wicks, voids); JLC says fill. Cheapest safe choice: small vias (0.3 mm) with tenting on the opposite side and reduced paste on the pad.
5. Solder mask dam: min 0.10 mm for green/red/yellow/blue/purple; 0.13 mm for black/white. Fine-pitch QFN pads gang into one opening if the dam is below that; the stackup says green, OK. Mask opening to trace >= 0.09 mm.
6. Hole-to-hole: via 0.2 mm, pad hole 0.45 mm. NPTH to copper >= 2 mm recommended (JLC blog) https://jlcpcb.com/blog/common-pcb-design-issues-recommendations .
7. Copper to routed edge 0.2 mm; to V-cut 0.4 mm (1.0 recommended, 2.0 mm for tall/stress-sensitive parts). [F] https://jlcpcb.com/blog/technical-guidance-v-cut-panelization-standards
8. Components to board edge: JLC assembly terms say >=2.5 mm for component bodies against the process edge/rails; but if the SMT rails are added by JLC (5 mm process edge) edge-side parts are fine. [from search, not on a fetched page] https://jlcpcb.com/help/article/Terms-and-Conditions-of-JLCPCB-Assembly-Service . Third parties say 3-5 mm. DISAGREE. Rule: keep parts >=3 mm from any edge that will touch the conveyor; side-view LEDs and tact switches on the edge need panel rails/tabs that hold them clear.
9. Edge parts (side tact switches, side LEDs, JST, USB-C overhang): ensure KiKit tabs/rails don't collide with overhang; add empty CNC slots in the process edge for protruding parts. [F via search] https://jlcpcb.com/help/article/specifications-for-adding-process-edges-and-positioning-holes
10. Panel (KiKit): process edge 5 mm; tooling holes 2 mm; fiducials 1 mm pad (copper dot, 2 mm mask opening) with center >= 3.85 mm from board edge; mouse bites hole 0.6 mm, 5-8 holes/set, board gap 1.6-2 mm; tab width >=3 mm (5 mm for <=0.8 mm board); V-cut = zero gap. [F] JLC V-cut/panel blog above + process-edge help article. Note: JLC can add its own rails (fee/"Remove order number" option); if you supply rails, put 3 fiducials, asymmetric, on rails.
11. Fiducials: 3 per panel (2 diagonal + 1 asymmetric) plus local pair near fine-pitch parts (QFN/FPC pad pitch <=0.5 mm). 1 mm copper, 2 mm mask opening, no silk on it. https://jlcpcb.com/blog/fiducial-marks
12. Paste/windowpaning: split large thermal pads (>~3 mm) into a grid of apertures covering 50-60 % of area; keep paste off via holes; mask-defined pads less than 50 um mask expansion. Stencil is generated from the paste layer, not mask. [F] JLC blog above; IPC-7525 [R].
13. Tombstoning (0402/0201): same pad size/trace width on both ends, symmetrical copper (no one pad on a big pour without thermal relief), same pad geometry, parts oriented along reflow direction. Prefer 0402 min on non-RF parts; 0201 only for RF/ESP matching.
14. Part orientation: pick one rotation for all polarised parts per type (diodes cathode up/left, ICs pin 1 top-left, LEDs, caps) and make all same-type parts match. Reduces JLC rotation errors; verify in JLC's 3D viewer after upload and compare "pos" file rotation with the KiCad footprint library convention (JLC rotation corrections table is needed for some parts, e.g. SOT-23, QFN, USB-C).
15. Polarity marks visible after assembly: put pin-1 dot / cathode bar on silkscreen *outside* the component body (the body hides marks). See section 4.
16. Basic vs extended parts: basic parts have no extra setup fee; each distinct extended part adds about USD 3 (check current price). Standardize values (use 0.1u 0402, 10k, 4.7k, 1k, 22R as basics). Re-check stock before ordering. Prefer 0402/0603 (basic) for resistors/caps. Source: JLC parts library https://jlcpcb.com/parts [R]
17. Hand-solder only parts that JLC cannot place (JST-PH can be placed; e-paper FPC connectors: bottom-contact vs top-contact flap direction, check). Use 'Economic' vs 'Standard' PCBA options consciously: Economic = one side only, limited parts. [R]
18. Order a JLC DFM report / use JLCDFM https://jlcdfm.com/ before paying. [R]
19. Gerber/pos/BOM: export with the KiCad JLC plugin or KiCad 10 fabrication outputs. Compare BOM line count to schematic. Verify CPL against placement preview.
20. Test points: >=1 mm round pads, 2 mm apart for probing, on one side, labeled in silk. Add TPs on 3V3, GND, VBAT, VBUS, EN, TX, RX, GPIO9, SDA, SCL. Also expose USB/UART or JTAG pads for debugging.

## 4. Silkscreen presentation

1. JLC absolute min: stroke 0.15 mm, height 0.8 mm; recommended stroke >=0.2 mm, height >=1.0 mm, ratio about 1:6. Hollow fonts need stroke >=0.2 and height >=1.5 mm. [F] https://jlcpcb.com/blog/character-design-specifications
2. KiCad text: 1.0 x 1.0 mm size, 0.15-0.2 mm thickness. Refdes: 0.8-1.0 mm height only where space is tight; use 1.0 mm elsewhere; keep every refdes the same size. DISAGREE: Sierra/Proto Express quote 25 mil min height; PCBCart quotes 40 mil; JLC says 0.8 mm. Use 1.0 mm.
3. Silk to pad clearance min 0.15 mm, recommended 0.25 mm. Silk on exposed copper is removed. Set KiCad DRC silk clearance >= 0.15 mm. [F] same source.
4. Never print over pads, vias (tented or not), test points, fiducials, or mounting holes. Run DRC "silkscreen overlap" + "silk over copper". Delete refdes on dense areas rather than shrink; reference docs with assembly drawing.
5. Orientation: text reads either left-to-right or bottom-to-top (rotate 90 deg only one way); max two directions on a board. [R] Altium/Sierra guidance https://www.protoexpress.com/blog/ ; common convention.
6. Place refdes next to its part, consistently on the same side (top/right), never between two parts where it could be misread. Group labels by block.
7. Polarity: pin-1 dot at IC corner outside the body, cathode bar/"+" for diodes, LEDs, tantalums, battery connector "+"/"-" marks and the JST pin-1 mark. USB-C and JST outline in silk. Use the 3D viewer to check what is hidden by the package.
8. Connector labels: label every pin of J-connectors with function (3V3, GND, SDA...). For the battery connector: "BAT +" and "-" next to pins. For the e-paper FPC: "EPD" + pin 1 marker.
9. Test points: label in silk (TP3V3, TPGND...). Switch labels: "BOOT", "RST", "USER"; LED labels: "CHG", "PWR".
10. Board name + rev + date (this board: name only, by choice): e.g. "ull-pocket v1.0 2026-11" on the board in 1.0-1.2 mm text; put it on the bottom if the top is dense. If JLC adds an order number, use their "Specify a location" (a 5x5 mm silk block labelled "JLCJLCJLCJLC") or choose "Remove order number" (extra fee). https://jlcpcb.com/help/article/ [R]
11. Logo as silkscreen bitmap: keep features >= 0.15 mm; verify with Gerber viewer. Prefer logo on bare-board area, not on copper.
12. Aesthetics: align text to a 0.5 mm grid; consistent sizes; group with box outlines (0.15-0.2 mm lines); mark mounting holes; add a cross/arrow to show sensor vent/antenna side; keep the antenna area free of silk.
13. Bottom silk is mirrored automatically; place bottom text on B.SilkS, never flipped by hand.
14. Final check: render Gerbers in KiCad Gerber viewer or https://tracespace.io /GerbView; zoom on every IC to confirm silk is legible and not clipped.

## 5. Using Claude / LLMs for hardware design (2025-26)

Evidence base is thin: tool READMEs, one academic paper, forum threads. Treat as practice, not proof.

Tools:
- KiCad MCP servers: mixelpixx/KiCAD-MCP-Server (tools for project, schematic, PCB, DRC, JLCPCB parts integration) https://glama.ai/mcp/servers/@mixelpixx/KiCAD-MCP-Server ; lamaalrajih/kicad-mcp (project discovery, DRC, BOM, visualization, read-mostly); kicad-sch-api. Forum thread: https://forum.kicad.info/t/i-built-an-mcp-server-that-lets-ai-assistants-help-with-kicad-pcb-design/66451
- circuit-synth: circuits as Python, generates KiCad; ships Claude Code agents https://pypi.org/project/circuit-synth/ . KiCad forum pushback: LLM output is a suggestion needing verification https://forum.kicad.info/t/circuit-synth-professional-circuit-design-python-kicad-ai/63035
- atopile (declarative hardware language, [R] https://atopile.io ) + atoplace (placement/DFM with MCP) https://github.com/glovepost/atoplace
- Circuit Weaver: strict machine-readable contract for agents https://pypi.org/project/circuit-weaver/
- Research: DRCY (multi-agent schematic review, fetches datasheets, checks pin by pin; on AllSpice Hub) https://www.themoonlight.io/review/drcy-agentic-hardware-design-reviews ; Pinscope (netlist+BOM+datasheet with deterministic checks); arXiv 2603.15672 / 2606.01188 (generate-execute-repair loop for schematics).

Recommended workflow for this repo:
1. Keep the design as text (KiCad S-expressions, scripts in tools/) under git; LLM edits are diffs you can review. Never let an LLM edit the board by clicking.
2. Ground every claim in a local datasheet: datasheets/ + DATASHEETS.md. Prompt: "Quote the datasheet page/table that supports each pin, voltage, address, and value. If you can't quote it, say UNVERIFIED."
3. Extract netlist (kicad-cli sch export netlist) and BOM to text; give the LLM netlist + datasheet and ask for a pin-by-pin table: pin, function per datasheet, net, verdict. This is the DRCY/Pinscope pattern.
4. Separate roles: one pass generates, a second fresh-context pass reviews without seeing the first's reasoning. Anchoring on your hypothesis inflates agreement.
5. Verification loop: ERC/DRC (kicad-cli sch erc / pcb drc) -> JLC DFM -> LLM review of reports -> human check on the items below. Use deterministic tools as ground truth; the LLM explains and triages, it does not sign off.
6. Ask for concrete review prompts: "List every pin whose connection violates an absolute-max or abs-required note", "Compare each footprint's pad geometry/pin-1/pin numbering to the datasheet land-pattern drawing", "Check I2C address collisions and pull-up values vs bus capacitance", "Check each cap's rated voltage >= 2x rail and DC-bias derating."
7. Have the LLM write small scripts (power budget, trace-width/IPC-2221, RC timing, divider ratios) and show the numbers; do not accept mental arithmetic.

Known failure modes (check each):
- Hallucinated or shifted pinouts; confusing similar parts (BQ24072 vs 73 vs 74 differ in output-voltage/ISET behavior; RT9080 variants by voltage).
- Wrong footprints: pin 1 / pad numbering / mirrored FPC contact side; JST-PH polarity; USB-C 16 vs 24-pin; LCSC part number pointing at a different package.
- Invented component values and "typical" circuits that do not match the datasheet application circuit; stale knowledge of KiCad 10 syntax (S-expr versions).
- Overconfident "looks good" on layout it cannot see; only trust it on text/netlist/numbers or on rendered images you provide, and view the images yourself.
- Silent partial coverage: ask it to report what it did NOT check.
- Easy mistakes need human eyes: antenna keep-out vs real footprint, 3D clearance, polarity vs part orientation in JLC preview, connector pinout against the mating cable/battery, enclosure fit.

Human-only gates before ordering: (a) print 1:1 and place real parts/connectors on the paper; (b) check JLC 3D/placement preview for every polarised part; (c) read the datasheet application circuit for BQ24073, MAX17048, RT9080 against the schematic yourself; (d) order a 5-piece prototype first; keep a bring-up checklist (power-on current limit, 3V3, USB enumeration, I2C scan).

## Gaps (not verified; do before relying)
- Exact MINI-1 on-PCB antenna keep-out dimensions: only in datasheet figures (Fig 3-1/10-1/11-1), not in text.
- BQ24073 section 12 layout text and via count; RT9080 layout notes: read TI/Richtek datasheets.
- JLC assembly page (component-to-edge, extended-part fee): pages were not retrievable; verify in the JLC order DFM check.
- Rick Hartley, IPC-2221/7351 and Sensirion SHT3x design guide: cited from memory, not fetched.

## This board against the checklist (rev 0.7, 2026-11-03)

Changed:
- Schematic notes still described rev 0.6 (DN on IO15, B3435 NTC with a 0.5-50.8 C window, IO15 pull-up). Updated to IO9 and B3950 (3.5-47.2 C).
- DRC now enforces JLC silkscreen spacing: 0.15 mm silk to pad, 0.1 mm silk to silk and to slots (`ull-pocket.kicad_dru`). Fixed the four places that broke it (C12 / U3, J4 "1" / "VREF", U2 pin-1 mark and label at the sensor moat).
- Silkscreen labels: ICs, connectors, diodes, buttons, LEDs and test points only. All resistor and capacitor labels are hidden (18 already were, for lack of room; 42 more now): at 0402 density most sat as close to a neighbour's pads as to their own part, so they misled more than they helped. `production/ull-pocket-r0.7-assembly.pdf` lists every part.
- Silk text stroke raised to 1/6 of the height (JLC's recommended ratio); UP / OK / DN raised from JLC's 0.8 mm minimum to 1.0 mm.
- Panel: the 0.5 mm mouse-bite holes reach 0.45 mm into the board, past the pours (0.3 mm from the edge), so they cut GND / +3V3 copper (84 panel DRC errors). No-pour areas 0.75 mm deep behind each tab (`tools/route/tab_keepouts.py`); panel DRC now has 0 errors.
- Removed a duplicate GND track; replaced the stale "placement only (unrouted)" title-block comment.

Checked, no change:
- Sharp track joints: 23 of 24 lie inside pads, where the pad copper covers them.
- ESP32 ground pad: 4 vias between the pad segments plus a ring of vias around them; U6 thermal pad has 5 vias.
- USB pair ~86 ohm differential with ESD (U8) next to J1; all assembled parts on the top side; panel has rails, 3 fiducials and tooling holes.

Not done:
- Teardrops: KiCad has no script interface for them. In pcbnew: Edit > Edit Teardrops (defaults), refill zones (B), run DRC, then regenerate the production files. Optional: the vias already meet JLC's limits.
- Vias in U6's thermal pad are not filled: some solder wicks into them. TI's layout shows vias in the pad; JLC fills vias only at extra cost.
- Gaps listed above: MINI-1 keep-out from the datasheet figure, BQ24073 section 12 layout text, Sensirion SHT3x design guide.

## Rev 0.9 review fixes (2026-11-09)

- BMP580 INT resets active-low, open-drain and disabled (INT_CONFIG 0x35); the schematic note said active-high. Added R35 100k pull-up on BARO_INT.
- U8 pin 5 moved from VBUS to +3V3, so the D+ pull-up can't back-feed VBUS on battery.
- VBUS from J1 to U6 IN moved from In2 (0.5 oz) to B.Cu (1 oz) at 0.5 mm; the C2-to-pin-13 stub is 0.5 mm where pin 14 allows.
- Two more GND vias under U7 pin 2. C3/C4 are now 10 uF 25 V 0805 (C15850).
- J2 + / - marks moved to the connector mouth; three back-silk texts under the display removed. Silkscreen carries no revision or date.
- BQ24073 /CE moves from GND to IO15 (net CHG_DIS, high pauses charging) with R36 100k pull-down; IO15 came from the green USR LED channel, so the USR LED is red and blue only. IO15 resets as an input with no pull (ESP32-C6 datasheet Table 2-1, p.17).
