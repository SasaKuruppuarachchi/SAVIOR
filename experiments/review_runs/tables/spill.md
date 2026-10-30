# Task D: promotion spill onto GT-static objects

Offline replay of the frozen pipeline on the t1 tuning split (all 20 Hz frames from the bag start; held-out t2 logs are stats_compact and have no per-instance records). Replay validated: per-frame (n_roots, n_promoted, n_held) identical to the online back-end v2 run_01 savior_stats of SAVIOR and SAVIOR-adaptive on all 8 sequences (35472/35472 frames).

Unit: potential-class detection-frames (a detection is matched to the GT instance covering >= 30 % of its pixels, GT moving flag of that frame from moving.csv; unmatched detections excluded from shares). promoted = linked to a dynamic chain in this frame (interaction). GT-static share = static / (static + moving), by detection-frames and by mask pixels. Parent = the instance that promoted it (its own GT state).


## SAVIOR (sens_fix1): promoted detections

| level | promoted det-frames | GT-static det-frames promoted / held (of all GT-static det-frames) | GT-static share (det) | GT-static share (px) | distinct GT-static instances promoted / static movable in view | parent: standing person | parent: walking person | parent: moving forklift / carried load | parent: GT-static object (2nd hop) | parent: unmatched parent |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 296 | 0.1 % / 0.5 % | 100.0 % | 100.0 % | 131 / 1316 | 3 % | 0 % | 0 % | 69 % | 29 % |
| L1 | 18417 | 6.4 % / 5.1 % | 99.4 % | 99.8 % | 742 / 1310 | 24 % | 12 % | 0 % | 63 % | 1 % |
| L2 | 27928 | 8.8 % / 5.5 % | 87.0 % | 58.3 % | 889 / 1328 | 21 % | 9 % | 9 % | 61 % | 1 % |
| L3 | 42833 | 14.7 % / 8.4 % | 84.4 % | 15.9 % | 1184 / 1316 | 15 % | 7 % | 24 % | 54 % | 1 % |
| all | 89474 | 7.1 % / 4.7 % | 88.4 % | 24.5 % | 2946 / 5270 | 19 % | 9 % | 14 % | 58 % | 1 % |

SAVIOR: GT-static promotions by the ROOT of the chain (always-dynamic person or moving root) and by hop count

| level | root: standing person | root: walking person | root: moving forklift / carried load | root: unmatched parent | root: GT-static object | 1 hop | 2 hops | 3 hops |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 6 % | 0 % | 0 % | 94 % | 0 % | 31 % | 39 % | 30 % |
| L1 | 68 % | 30 % | 0 % | 1 % | 0 % | 37 % | 36 % | 28 % |
| L2 | 60 % | 24 % | 15 % | 1 % | 1 % | 38 % | 36 % | 25 % |
| L3 | 42 % | 39 % | 11 % | 1 % | 8 % | 31 % | 45 % | 24 % |
| all | 54 % | 32 % | 10 % | 1 % | 4 % | 35 % | 40 % | 25 % |

## SAVIOR-adaptive (p7_nb): promoted detections

| level | promoted det-frames | GT-static det-frames promoted / held (of all GT-static det-frames) | GT-static share (det) | GT-static share (px) | distinct GT-static instances promoted / static movable in view | parent: standing person | parent: walking person | parent: moving forklift / carried load | parent: GT-static object (2nd hop) | parent: unmatched parent |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 346 | 0.1 % / 0.6 % | 100.0 % | 100.0 % | 145 / 1316 | 4 % | 0 % | 0 % | 73 % | 23 % |
| L1 | 22567 | 7.9 % / 6.9 % | 99.5 % | 99.9 % | 809 / 1310 | 22 % | 12 % | 0 % | 65 % | 1 % |
| L2 | 33041 | 10.5 % / 7.8 % | 87.4 % | 59.3 % | 983 / 1328 | 18 % | 9 % | 8 % | 64 % | 1 % |
| L3 | 53372 | 18.6 % / 11.3 % | 85.9 % | 17.8 % | 1285 / 1316 | 12 % | 7 % | 25 % | 56 % | 1 % |
| all | 109326 | 8.8 % / 6.4 % | 89.3 % | 27.0 % | 3222 / 5270 | 16 % | 9 % | 14 % | 60 % | 1 % |

SAVIOR-adaptive: GT-static promotions by the ROOT of the chain (always-dynamic person or moving root) and by hop count

| level | root: standing person | root: walking person | root: moving forklift / carried load | root: unmatched parent | root: GT-static object | 1 hop | 2 hops | 3 hops |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 8 % | 0 % | 0 % | 92 % | 0 % | 27 % | 38 % | 35 % |
| L1 | 66 % | 33 % | 0 % | 1 % | 0 % | 34 % | 36 % | 30 % |
| L2 | 57 % | 26 % | 15 % | 1 % | 1 % | 35 % | 36 % | 28 % |
| L3 | 38 % | 43 % | 11 % | 1 % | 7 % | 27 % | 45 % | 28 % |
| all | 50 % | 36 % | 10 % | 1 % | 3 % | 31 % | 40 % | 29 % |

## SAVIOR w/o motion (sf1_nomotion): promoted detections

| level | promoted det-frames | GT-static det-frames promoted / held (of all GT-static det-frames) | GT-static share (det) | GT-static share (px) | distinct GT-static instances promoted / static movable in view | parent: standing person | parent: walking person | parent: moving forklift / carried load | parent: GT-static object (2nd hop) | parent: unmatched parent |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 362 | 0.1 % / 0.3 % | 100.0 % | 100.0 % | 131 / 1316 | 2 % | 0 % | 0 % | 73 % | 25 % |
| L1 | 19199 | 6.7 % / 2.7 % | 99.4 % | 99.8 % | 747 / 1310 | 23 % | 13 % | 0 % | 63 % | 1 % |
| L2 | 28949 | 8.6 % / 2.9 % | 81.8 % | 39.2 % | 847 / 1328 | 22 % | 10 % | 7 % | 61 % | 1 % |
| L3 | 41782 | 13.6 % / 4.3 % | 80.3 % | 14.2 % | 1098 / 1316 | 17 % | 9 % | 24 % | 50 % | 1 % |
| all | 90292 | 6.9 % / 2.4 % | 84.9 % | 21.3 % | 2823 / 5270 | 20 % | 10 % | 13 % | 57 % | 1 % |

SAVIOR w/o motion: GT-static promotions by the ROOT of the chain (always-dynamic person or moving root) and by hop count

| level | root: standing person | root: walking person | root: moving forklift / carried load | root: unmatched parent | root: GT-static object | 1 hop | 2 hops | 3 hops |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 5 % | 0 % | 0 % | 95 % | 0 % | 27 % | 41 % | 32 % |
| L1 | 67 % | 31 % | 0 % | 2 % | 0 % | 36 % | 36 % | 28 % |
| L2 | 64 % | 35 % | 0 % | 1 % | 0 % | 32 % | 39 % | 29 % |
| L3 | 48 % | 51 % | 0 % | 1 % | 0 % | 25 % | 49 % | 26 % |
| all | 58 % | 41 % | 0 % | 2 % | 0 % | 30 % | 43 % | 27 % |

## SAVIOR w/o interaction (sf1_noint): promoted detections

| level | promoted det-frames | GT-static det-frames promoted / held (of all GT-static det-frames) | GT-static share (det) | GT-static share (px) | distinct GT-static instances promoted / static movable in view | parent: standing person | parent: walking person | parent: moving forklift / carried load | parent: GT-static object (2nd hop) | parent: unmatched parent |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 0 | 0.0 % / 0.1 % | 0.0 % | 0.0 % | 0 / 1316 | 0 % | 0 % | 0 % | 0 % | 0 % |
| L1 | 0 | 0.0 % / 0.1 % | 0.0 % | 0.0 % | 0 / 1310 | 0 % | 0 % | 0 % | 0 % | 0 % |
| L2 | 0 | 0.0 % / 0.1 % | 0.0 % | 0.0 % | 0 / 1328 | 0 % | 0 % | 0 % | 0 % | 0 % |
| L3 | 0 | 0.0 % / 0.2 % | 0.0 % | 0.0 % | 0 / 1316 | 0 % | 0 % | 0 % | 0 % | 0 % |
| all | 0 | 0.0 % / 0.1 % | 0.0 % | 0.0 % | 0 / 5270 | 0 % | 0 % | 0 % | 0 % | 0 % |

SAVIOR w/o interaction: GT-static promotions by the ROOT of the chain (always-dynamic person or moving root) and by hop count

| level | root: standing person | root: walking person | root: moving forklift / carried load | root: unmatched parent | root: GT-static object | 1 hop | 2 hops | 3 hops |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| L0 | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |
| L1 | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |
| L2 | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |
| L3 | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |
| all | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |

Notes: the "moving forklift / carried load" parent column is the reviewer's case (a GT-static stack promoted through contact with a moving vehicle or its load). SAVIOR w/o interaction has no promotions by construction (sanity check).
