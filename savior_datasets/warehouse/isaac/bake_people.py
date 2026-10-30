# SPDX-License-Identifier: GPL-3.0-or-later
"""Bake retargeted people animations (walk loop in place, idle loop, sit) for every character (run once).

The Isaac People characters use a 101-joint Reallusion skeleton, the clips in People/Animations a 81-joint biped
skeleton. Both carry omni.anim.retarget tags; the biped source skeleton itself ships with the IRA extension
(isaacsim.replicator.agent.core/data/test_scenes/test_biped/biped_demo_meters.usd). We run the retargeter
offline (CreateRetargetAnimationsCommand) and store the clips per character in <data>/cache/anims/<char>.usda;
the renderer then samples them per frame (deterministic, no animation graph / timeline involved).

  $HOME/isaacsim/python.sh isaac/bake_people.py [--chars a b ...]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

CLIPS = {'walk': 'stand_walk_loop_in_place', 'idle': 'stand_idle_loop', 'sit': 'Sit'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chars', nargs='*', default=common.CHARACTERS)
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()
    app = common.start_app()
    from isaacsim.core.utils.extensions import enable_extension, get_extension_path_from_name
    enable_extension('omni.anim.retarget.core')
    enable_extension(common.IRA_BIPED)
    for _ in range(5):
        app.update()
    import omni.kit.commands
    import omni.usd
    from pxr import Sdf, Usd, UsdGeom
    biped = os.path.join(get_extension_path_from_name(common.IRA_BIPED), 'data', 'test_scenes', 'test_biped',
                         'biped_demo_meters.usd')
    os.makedirs(common.ANIM_CACHE, exist_ok=True)
    for ch in args.chars:
        out = os.path.join(common.ANIM_CACHE, f'{ch}.usda')
        if os.path.exists(out) and not args.force:
            print(f'[bake] {ch}: exists')
            continue
        omni.usd.get_context().new_stage()
        app.update()
        st = omni.usd.get_context().get_stage()
        UsdGeom.SetStageUpAxis(st, 'Z')
        UsdGeom.SetStageMetersPerUnit(st, 1.0)
        b = st.DefinePrim('/Biped', 'Xform')
        b.GetReferences().AddReference(biped)
        c = st.DefinePrim('/Char', 'Xform')
        c.GetReferences().AddReference(common.char_usd(ch))
        st.DefinePrim('/Anims', 'Scope')
        st.DefinePrim('/Out', 'Scope')
        for k, clip in CLIPS.items():
            st.DefinePrim(f'/Anims/{k}', 'SkelAnimation').GetReferences().AddReference(
                common.asset(f'Isaac/People/Animations/{clip}.skelanim.usd'))
        for _ in range(3):
            app.update()
        src = [p for p in Usd.PrimRange(b) if p.GetTypeName() == 'Skeleton'][0]
        tgt = [p for p in Usd.PrimRange(c) if p.GetTypeName() == 'Skeleton'][0]
        omni.kit.commands.execute('CreateRetargetAnimationsCommand', source_skeleton_path=str(src.GetPath()),
                                  target_skeleton_path=str(tgt.GetPath()),
                                  source_animation_paths=[f'/Anims/{k}' for k in CLIPS],
                                  target_animation_parent_path='/Out', set_root_identity=False)
        layer = Sdf.Layer.CreateNew(out)
        for k in CLIPS:
            Sdf.CreatePrimInLayer(layer, '/Out')
            Sdf.CopySpec(st.GetRootLayer(), f'/Out/{k}', layer, f'/Out/{k}')
        layer.customLayerData = {'character': ch, 'skeleton': str(tgt.GetPath()).replace('/Char', ''),
                                 'source': 'People/Animations ' + ', '.join(CLIPS.values())}
        layer.Save()
        print(f'[bake] {ch}: wrote {out}')
    app.close()


if __name__ == '__main__':
    main()
