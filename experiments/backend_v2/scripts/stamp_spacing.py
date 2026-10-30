#!/usr/bin/env python3
"""stamp_spacing.py <bag dir>... : header-stamp spacing of /cam0/image_raw (bag METADATA only: reads the CDR header stamp of
each image message via rosbag2_py; no estimator, perception or ground truth involved) and the frames that
OpenVINS' callback_stereo keeps for a given track_frequency (rule: keep if t >= t_last_kept + 1/f)."""
import struct, sys
import numpy as np

for bag in sys.argv[1:]:
    import rosbag2_py
    r = rosbag2_py.SequentialCompressionReader()  # handles message-level zstd (warehouse) and plain bags
    r.open(rosbag2_py.StorageOptions(uri=bag, storage_id=''), rosbag2_py.ConverterOptions('', ''))
    r.set_filter(rosbag2_py.StorageFilter(topics=['/cam0/image_raw']))
    st = []
    while r.has_next():
        _, data, _ = r.read_next()
        sec, nsec = struct.unpack_from('<iI', data, 4)
        st.append(sec + nsec * 1e-9)
    t = np.array(sorted(st))
    dt = np.diff(t)
    out = [bag.rstrip('/').split('/')[-1], f'n={t.size}', f'dt median {np.median(dt)*1e3:.2f} ms',
           f'min {dt.min()*1e3:.2f} max {dt.max()*1e3:.2f}', f'|dt-50ms|>1ms: {(np.abs(dt-0.05) > 1e-3).sum()}']
    for f in (21.0, 10.5):
        keep, last = [], -1e9
        for x in t:
            if x >= last + 1.0 / f:
                keep.append(x); last = x
        kd = np.diff(keep)
        out.append(f'f={f}: kept {len(keep)} ({len(keep)/t.size:.3f}), kept-dt median {np.median(kd)*1e3:.1f} ms, '
                   f'>=140 ms gaps {(kd >= 0.14).sum()}')
    print(' | '.join(out))
