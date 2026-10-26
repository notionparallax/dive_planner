
I'm building a decompression planning tool for hydrogen (Hydreliox: H₂/He/O₂) diving. I need to understand isobaric counterdiffusion (ICD) management for H₂ dives specifically.
Please research and answer:
H₂ diffusivity vs He and N₂ — H₂ is lighter than He. How much faster does it diffuse through tissue, and what does that mean for ICD severity compared to He/N₂ ICD?
COMEX/IDEX H₂ dive protocols — What intermediate gas strategies did Fructus, Brauer, or the COMEX team use on ascent from deep H₂ dives? Did they use He-only or He/N₂ intermediates?
The O₂ constraint — With O₂ capped at ~4% due to combustion risk, you can't use the standard "raise O₂, lower fast gas" trick. What's the recommended strategy?
Switch depth spacing — Is there a published rule for how far apart gas switches should be to avoid ICD (analogous to the 1 ATM N₂ increase rule from Hamilton/Lambertsen for He dives)?
Does shallow ICD theory transfer? — Does the Lambertsen "superficial ICD" (skin/joint bends from N₂ wash-in over He) literature apply to H₂ dives, or is H₂ fast enough that deep ICD is the bigger concern?
Cite papers or sources where possible. Key authors to look for: Fructus, Brauer, Barnard, Elliott, Masurel, Rostain, Gardette.

Show less
12:05 PM

Searched the web
Searched the web
Good data gathered. Let me now compile this into a structured technical answer.

ICD Management for Hydrogen (Hydreliox) Diving: A Technical Overview

1. H₂ Diffusivity vs. He and N₂
The hierarchy is well established. In aqueous tissue (the primary medium for diffusion modelling):

N₂ and O₂ have a diffusivity of ~2.3×10⁻⁵ cm²/s, He ~3.8×10⁻⁵ cm²/s, and H₂ ~5.8×10⁻⁵ cm²/s.
uspto

That gives approximate ratios:

H₂/N₂: 2.5×
H₂/He: 1.53×
He/N₂: 1.65× (commonly cited as 2.65× in diving literature — that figure likely reflects lipid tissue or combined tissue models rather than pure aqueous diffusion)
Helium has a diffusivity approximately 2.65 times that of nitrogen. H₂ sits ~1.5× above He on the same basis.
InDEPTH

Hydrogen demonstrates a higher diffusion rate than helium in tissues, saturating and desaturating approximately 3.7 times faster than nitrogen (versus helium's 2.7 times). These figures come from the tissue half-time data used in COMEX's own modelling.
Grokipedia

ICD severity implication: Deep tissue ICD severity scales with the diffusivity ratio between the incoming and outgoing gas. Deep tissue ICD occurs when different inert gases are breathed in sequence — the rapidly diffusing gas is transported into the tissue faster than the slower diffusing gas is transported out. Switching to H₂ from He mid-decompression would produce a smaller counterdiffusion gradient than switching from N₂ to He (because H₂ is only 1.5× faster than He, versus He being 2.65× faster than N₂). The dangerous direction is switching away from H₂ to He-only or He/N₂ mixtures during ascent — the H₂-saturated tissues are then exposed to a much slower-moving replacement gas, producing net supersaturation.
Infogalactic

Saturation divers breathing hydreliox who switched to a heliox mixture developed symptoms of decompression sickness during Hydra V. This is the canonical H₂ ICD incident.
HandWiki

1. COMEX/Hydra Ascent Protocols: What They Actually Did
The Hydra programme ran from the 1970s through 1992. The ICD problem first bit hard at Hydra V (Hydra 5, ~450 msw), where an abrupt switch from hydreliox to heliox caused DCS. Saturation divers on the Hydra V mission experienced DCS following a gas switch from hydreliox to a faster-diffusing heliox mixture, with the gas switch thought to have caused the DCS (Rostain, 1987).
InDEPTH

The solution developed for Hydra VIII and beyond was not a breathing-gas switch but physical hydrogen removal:

Protocols typically involve prolonged bottom times at depth to achieve equilibrium, followed by linear ascents with multiple stops, transitioning from hydreliox to heliox once hydrogen partial pressure is reduced below critical thresholds (e.g., to 250 msw or P_H₂ < 1.2 MPa) to leverage helium's slower kinetics for shallower stages.
Grokipedia

In the Hydra VIII trial, six divers underwent 18 days of decompression from 500 msw saturation, including catalytic removal of hydrogen to 250 msw before standard heliox procedures, resulting in no DCS incidents and full recovery.
Grokipedia

The catalytic system (a palladium catalyst in the habitat atmosphere) oxidised H₂ + O₂ → H₂O, progressively reducing the H₂ partial pressure in the breathing environment during the upper portion of the decompression without requiring a discrete gas switch. This is the key insight: COMEX avoided the H₂→He ICD problem by eliminating the discrete switch event entirely.

The Hydra VIII bottom mix was 49% hydrogen, 50.2% helium, and 0.8% oxygen. At 500 msw, the ppO₂ was ~0.04 bar — well within the explosion-suppression regime.
InDEPTH

Key primary sources here are internal COMEX reports: Fructus & Gardette (1987) Hydra 6 internal report; Imbert, Gortan, Fructus, Ciesielski & Gardette (1987) "Hydra 8: Pre-commercial Hydrogen Diving Project" (SUT Subtech proceedings). The Hydra 8 paper is the most accessible published account.

1. The O₂ Constraint and What It Eliminates
With the lower explosive limit of hydrogen being around 4% by volume, using less than this amount in normoxic environments effectively mitigates the fire risk but does little for deep divers. Instead, extremely hypoxic gases and high concentrations of hydrogen and helium have been used with great success.
InDEPTH

The 4–5% O₂ ceiling (by volume) is hard. At 500 msw (51 ATA), 1% O₂ = 0.51 bar ppO₂ — still adequate. But on ascent, the same 1% becomes hypoxic at around 50 msw. This creates a ppO₂ window problem: any mix safe at depth will become hypoxic during the mid-decompression range unless the O₂ fraction is increased, but increasing it risks combustion as total pressure drops.

The consequence is you cannot use the standard heliox/trimix decompression trick of raising ppO₂ toward 1.6 bar during deco stops to accelerate off-gassing and reduce stops. O₂-driven acceleration is essentially unavailable while H₂ is present in meaningful concentrations. The second breathing gas is of the hydreliox type and contains hydrogen at a minimum partial pressure of 0.33 MPa, less than 4 volume percent oxygen.
Google Patents

Practical strategies:

Catalytic H₂ removal (Hydra VIII approach): reduce H₂ fractionally in the habitat atmosphere during ascent so the gas fraction shifts continuously rather than in a discrete switch.
Staged fractional dilution: step down H₂% across multiple decompression stops while incrementally increasing He%, with each step small enough to limit the ICD gradient. The COMEX patent (EP0773880A1) specifies this model.
Defer O₂ enrichment until H₂ has been reduced below combustion-safe levels (typically after transitioning to pure heliox).
4. Gas Switch Depth Spacing: Is There a Published Rule?
For conventional He/N₂ diving, the established Lambertsen/Hamilton guidance is qualitative rather than quantitative — it's rules about direction rather than depth spacing. The operative rules are:

Don't switch from N₂-rich to He-rich environments (especially superficial ICD in saturation)
Lambertsen proposed that gas switches going from helium-rich to nitrogen-rich mixtures would be acceptable, but changes from nitrogen to helium should include recompression.
Wikipedia
Doolette and Mitchell propose that a switch from a helium-rich to a nitrogen-rich mix, as is common in technical diving when switching from trimix to nitrox on ascent, may cause a transient supersaturation of inert gas within the inner ear, and suggest that breathing-gas switches should be carefully scheduled either deep or shallow to avoid the period of maximum supersaturation resulting from decompression.
Wikipedia
"Deep or shallow" is the key prescription — make the switch either before the critical supersaturation window opens, or after you've ascended past it. There is no universally published specific depth interval rule analogous to a fixed ATM increase limit.

The "1 ATM N₂ increase" framing you've referenced is a technical diving community heuristic (associated with Hamilton and with the Rule of Fifths concept), not a formally published physiological threshold. The Rule of Fifths (as discussed at Scuba Engineer) states that a 25% reduction in He fraction permits no more than a ~5% increase in N₂ fraction at the ceiling. A switch from Trimix 20/25 to Nitrox 32 is not acceptable since nitrogen jumps from 55 to 68% — a 13% jump — where the rule suggests a maximum allowable increase in %N₂ for a 25% drop in He of only 5%. This is a community-derived rule, not directly from Lambertsen or Hamilton papers.
Scuba Engineer

For H₂ specifically, no equivalent published rule exists in the open literature. The COMEX approach sidestepped the problem by continuous catalytic removal rather than discrete switches, which implies they regarded any discrete switch as unacceptably risky until H₂ was at very low partial pressure.

1. Does Lambertsen's Superficial ICD Theory Transfer to H₂?
The two ICD forms behave differently with H₂:

Superficial ICD (Lambertsen's skin/joint model) requires a high-diffusivity gas in the environment with a lower-diffusivity gas being breathed. Superficial ICD occurs when the inert gas breathed by the diver diffuses more slowly into the body than the inert gas surrounding the body — an example would be breathing air in a heliox environment. The helium in the heliox diffuses into the skin quickly while the nitrogen diffuses more slowly from the capillaries to the skin. In a hydreliox saturation environment, the habitat atmosphere already contains H₂ — so skin counterdiffusion from H₂ in/N₂ or He out is the issue. Because H₂ is the fastest mover, any scenario where the diver breathes a He or N₂-richer mix than the habitat atmosphere would create superficial ICD, but in practice the breathing gas and habitat gas are the same in saturation, so this vector is less concerning than the deep tissue form.
Infogalactic

Deep tissue ICD is the primary H₂ concern. Given H₂'s speed, it saturates tissues very rapidly. Hydrogen's off-gassing occurs more rapidly in faster tissue compartments, with time constants around 0.5 hours, leading to half-times of approximately 20–30 minutes, while slower compartments require adjustments about 1.5 times longer than helium's equivalents. This means:
Grokipedia

H₂ equilibrates quickly on compression — good
On ascent, H₂ desaturates fast from fast compartments, but slow compartments hold it longer
A switch from H₂/He to He-only creates a situation where H₂ is still loading out of slow compartments while He loads in — the net tissue tension can rise
Because H₂ is faster than He (not slower), the dangerous switch direction is H₂ → He (the He now loads slowly into tissues that still contain abundant fast-leaving H₂, but wait — the actual hazard is net total tension). The Hydra V incident confirms this: switching to faster He creates inward He diffusion before outward H₂ clearance balances it. This is counterintuitive until you track total dissolved gas tension rather than just individual gas.

Short answer: the Lambertsen superficial ICD literature transfers conceptually but the polarity is different. For H₂ dives, deep tissue ICD triggered by the H₂→He switch is the dominant threat, and shallow ICD (skin/joint) is secondary. The Hydra V incident is the empirical proof.

Key Sources
Reference Relevance
Rostain, J.C. (1987) — cited in Hydra V report H₂/He ICD incident
Imbert, Gortan, Fructus, Ciesielski & Gardette (1987) Hydra 8: Pre-commercial Hydrogen Diving Project, SUT Subtech proceedings Primary COMEX H₂ protocol paper
Lambertsen & Idicula (1975) J Appl Physiol 39:434 Original ICD description
D'Aoust et al. (1977) Animal model deep tissue ICD demonstration
Doolette & Mitchell (2003) J Appl Physiol 94:2145 Inner ear ICD model; switch timing guidance
EP0773880A1 (COMEX patent, 1996) Hydreliox operational patent; staged decompression approach
The most significant gap in the open literature is that COMEX's detailed hydreliox decompression tables and their specific switch-depth criteria remain internal documents. What's published are the outcomes (Hydra VIII: zero DCS over 18 days of decompression) and the method (catalytic H₂ removal) but not the precise rate or trigger pressure for the switch. For a decompression tool, the ~250 msw / P_H₂ < 1.2 MPa transition threshold is the best publicly available datum to work from.

is catalytic removal essentially a rebreather scrubber that's set up for hydrogen rather than co2?
Would it work to have a rebreather that can gradually swap the hydrogen for helium as the h2 is scrubbed out, so that once the h2 % goes down enough it can start increasing the o2?

Then the rebreather would have a diluent of 4% o2 and the rest hydrogen (or maybe a tiny bit of N2 to reduce HPNS), an 02 bottle, a helium bottle, a CO2 Scrubber loop, and an isolatable h2 scrubber?

12:18 PM
Good questions. Let me work through them.

Catalytic removal vs. CO₂ scrubber

Conceptually similar but chemically different. A CO₂ scrubber is a chemical absorption reaction (sodalime or similar). The COMEX catalytic H₂ removal is an oxidation reaction — palladium or platinum catalyst promotes H₂ + ½O₂ → H₂O at room temperature without ignition. It consumes O₂ in the process, which has to be accounted for. In the Hydra VIII habitat it was a separate chamber unit in the atmospheric loop, not integrated into a breathing loop. So: same function (removing an unwanted gas from a closed loop), different chemistry, different engineering.

Your proposed rebreather architecture

The logic is sound in principle. Walking through the gas flows:

At depth, diluent is H₂/O₂ (4% O₂ + balance H₂, maybe trace N₂). The rebreather maintains ppO₂ via O₂ injection as normal. The H₂ scrubber loop periodically or continuously pulls gas through the palladium catalyst, removing H₂ and producing H₂O (which needs to be absorbed or vented). As H₂ partial pressure drops in the loop, you inject He to maintain total pressure. Once H₂ has dropped below ~4% of total mixture at the ambient pressure you're currently at, the combustion risk disappears and you can start increasing O₂ fraction normally.

So you'd have a continuous transition:

Deep: high H₂, very low O₂ (0.8–1% by volume), He as ballast
Mid-decompression: H₂ declining, He increasing, O₂ fraction creeping up as ppO₂ constraint relaxes
Shallow: H₂ gone or negligible, pure heliox or trimix decompression, full O₂ control restored
Problems worth thinking hard about

The O₂ consumption issue. The catalyst reaction H₂ + ½O₂ → H₂O consumes O₂. At depth where your ppO₂ is already being held at a knife-edge floor (~0.3–0.5 bar), the scrubber is actively competing with the diver for O₂. The controller would need to account for scrubber O₂ consumption separately from metabolic consumption, or you'd track into hypoxia.

Heat. The catalytic reaction is exothermic. In a small-volume CCR loop this could be significant — you're not just dealing with CO₂ scrubber exotherm, you've now got two heat sources. At depth in cold water this might actually be welcome, but it needs to be characterised.

H₂O production. Every mole of H₂ removed produces a mole of H₂O. That water has to go somewhere — absorbed by a desiccant in the catalyst circuit, or it'll condense and potentially flood the catalyst bed, which poisons its activity.

Catalyst poisoning and rate. Palladium catalysts are well characterised for this reaction, but diving environments introduce CO₂, trace contaminants, seawater ingress risk. The rate of H₂ removal via the catalyst needs to be fast enough to achieve meaningful ppH₂ reduction over a decompression schedule without creating ICD by pulling H₂ down too fast in the breathing loop faster than tissues can follow. Paradoxically, scrubbing H₂ too fast from the breathing gas while tissues are still H₂-saturated would itself create a steep ICD gradient — you'd be doing exactly what the Hydra V incident did, just via scrubbing rather than a hard switch.

That last point is the critical design constraint. The scrubber removal rate needs to be matched to the slowest tissue compartment's H₂ half-time (~several hours for slow compartments). The COMEX approach over 18 days of decompression suggests a very slow, controlled reduction. Your rebreather controller would need to track modelled tissue H₂ loading and pace the scrubber rate to stay within ICD-safe gradients — essentially a fourth dimension on top of the normal ppO₂/ppCO₂/total pressure control.

Is it a viable architecture?

Yes, more than the alternatives. The discrete-switch approach (COMEX Hydra V) demonstrably fails. Continuous gradual replacement — which is what your design achieves — is exactly the lesson COMEX learned. The rebreather format just miniaturises and automates what they did at habitat scale.

The engineering challenge is the controller complexity: you're now managing ppO₂ floor (combustion), ppO₂ ceiling (toxicity), ppCO₂ (scrubber), ppH₂ rate of change (ICD), ppH₂ absolute level (HPNS, narcosis), and total inert gas loading simultaneously. That's a more complex control problem than any existing CCR. But the architecture itself — diluent manifold + O₂ bottle + He bottle + CO₂ scrubber + catalytic H₂ oxidiser — is internally consistent.

The N₂ trace for HPNS is a reasonable addition. Small amounts (maybe 2–5% at depth) provide narcotic buffering. Watch the ICD implications of N₂ during the He wash-in phase — by that point you don't want three competing inert gases at play if you can avoid it.

could the scrubber get it's own o2 source?
I assume we _could_ use a combustion chamber instead of paladium, but it'd be a big shift in risk

has anyone else proposed this rebreather architecture?

1:45 PM
Dedicated O₂ for the scrubber

Yes, straightforward fix. A small dedicated O₂ feed to the catalyst circuit, metered stoichiometrically against the H₂ removal rate, keeps it completely decoupled from the breathing loop O₂ budget. You'd size it against the maximum scrubbing rate — at the relatively slow rates needed to avoid ICD-pace H₂ drawdown, O₂ consumption would be modest. A small separate cylinder or a bleed from the main O₂ bottle via a separate regulator path. Clean separation of concerns.

Combustion chamber

Technically it works — you're just doing the same reaction faster and hotter. The problems are significant though. The palladium catalyst operates at ambient temperature with no ignition risk because the reaction proceeds below the H₂ flammability threshold at the catalyst surface. A combustion chamber requires controlled ignition in a system that already contains hydrogen at pressure, produces a flame or sustained high-temperature reaction zone, and lives inside a diving apparatus worn by a human. The failure modes are categorically worse. Palladium is the right call — the only reason to consider combustion would be if catalyst poisoning or flooding made it unworkable in practice, and those are solvable engineering problems.

Has anyone proposed this architecture?

Not in the open literature in the form you've described — a fully integrated CCR with onboard catalytic H₂ scrubbing and He/O₂ wash-in. The closest published work is:

The 2024 Pearse Resurgence case report (Mitchell et al., Diving and Hyperbaric Medicine, 2024) — using an electronic closed-circuit rebreather, helihydrox (approximately 3% oxygen, 59% helium and 38% hydrogen) was breathed between 200 and 230 m, associated with amelioration of HPNS symptoms. That dive used a CCR for H₂ delivery but with standard decompression and no onboard scrubbing — the H₂ fraction was low enough that they managed the ascent without catalytic removal. No ICD protocol beyond standard trimix practices was described.
PubMed

The COMEX EP0773880A1 patent (1996) describes staged fractional substitution of H₂ with He during decompression but as a habitat-level process, not a wearable rebreather.

Zetterström's 1940s dives used surface-supplied hydrox with a manual switch to air for decompression — no ICD management at all, which killed him when the switch was mistimed.

So the specific combination you're describing — CCR + catalytic H₂ oxidiser with dedicated O₂ feed + He injection paced to tissue model — appears to be novel as an integrated architecture. The components are all proven individually. The control logic is the uncharted part, and the ICD-rate-limited scrubbing constraint is the key design insight that doesn't appear to be explicitly articulated anywhere in the published literature, even though it follows directly from the Hydra V lesson.

If you're serious about this as a design, that controller logic — specifically the algorithm that paces H₂ removal against modelled tissue compartment H₂ tension to stay within ICD-safe gradients — is probably where the novel IP sits.

how much would a paladium scrubber cost? Is it consumed, or is it catalytic?
the combustion chamber might win out on cost

1:48 PM
Palladium: catalytic, not consumed

True catalyst — it's not consumed in the reaction, just facilitates it. A palladium catalyst bed in principle lasts indefinitely with proper maintenance. What degrades it in practice: sulphur compounds (poisons the surface), water flooding (physical blockage, recoverable by drying), CO₂ exposure (minor effect), particulate contamination. In a clean diving gas circuit with a desiccant pre-stage it would have a long service life.

Cost

Palladium spot price is currently around USD $10–12/troy oz (it crashed from a ~$2,800 peak in 2022 — oversupply from EV transition reducing autocatalyst demand). A small catalyst bed for a rebreather-scale application wouldn't need much — grams rather than ounces of actual Pd, dispersed on an alumina or ceramic substrate. Industrial Pd catalyst cartridges for hydrogen recombination (used in nuclear facilities, battery storage, gloveboxes) run roughly $200–800 depending on size and form factor. Not cheap, but a one-time cost for something that lasts years.

Combustion chamber cost comparison

A small controlled combustion chamber is mechanically simpler and cheaper to fabricate — no precious metal required. Ignition system, heat-resistant chamber, thermal management. Maybe $50–200 in components. But you'd need flame arrestors, thermal cutoffs, ignition reliability engineering. The certification and testing burden for putting a controlled hydrogen combustion device in a life-support system would dwarf the material cost difference.

The palladium option almost certainly wins on total cost once you factor in that the catalyst is reusable and the engineering risk delta is enormous.

definitely!
So the usage could be that the diver breathes a high hydrogen mix on the bottom, potentially just 4% o2 and 96% h2, and that keeps the cost of the fill down. Then, on ascent to the first switch, transition from h2 to he in the loop, because the scrubber consumes the h2, and then they can start to increase the o2% for faster off gassing for the rest of the ascent.

Assuming that the ascent rate from 100m to 50m is going to be fairly fast (lets say 15m/min) how big would the scrubber need to be to have made that switch by the time the diver gets there? Or is the ICD rate going to constrain that?
 I'm guessing that that is a hard mathematical problem, would it be better solved with a python function?

1:55 PM
The ICD rate constraint is almost certainly the binding constraint, not scrubber capacity. Here's why that matters for the calculation.

The two constraints are different in kind

Scrubber capacity is an engineering variable — you can make it bigger. ICD rate is a physiological limit — it's set by tissue half-times and you can't engineer around it. If the scrubber can pull H₂ out of the breathing loop faster than tissues can follow, you've recreated the Hydra V problem mechanically. So the scrubber needs to be rate-limited by the controller to match tissue off-gassing, not run at maximum capacity.

The relevant tissue half-times for H₂ are roughly 20–30 min for fast compartments, several hours for slow ones. A 15 min/5 stop ascent from 100→50m is going to be fast relative to slow compartment half-times regardless of scrubber size.

What the calculation actually needs

The hard part isn't scrubber volume, it's: given a tissue H₂ loading at 100m (function of bottom time and depth), what breathing-loop ppH₂ reduction rate keeps the ICD gradient — difference between breathing gas H₂ tension and tissue H₂ tension — below some threshold? That threshold isn't well published for H₂ specifically, which is a real problem.

Python is the right tool

The core model is a multi-compartment Haldanean off-gassing calculation with an added ICD gradient constraint, plus the combustion-safety floor on O₂%. It's maybe 150–200 lines of reasonably clean Python. Worth building properly.

Want me to write it? I'd structure it as:

Compartment H₂ loading at end of bottom segment
Ascent simulation with configurable rate
Scrubber removal as a controlled rate variable (adjustable by controller, capped by ICD threshold)
He injection to maintain total pressure
O₂ fraction tracking against combustion floor
Output: minimum time to reach safe O₂ increase depth, required scrubber rate, ICD gradient over time
The ICD threshold would need to be a tuneable parameter since it's not well characterised for H₂ — you'd want to run sensitivity analysis across plausible values.

Claude is AI and can make mistakes. Please double-check responses.
