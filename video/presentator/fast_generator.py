"""CPU fast path for OcclusionAwareSPADEGenerator (added for CPU-only use).

Numerically equivalent to generator(source_image, kp_driving=..., kp_source=...) but:
  * the source-image encoding (first/down/second/resblocks_3d + dense-motion
    compress/norm) is computed once and cached instead of once per frame;
  * spectral norm is baked into the conv weights;
  * the two heavy, purely convolutional parts (3D hourglass + mask/occlusion
    convs, and third/fourth/SPADE decoder) run through OpenVINO on CPU
    (~2x faster than PyTorch's oneDNN path on this machine).
grid_sample / softmax / keypoint maths stay in PyTorch.

Enable/disable with env SADTALKER_FAST=1/0 (default 1 when running on CPU).
SADTALKER_OV_INT8=1 additionally int8-quantizes the decoder weights (experimental).
"""
import os
import torch
import torch.nn as nn
import torch.nn.functional as F


class _DMHead(nn.Module):
    """hourglass -> (mask logits, occlusion map)"""

    def __init__(self, dm):
        super().__init__()
        self.dm = dm

    def forward(self, input_):
        dm = self.dm
        prediction = dm.hourglass(input_)
        mask = dm.mask(prediction)
        bs, c, d, h, w = prediction.shape
        occ = torch.sigmoid(dm.occlusion(prediction.reshape(bs, c * d, h, w)))
        return mask, occ


class _DecHead(nn.Module):
    """third/fourth/occlusion/SPADE decoder -> image"""

    def __init__(self, g):
        super().__init__()
        self.g = g

    def forward(self, feat2d, occ):
        g = self.g
        out = g.third(feat2d)
        out = g.fourth(out)
        if out.shape[2] != occ.shape[2] or out.shape[3] != occ.shape[3]:
            occ = F.interpolate(occ, size=out.shape[2:], mode='bilinear')
        out = out * occ
        return g.decoder(out)


class FastGenerator:
    def __init__(self, generator):
        self.g = generator.eval()
        for m in list(self.g.modules()):
            if hasattr(m, 'weight_orig'):
                torch.nn.utils.remove_spectral_norm(m)
        self._src_key = None
        self._ov = {}
        try:
            import openvino as ov
            self.core = ov.Core()
            self.core.set_property('CPU', {'PERFORMANCE_HINT': 'LATENCY'})
        except Exception as e:  # fall back to torch for the heavy parts
            print('[fast_generator] OpenVINO unavailable, using torch:', e)
            self.core = None

    # ---------------------------------------------------------------- helpers
    def _compiled(self, name, module, example):
        key = (name,) + tuple(tuple(t.shape) for t in example)
        if key not in self._ov:
            import openvino as ov
            int8 = name == 'dec' and os.environ.get('SADTALKER_OV_INT8', '0') == '1'
            cache_dir = os.environ.get('SADTALKER_OV_CACHE', os.path.join('checkpoints', 'ov_cache'))
            os.makedirs(cache_dir, exist_ok=True)
            fname = '_'.join([name] + ['x'.join(map(str, s)) for s in key[1:]]) + ('_int8' if int8 else '') + '.xml'
            xml = os.path.join(cache_dir, fname)
            if os.path.isfile(xml):
                m = self.core.read_model(xml)
            else:
                m = ov.convert_model(module, example_input=example)
                if int8:
                    import nncf
                    m = nncf.compress_weights(m, mode=nncf.CompressWeightsMode.INT8_ASYM)
                ov.save_model(m, xml, compress_to_fp16=False)
            self._ov[key] = self.core.compile_model(m, 'CPU')
        return self._ov[key]

    def _run(self, name, module, *inputs):
        if self.core is None:
            out = module(*inputs)
            return out if isinstance(out, tuple) else (out,)
        c = self._compiled(name, module, inputs)
        res = c([t.contiguous().numpy() for t in inputs])
        return tuple(torch.from_numpy(res[i].copy()) for i in range(len(c.outputs)))

    def _encode_source(self, source_image):
        g = self.g
        dm = g.dense_motion_network
        out = g.first(source_image)
        for blk in g.down_blocks:
            out = blk(out)
        out = g.second(out)
        bs, c, h, w = out.shape
        feature_3d = g.resblocks_3d(out.view(bs, g.reshape_channel, g.reshape_depth, h, w))
        comp = F.relu(dm.norm(dm.compress(feature_3d)))
        return feature_3d, comp

    # ------------------------------------------------------------------- call
    @torch.no_grad()
    def __call__(self, source_image, kp_driving, kp_source):
        g = self.g
        dm = g.dense_motion_network
        key = (source_image.data_ptr(), tuple(source_image.shape))
        if self._src_key != key:
            self._feature_3d, self._comp = self._encode_source(source_image)
            self._src_key = key
        feature_3d, comp = self._feature_3d, self._comp

        bs, _, d, h, w = comp.shape
        sparse_motion = dm.create_sparse_motions(comp, kp_driving, kp_source)
        deformed = dm.create_deformed_feature(comp, sparse_motion)
        heatmap = dm.create_heatmap_representations(deformed, kp_driving, kp_source)
        input_ = torch.cat([heatmap, deformed], dim=2).view(bs, -1, d, h, w)

        mask, occ = self._run('dm', _DMHead(dm).eval(), input_)
        mask = F.softmax(mask, dim=1).unsqueeze(2)
        mask = torch.where(mask < 1e-3, torch.zeros_like(mask), mask)
        sparse_motion = sparse_motion.permute(0, 1, 5, 2, 3, 4)
        deformation = (sparse_motion * mask).sum(dim=1).permute(0, 2, 3, 4, 1)

        out = g.deform_input(feature_3d, deformation)
        b, c, dd, hh, ww = out.shape
        out = out.view(b, c * dd, hh, ww)
        (pred,) = self._run('dec', _DecHead(g).eval(), out, occ)
        return {'prediction': pred}


def maybe_fast(generator, device):
    if str(device) != 'cpu' or os.environ.get('SADTALKER_FAST', '1') != '1':
        return generator
    return FastGenerator(generator)
