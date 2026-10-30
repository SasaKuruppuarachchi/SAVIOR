"""trtbench.py engine [engine ...]: pure TensorRT GPU time per inference (CUDA events around execute_async_v3, batch 1,
torch-allocated IO, 50 warmup + 300 timed, interleaved rounds) -> json lines {engine, gpu_ms median/p90/min, wall_ms}."""
import json, sys, time
import numpy as np
import tensorrt as trt
import torch
logger = trt.Logger(trt.Logger.WARNING)
res = {}
ctxs = {}
for p in sys.argv[1:]:
    with open(p, 'rb') as f:
        data = f.read()
    # ultralytics engines carry a json metadata header: 4-byte little-endian length + json, then the plan
    try:
        n = int.from_bytes(data[:4], 'little')
        json.loads(data[4:4 + n].decode())
        plan = data[4 + n:]
    except Exception:
        plan = data
    eng = trt.Runtime(logger).deserialize_cuda_engine(plan)
    ctx = eng.create_execution_context()
    bufs = {}
    for i in range(eng.num_io_tensors):
        name = eng.get_tensor_name(i)
        shp = tuple(eng.get_tensor_shape(name))
        dt = {trt.float32: torch.float32, trt.float16: torch.float16, trt.int32: torch.int32, trt.int8: torch.int8}[eng.get_tensor_dtype(name)]
        t = torch.rand(shp, device='cuda').to(dt) if dt.is_floating_point else torch.zeros(shp, dtype=dt, device='cuda')
        bufs[name] = t
        ctx.set_tensor_address(name, t.data_ptr())
    ctxs[p] = (eng, ctx, bufs)
stream = torch.cuda.Stream()
times = {p: [] for p in ctxs}
walls = {p: [] for p in ctxs}
for rnd in range(6):
    for p, (eng, ctx, bufs) in ctxs.items():
        for i in range(60):
            s, e = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
            t0 = time.perf_counter()
            s.record(stream)
            ctx.execute_async_v3(stream.cuda_stream)
            e.record(stream)
            e.synchronize()
            w = (time.perf_counter() - t0) * 1e3
            if rnd > 0:
                times[p].append(s.elapsed_time(e)); walls[p].append(w)
for p in ctxs:
    a = np.array(times[p]); w = np.array(walls[p])
    print(json.dumps({'engine': p.split('/')[-1], 'gpu_ms_med': round(float(np.median(a)), 3), 'gpu_ms_p90': round(float(np.percentile(a, 90)), 3),
                      'gpu_ms_min': round(float(a.min()), 3), 'wall_ms_med': round(float(np.median(w)), 3), 'n': int(a.size)}), flush=True)
