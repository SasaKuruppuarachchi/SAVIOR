#!/usr/bin/env python3
"""export_masks_t3.py <export_masks.py args> : the UNCHANGED frozen src/savior/sota/mask_export/export_masks.py on t3
sequences. The frozen frozen_params.is_viode() recognises warehouse sequences by the names aisles_/hall_/dock_ only;
this wrapper makes it return False (warehouse) for '<id>_t3_L<k>' names and changes nothing else (same module objects,
same frozen settings, bag path data/warehouse/ros2_stereoseg/<seq>). Run inside the savior image like export_masks.py."""
import os
import runpy
import sys

D = '/home/sasa/workspace/savior_ws/src/savior/sota/mask_export'
sys.path.insert(0, D)
import frozen_params  # noqa: E402

_is_viode = frozen_params.is_viode
frozen_params.is_viode = lambda seq: False if '_t3_L' in seq else _is_viode(seq)
sys.argv = [os.path.join(D, 'export_masks.py')] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
