"""Independent integer and FP64 selected-route reference for Q smoothing."""
from types import SimpleNamespace
import pytest
np = pytest.importorskip("numpy")
pytest.importorskip("mlx.core")

pytestmark = pytest.mark.hardware


def inputs(constant=False):
    import mlx.core as mx
    rng = np.random.default_rng(138)
    sizes=np.array([23,64,17,64],np.int32)
    g=SimpleNamespace(tile_elems=64,num_prefix_tiles=1,num_video_tiles=3,
        padded_length=256,variable_block_sizes=sizes)
    arrays=[rng.normal(size=(256,2,128)).astype(np.float32) for _ in range(3)]
    arrays[0][:,:,::4]+=6
    arrays[1][64:128]+=2
    if constant: arrays[2][:]=3.5
    for a in arrays:
        for b,length in enumerate(sizes): a[b*64+length:(b+1)*64]=123
    q,k,v=[mx.array(a,mx.bfloat16) for a in arrays]
    idx=mx.array([[[0,2,1],[2,1,-9],[1,0,-9]],[[1,0,2],[0,2,-9],[2,1,0]]],mx.int32)
    num=mx.array([[3,2,2],[3,2,3]],mx.int32)
    return q,k,v,idx,num,g,128**-.5


@pytest.mark.parametrize("constant",[False,True])
def test_integer_dots_correction_float_pv_and_padding(constant):
    import mlx.core as mx
    from h3_apple.runtime.qk_smooth import SmoothQKSparse
    q,k,v,idx,num,g,scale=inputs(constant)
    candidate=SmoothQKSparse()
    pack=candidate.pack(q,k,v,idx,num,g)
    packed,scales,correction,sizes=pack
    pq,pk,pv=[np.asarray(x.astype(mx.float32)) for x in packed]
    qs,ks=[np.asarray(x) for x in scales]
    corr=np.asarray(correction)
    sizes=np.asarray(sizes)
    valid=np.concatenate([np.arange(b*64,b*64+n) for b,n in enumerate(sizes)])
    validq=valid[valid>=64]
    qf,kf=[np.asarray(x.astype(mx.float32)) for x in (q,k)]
    qmean=qf[validq].astype(np.float64).mean(0)
    kmean=kf[valid].astype(np.float64).mean(0)
    centered=kf.astype(np.float64)-kmean
    exact_corr=np.einsum('thd,hd->ht',centered,qmean)
    for b,n in enumerate(sizes[:3]):
        np.testing.assert_allclose(corr[:,b*64:b*64+n],exact_corr[:,b*64:b*64+n],atol=2e-4,rtol=2e-5)
    np.testing.assert_array_equal(pk[:,192:],0)
    np.testing.assert_array_equal(pq[:,:64],0)
    np.testing.assert_array_equal(corr[:,192:],0)
    # Mean restoration identity before quantization, modulo a per-query constant.
    lhs=qf[validq,0].astype(np.float64) @ kf[valid,0].astype(np.float64).T
    rhs=(qf[validq,0]-qmean[0]) @ centered[valid,0].T+exact_corr[0,valid]
    np.testing.assert_allclose((lhs-rhs)-(qf[validq,0]@kmean[0])[:,None],0,atol=1e-10)
    actual,dots=candidate.run_packed(*pack,idx,num,g,scale,debug=True)
    mx.eval(actual,dots)
    expected=np.zeros((2,256,128),np.float64)
    expected_dots=np.zeros(dots.shape,np.int32)
    indices,counts=np.asarray(idx),np.asarray(num)
    for h in range(2):
        for tile in range(3):
            query=slice((tile+1)*64,(tile+2)*64)
            maximum=np.full(64,-np.inf); den=np.zeros(64); state=np.zeros((64,128))
            for r,route in enumerate(indices[h,tile,:counts[h,tile]]):
                key=slice(route*64,(route+1)*64)
                dot=pq[h,query].astype(np.int32)@pk[h,key].astype(np.int32).T
                expected_dots[h,tile,r]=dot
                for half in (0,32):
                    length=min(32,int(sizes[route])-half)
                    if length<=0: continue
                    kr=slice(route*64+half,route*64+half+length)
                    scores=(dot[:,half:half+length].astype(np.float64)*qs[h,query,None]*ks[h,None,kr]+corr[h,None,kr])*scale
                    newmax=np.maximum(maximum,scores.max(1))
                    adjust=np.exp(maximum-newmax); p=np.exp(scores-newmax[:,None])
                    state=state*adjust[:,None]+p@pv[h,kr]
                    den=den*adjust+p.sum(1); maximum=newmax
            expected[h,query]=state/den[:,None]
    for b,n in enumerate(sizes): expected[:,b*64+n:(b+1)*64]=0
    # The original kernel never visits a wholly invalid 32-key half.
    for h in range(2):
        for tile in range(3):
            for r,route in enumerate(indices[h,tile,:counts[h,tile]]):
                if sizes[route]<=32: expected_dots[h,tile,r,:,32:]=0
    np.testing.assert_array_equal(np.asarray(dots),expected_dots)
    observed=np.asarray(actual.astype(mx.float32))
    np.testing.assert_allclose(observed,expected,atol=.025,rtol=.006)
    np.testing.assert_array_equal(observed[:,:64],0)
    if constant:
        for b,n in enumerate(sizes[1:],1): np.testing.assert_array_equal(observed[:,b*64:b*64+n],3.5)
    ordinary=candidate(q,k,v,idx,num,g,scale)
    np.testing.assert_array_equal(np.asarray(ordinary.astype(mx.float32)),observed.transpose(1,0,2))


def test_invalid_route():
    import mlx.core as mx
    from h3_apple.runtime.qk_smooth import SmoothQKSparse
    args=list(inputs())
    args[3]=mx.full(args[3].shape,4,mx.int32)
    with pytest.raises(ValueError,match="out of bounds"): SmoothQKSparse()(*args)
