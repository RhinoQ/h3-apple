"""Automatic small-face tracking and the accepted native-size feathered composite."""
import numpy as np
from PIL import Image

def fill_single_gaps(rows):
    """Bridge one empty frame only between unambiguous overlapping detections."""
    original = [r['boxes'] for r in rows]
    for i in range(1,len(rows)-1):
        if original[i] or rows[i]['cut'] or rows[i+1]['cut']:
            continue
        if len(original[i-1]) != 1 or len(original[i+1]) != 1:
            continue
        a,b = original[i-1][0],original[i+1][0]
        intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
        union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
        if union > 0 and intersection/union >= .5:
            rows[i]['boxes']=[[(a[j]+b[j])/2 for j in range(4)]+[min(a[4],b[4])]]
            rows[i]['interpolated_single_gap']=True

def association(rows, width, height):
    """Consecutive-only nearest-box tracks; never bridge cuts or missing faces."""
    tracks = {}; previous = []; serial = 0
    for row in rows:
        current = []
        available = [] if row['cut'] else previous.copy()
        for box in sorted(row['boxes'], key=lambda b: b[0]):
            cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
            options = []
            for old in available:
                b = old['source_box']; ox, oy = (b[0]+b[2])/2, (b[1]+b[3])/2
                distance = ((cx-ox)**2+(cy-oy)**2)**.5
                scale = max(box[2]-box[0], box[3]-box[1], b[2]-b[0], b[3]-b[1])
                ratio = max(box[2]-box[0], box[3]-box[1])/max(b[2]-b[0], b[3]-b[1])
                if distance <= scale*.5 and .5 <= ratio <= 2:
                    options.append((distance, old['track'], old))
            if options:
                _, track, old = min(options, key=lambda v: (v[0], v[1]))
                available.remove(old)
            else:
                track = serial; serial += 1
            rec = dict(frame=row['frame'], track=track, source_box=box[:4], confidence=box[4],
                       interpolated_single_gap=row.get('interpolated_single_gap',False))
            current.append(rec); tracks.setdefault(track, []).append(rec)
        previous = current
    selected = []
    for track in tracks.values():
        # A 256-pixel context cannot contain a large face's feathered mask.
        # Freeze eligibility for the whole contiguous track to avoid threshold flicker.
        sizes = [max(r['source_box'][2]-r['source_box'][0], r['source_box'][3]-r['source_box'][1]) for r in track]
        if len(track) < 5 or min(sizes) < 32 or max(sizes) > 160:
            continue
        for n, rec in enumerate(track):
            neighbors = track[max(0,n-4):n+5]
            cx = sum((r['source_box'][0]+r['source_box'][2])/2 for r in neighbors)/len(neighbors)
            cy = sum((r['source_box'][1]+r['source_box'][3])/2 for r in neighbors)/len(neighbors)
            left = int(np.clip(round(cx-128), 0, width-256))
            top = int(np.clip(round(cy-128), 0, height-256))
            selected.append(dict(**rec, crop=[left,top,left+256,top+256]))
    return sorted(selected, key=lambda r: (r['frame'], r['track'])), tracks

def alpha_mask(record):
    left, top, right, bottom = record['crop']
    x0, y0, x1, y1 = record['source_box']
    cx, cy = (x0+x1)/2, (y0+y1)/2
    rx, ry = (x1-x0)*.70, (y1-y0)*.70
    yy, xx = np.mgrid[top:bottom, left:right]
    # A source-derived rectangle with cosine feather, never an output-derived mask.
    d = np.maximum(np.abs((xx-cx)/rx), np.abs((yy-cy)/ry))
    t = np.clip((1-d)/.25, 0, 1)
    return ((1-np.cos(np.pi*t))*.5).astype(np.float32)

def composite(source, restored_native, record):
    output = np.asarray(source).copy()
    left, top, right, bottom = record['crop']
    patch = np.asarray(restored_native)
    assert patch.shape == (256,256,3)
    alpha = alpha_mask(record)
    original = output[top:bottom, left:right].copy()
    mixed = np.rint(original*(1-alpha[...,None])+patch*alpha[...,None]).clip(0,255).astype(np.uint8)
    assert np.array_equal(mixed[alpha == 0], original[alpha == 0])
    output[top:bottom, left:right] = mixed
    return Image.fromarray(output)
