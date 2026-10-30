# Review runs A–E – report (agent a2bcaab8, saved by the coordinator 2026-10-27)
Freeze: FREEZE.yaml md5 d00e1421c1291253bfcd3bb464029ebb, written 2026-10-26 18:12:52 EET, before the first held-out job.
Parameter-diff check exact. FREEZE_AMENDMENT.txt: runner-only fix for task E (before any E result).
Validity: t1 960/960; held-out 987/990; E 467/475 (8 invalid after 3 attempts: masks stopped reaching OpenVINS, likely HDD-bag related, unconfirmed).

## A. Held-out ablations (vs SAVIOR)
- w/o interaction tree: t2 L0+L1 +11 % (H .079), L2+L3 −12 % n.s.; VIODE ±0.
- w/o motion evidence: t2 L2+L3 −16 % n.s., hall+dock L3 −54 % (H .072); VIODE ±6 %.
- Both still beat Y-Cls on t2 (Holm < .05). Neither component has a measurable held-out benefit.

## B. Robust baseline: OpenVINS-v2 with tighter chi2 (x0.25, t1-tuned)
- vs OpenVINS: t2 −58 % (seq sign-flip .009); VIODE −36 %.
- SAVIOR vs OV-chi2: t2 +33 % (L2+L3 +66 %); VIODE +15 % (mid+high +0.4 %).
- SAVIOR+chi2 vs SAVIOR: t2 +8 %, VIODE −37 % (H 1e-12); fails 8/10 on hall_t2_L3.
- Failures, t2 L2+L3: OV-chi2 4/60 (OpenVINS 13); VIODE mid+high OV-chi2 8 (OpenVINS 5).

## C. Gate sweep under back-end v2 (t1)
- The sweep had 11 settings (P7 stage E had 9 plus 2 checked before the freeze). The paper's "nine" needs a qualifier (savior_v2.tex l.158, supp l.100).
- All 11 beat Y-Cls at L2+L3 (−22 to −33 %) and at L0+L1, with 0 failures. 1 m: −30.5 %; 0 m within 3.8 % of 1 m. Under v1 only 1 m worked.

## D. Promotion spill (t1 offline replay, identical to the online runs in 35 472/35 472 frames)
- Share of promotions that land on GT-static objects: by count L2 87 % / L3 84 %; by pixels L2 58 % / L3 16 %.
- 7.1 % of GT-static detection-frames are promoted.
- Static promotions via a moving forklift or its load: 14 % (24 % at L3). Via standing people 19 %, walking people 9 %, chains 58 %.

## E. Final SAVIOR on OpenLORIS / uHumans2 (original configs)
- OpenLORIS held-out (8 seq): SAVIOR vs OpenVINS −7.3 % [−12, −3] (H .017); seq −7.2 % [−15, +1] (sf .12). Y-Cls −3.7 %. SAVIOR vs Y-Cls −3.5 %.
- cafe1-1 +3.0 %. uHumans2 06h+12h +6.2 % n.s.
- Empty-mask controls −1…+0.4 % (uHumans2 −8.7 % n.s.; not bit-deterministic).
