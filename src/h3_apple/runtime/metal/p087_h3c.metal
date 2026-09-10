inline uint h3_compact_morton_even_bits(uint value) {
    value &= 0x55555555u;
    value = (value | (value >> 1)) & 0x33333333u;
    value = (value | (value >> 2)) & 0x0f0f0f0fu;
    value = (value | (value >> 4)) & 0x00ff00ffu;
    value = (value | (value >> 8)) & 0x0000ffffu;
    return value;
}

inline uint h3_lower_bits_mask(uint bits) {
    return bits ? (1u << bits) - 1u : 0u;
}

inline uint2 h3_morton_decode_rectangular(uint code, uint x_bits,
                                          uint y_bits) {
    uint paired_bits = min(x_bits, y_bits);
    uint paired_code = code & h3_lower_bits_mask(paired_bits * 2);
    uint2 tile = uint2(h3_compact_morton_even_bits(paired_code),
                       h3_compact_morton_even_bits(paired_code >> 1));
    uint tail = code >> (paired_bits * 2);
    if (x_bits > paired_bits) {
        uint extra = x_bits - paired_bits;
        tile.x |= (tail & h3_lower_bits_mask(extra)) << paired_bits;
        tail >>= extra;
    }
    if (y_bits > paired_bits) tile.y |= tail << paired_bits;
    return tile;
}

/* Compact four-column Morton blocks. Full 4x4 row blocks use a true Morton
 * code; the final 1-3 row strip is packed without launching empty groups. */
inline uint2 h3_morton_decode_compact4(uint code, uint row_tiles) {
    uint groups_per_column_block = row_tiles * 4;
    uint column_block = code / groups_per_column_block;
    uint local = code - column_block * groups_per_column_block;
    uint full_rows = row_tiles & ~3u;
    uint full_groups = full_rows * 4;
    if (local < full_groups) {
        uint row_block = local >> 4;
        uint2 tile = uint2(h3_compact_morton_even_bits(local & 15u),
                           h3_compact_morton_even_bits((local & 15u) >> 1));
        return uint2(row_block * 4 + tile.x,
                     column_block * 4 + tile.y);
    }
    uint tail_rows = row_tiles - full_rows;
    uint tail = local - full_groups;
    return uint2(full_rows + tail % tail_rows,
                 column_block * 4 + tail / tail_rows);
}

/* Exact compact Morton walk for a final 1-3 column strip as well. */
inline uint2 h3_morton_decode_compact(uint code, uint row_tiles,
                                      uint column_tiles) {
    uint full_columns = column_tiles & ~3u;
    uint full_groups = row_tiles * full_columns;
    if (code < full_groups)
        return h3_morton_decode_compact4(code, row_tiles);
    uint tail_columns = column_tiles - full_columns;
    uint tail = code - full_groups;
    return uint2(tail / tail_columns,
                 full_columns + tail % tail_columns);
}



inline float h3_int8_reduce_max(float value, threadgroup float *scratch,
                                ushort simdgroup, ushort lane) {
    value = max(value, simd_shuffle_xor(value, 16));
    value = max(value, simd_shuffle_xor(value, 8));
    value = max(value, simd_shuffle_xor(value, 4));
    value = max(value, simd_shuffle_xor(value, 2));
    value = max(value, simd_shuffle_xor(value, 1));
    if (lane == 0) scratch[simdgroup] = value;
    threadgroup_barrier(mem_flags::mem_threadgroup);
    if (simdgroup == 0) {
        value = lane < 8 ? scratch[lane] : 0.0f;
        value = max(value, simd_shuffle_xor(value, 16));
        value = max(value, simd_shuffle_xor(value, 8));
        value = max(value, simd_shuffle_xor(value, 4));
        value = max(value, simd_shuffle_xor(value, 2));
        value = max(value, simd_shuffle_xor(value, 1));
        if (lane == 0) scratch[0] = value;
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    return scratch[0];
}

kernel void h3_quantize_bf16_int8_rows(
                           device const bfloat *input [[buffer(0)]],
                           device int8_t *output [[buffer(1)]],
                           device float *scales [[buffer(2)]],
                           constant int8_quant_args &args [[buffer(3)]],
                           uint tid [[thread_index_in_threadgroup]],
                           ushort simdgroup
                               [[simdgroup_index_in_threadgroup]],
                           ushort lane [[thread_index_in_simdgroup]],
                           uint row [[threadgroup_position_in_grid]]) {
    uint base = row * args.columns;
    if (row >= args.rows) {
        if ((args.columns & 3u) == 0) {
            device char4 *output4 =
                reinterpret_cast<device char4 *>(output);
            uint vector_base = row * (args.columns / 4);
            for (uint column = tid; column < args.columns / 4;
                 column += 256)
                output4[vector_base + column] = char4(0);
        } else {
            for (uint column = tid; column < args.columns; column += 256)
                output[base + column] = 0;
        }
        if (tid == 0) scales[row] = 1.0f;
        return;
    }
    threadgroup float scratch[8];
    float local_max = 0.0f;
    if ((args.columns & 3u) == 0) {
        device const bfloat4 *input4 =
            reinterpret_cast<device const bfloat4 *>(input);
        uint vectors_per_row = args.columns / 4;
        uint vector_base = row * vectors_per_row;
        for (uint column = tid; column < vectors_per_row; column += 256) {
            float4 value = float4(input4[vector_base + column]);
            local_max = max(local_max,
                max(max(fabs(value.x), fabs(value.y)),
                    max(fabs(value.z), fabs(value.w))));
        }
    } else {
        for (uint column = tid; column < args.columns; column += 256)
            local_max = max(local_max, fabs((float)input[base + column]));
    }
    float max_abs = h3_int8_reduce_max(
        local_max, scratch, simdgroup, lane);
    float clipped_max = max_abs * args.clip;
    float scale = clipped_max > 0.0f ? clipped_max / 127.0f : 1.0f / 127.0f;
    float inverse = clipped_max > 0.0f ? 127.0f / clipped_max : 127.0f;
    if (tid == 0) scales[row] = scale;
    if ((args.columns & 3u) == 0) {
        device const bfloat4 *input4 =
            reinterpret_cast<device const bfloat4 *>(input);
        device char4 *output4 =
            reinterpret_cast<device char4 *>(output);
        uint vectors_per_row = args.columns / 4;
        uint vector_base = row * vectors_per_row;
        for (uint column = tid; column < vectors_per_row; column += 256) {
            int4 quantized = int4(rint(
                float4(input4[vector_base + column]) * inverse));
            output4[vector_base + column] =
                char4(clamp(quantized, int4(-127), int4(127)));
        }
    } else {
        for (uint column = tid; column < args.columns; column += 256) {
            int quantized = (int)rint((float)input[base + column] * inverse);
            output[base + column] =
                (int8_t)clamp(quantized, -127, 127);
        }
    }
}

kernel void h3_quantize_bf16_int8_groups(
                           device const bfloat *input [[buffer(0)]],
                           device int8_t *output [[buffer(1)]],
                           device float *scales [[buffer(2)]],
                           constant int8_group_quant_args &args [[buffer(3)]],
                           uint tid [[thread_index_in_threadgroup]],
                           ushort simdgroup
                               [[simdgroup_index_in_threadgroup]],
                           ushort lane [[thread_index_in_simdgroup]],
                           uint row [[threadgroup_position_in_grid]]) {
    uint vectors_per_row = args.columns / 4;
    uint vectors_per_group = args.group_size / 4;
    uint vector_base = row * vectors_per_row;
    device const bfloat4 *input4 =
        reinterpret_cast<device const bfloat4 *>(input);
    device char4 *output4 = reinterpret_cast<device char4 *>(output);
    if (row >= args.rows) {
        for (uint column = tid; column < vectors_per_row; column += 256)
            output4[vector_base + column] = char4(0);
        for (uint group = tid; group < args.groups; group += 256)
            scales[row * args.groups + group] = 1.0f;
        return;
    }
    threadgroup float scratch[8];
    for (uint group = 0; group < args.groups; group++) {
        uint start = vector_base + group * vectors_per_group;
        float local_max = 0.0f;
        for (uint local = tid; local < vectors_per_group; local += 256) {
            float4 value = float4(input4[start + local]);
            local_max = max(local_max,
                max(max(fabs(value.x), fabs(value.y)),
                    max(fabs(value.z), fabs(value.w))));
        }
        float max_abs = h3_int8_reduce_max(
            local_max, scratch, simdgroup, lane);
        float scale = max_abs > 0.0f ? max_abs / 127.0f : 1.0f / 127.0f;
        float inverse = max_abs > 0.0f ? 127.0f / max_abs : 127.0f;
        if (tid == 0) scales[row * args.groups + group] = scale;
        for (uint local = tid; local < vectors_per_group; local += 256) {
            int4 quantized = int4(rint(float4(input4[start + local]) *
                                       inverse));
            output4[start + local] =
                char4(clamp(quantized, int4(-127), int4(127)));
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }
}

kernel void h3_fc1_swiglu_int8_nax_r128_impl(
                           device int8_t *input [[buffer(0)]],
                           device int8_t *weight [[buffer(1)]],
                           device const float *input_scales [[buffer(2)]],
                           device const float *weight_scales [[buffer(3)]],
                           device bfloat *output [[buffer(4)]],
                           constant linear_args &args [[buffer(5)]],
                           uint code [[threadgroup_position_in_grid]]) {
    constexpr uint TILE = 128;
    uint padded_rows = (args.rows + TILE - 1) & ~(TILE - 1);
    uint row_tiles = padded_rows / TILE;
    uint column_tiles = args.output_dim / TILE;
    uint2 group = h3_morton_decode_compact(
        code, row_tiles, column_tiles);
    uint row_start = group.x * TILE;
    uint column_start = group.y * TILE;
    uint input_dim = INPUT_DIM ? INPUT_DIM : args.input_dim;
    constexpr bool FULL_PRODUCT = INPUT_DIM != 0 && K_TILE == INPUT_DIM;
    auto x = tensor<device int8_t, dextents<int32_t, 2>, tensor_inline>(
        input, dextents<int32_t, 2>((int)input_dim,
                                    (int)padded_rows));
    auto w = tensor<device int8_t, dextents<int32_t, 2>, tensor_inline>(
        weight, dextents<int32_t, 2>((int)input_dim,
                                     (int)args.output_dim * 2));
    constexpr auto descriptor = matmul2d_descriptor(
        TILE, TILE, K_TILE, false, true, true,
        FULL_PRODUCT ? matmul2d_descriptor::mode::multiply :
                       matmul2d_descriptor::mode::multiply_accumulate);
    matmul2d<descriptor, execution_simdgroups<8>> mm;
    threadgroup bfloat gate_tile[TILE * TILE];
    {
        auto first_a = x.slice<TILE, K_TILE>(0, (int)row_start);
        auto first_b = w.slice<K_TILE, TILE>(0, (int)column_start);
        auto accum = mm.template get_destination_cooperative_tensor<
            decltype(first_a), decltype(first_b), int32_t>();
        if constexpr (!FULL_PRODUCT) {
            #pragma clang loop unroll(full)
            for (ushort element = 0; element < accum.get_capacity(); element++)
                if (accum.is_valid_element(element)) accum[element] = 0;
        }
        if (INPUT_DIM) {
            for (uint k = 0; k < INPUT_DIM; k += K_TILE) {
                auto a = x.slice<TILE, K_TILE>((int)k, (int)row_start);
                auto b = w.slice<K_TILE, TILE>((int)k, (int)column_start);
                mm.run(a, b, accum);
            }
        } else {
            for (uint k = 0; k < input_dim; k += K_TILE) {
                auto a = x.slice<TILE, K_TILE>((int)k, (int)row_start);
                auto b = w.slice<K_TILE, TILE>((int)k, (int)column_start);
                mm.run(a, b, accum);
            }
        }
        #pragma clang loop unroll(full)
        for (ushort element = 0; element < accum.get_capacity(); element++) {
            if (!accum.is_valid_element(element)) continue;
            auto index = accum.get_multidimensional_index(element);
            uint row = row_start + (uint)index[1];
            uint column = column_start + (uint)index[0];
            float value = (float)accum[element] * input_scales[row] *
                          weight_scales[column];
            gate_tile[(uint)index[1] * TILE + (uint)index[0]] =
                (bfloat)value;
        }
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
    {
        auto first_a = x.slice<TILE, K_TILE>(0, (int)row_start);
        auto first_b = w.slice<K_TILE, TILE>(
            0, (int)args.output_dim + (int)column_start);
        auto accum = mm.template get_destination_cooperative_tensor<
            decltype(first_a), decltype(first_b), int32_t>();
        if constexpr (!FULL_PRODUCT) {
            #pragma clang loop unroll(full)
            for (ushort element = 0; element < accum.get_capacity(); element++)
                if (accum.is_valid_element(element)) accum[element] = 0;
        }
        if (INPUT_DIM) {
            for (uint k = 0; k < INPUT_DIM; k += K_TILE) {
                auto a = x.slice<TILE, K_TILE>((int)k, (int)row_start);
                auto b = w.slice<K_TILE, TILE>(
                    (int)k, (int)args.output_dim + (int)column_start);
                mm.run(a, b, accum);
            }
        } else {
            for (uint k = 0; k < input_dim; k += K_TILE) {
                auto a = x.slice<TILE, K_TILE>((int)k, (int)row_start);
                auto b = w.slice<K_TILE, TILE>(
                    (int)k, (int)args.output_dim + (int)column_start);
                mm.run(a, b, accum);
            }
        }
        #pragma clang loop unroll(full)
        for (ushort element = 0; element < accum.get_capacity(); element++) {
            if (!accum.is_valid_element(element)) continue;
            auto index = accum.get_multidimensional_index(element);
            uint local = (uint)index[1] * TILE + (uint)index[0];
            uint row = row_start + (uint)index[1];
            uint column = column_start + (uint)index[0];
            if (row >= args.rows) continue;
            float gate = (float)gate_tile[local];
            float up = (float)accum[element] * input_scales[row] *
                       weight_scales[args.output_dim + column];
            output[row * args.output_dim + column] =
                (bfloat)(gate / (1.0f + exp(-gate)) * up);
        }
    }
}

kernel void h3_linear_int8_grouped_local_nax_r128x64(
                           device int8_t *input [[buffer(0)]],
                           device int8_t *weight [[buffer(1)]],
                           device const float *input_scales [[buffer(2)]],
                           device const float *weight_scales [[buffer(3)]],
                           device bfloat *output [[buffer(4)]],
                           constant linear_args &args [[buffer(5)]],
                           uint code [[threadgroup_position_in_grid]],
                           ushort tid [[thread_index_in_threadgroup]]) {
    constexpr uint ROW_TILE = 128;
    constexpr uint COLUMN_TILE = 64;
    constexpr uint K_TILE = 512;
    constexpr uint SCALE_GROUP = 1024;
    constexpr uint K_TILES_PER_GROUP = SCALE_GROUP / K_TILE;
    constexpr uint SCALE_GROUPS = 14;
    constexpr uint FRAGMENT_CAPACITY = 64;
    uint padded_rows = (args.rows + ROW_TILE - 1) & ~(ROW_TILE - 1);
    uint row_tiles = padded_rows / ROW_TILE;
    uint column_tiles = args.output_dim / COLUMN_TILE;
    uint2 group = h3_morton_decode_compact(
        code, row_tiles, column_tiles);
    uint row_start = group.x * ROW_TILE;
    uint column_start = group.y * COLUMN_TILE;
    uint scale_groups = args.input_dim / SCALE_GROUP;
    threadgroup float local_input_scales[ROW_TILE * SCALE_GROUPS];
    threadgroup float local_weight_scales[COLUMN_TILE];
    for (uint local = tid; local < ROW_TILE * SCALE_GROUPS; local += 256) {
        uint row = row_start + local / SCALE_GROUPS;
        uint scale_group = local % SCALE_GROUPS;
        local_input_scales[local] =
            input_scales[row * SCALE_GROUPS + scale_group];
    }
    if (tid < COLUMN_TILE)
        local_weight_scales[tid] = weight_scales[column_start + tid];
    auto x = tensor<device int8_t, dextents<int32_t, 2>, tensor_inline>(
        input, dextents<int32_t, 2>((int)args.input_dim,
                                    (int)padded_rows));
    auto w = tensor<device int8_t, dextents<int32_t, 2>, tensor_inline>(
        weight, dextents<int32_t, 2>((int)args.input_dim,
                                     (int)args.output_dim));
    constexpr auto descriptor = matmul2d_descriptor(
        ROW_TILE, COLUMN_TILE, K_TILE, false, true, true,
        matmul2d_descriptor::mode::multiply_accumulate);
    constexpr auto first_descriptor = matmul2d_descriptor(
        ROW_TILE, COLUMN_TILE, K_TILE, false, true, true,
        matmul2d_descriptor::mode::multiply);
    matmul2d<descriptor, execution_simdgroups<8>> mm;
    matmul2d<first_descriptor, execution_simdgroups<8>> first_mm;
    thread float totals[FRAGMENT_CAPACITY];
    for (uint scale_group = 0; scale_group < scale_groups;
         scale_group += 2) {
        uint first_k = scale_group * SCALE_GROUP;
        uint second_k = first_k + SCALE_GROUP;
        auto first_a = x.slice<ROW_TILE, K_TILE>(
            (int)first_k, (int)row_start);
        auto first_b = w.slice<K_TILE, COLUMN_TILE>(
            (int)first_k, (int)column_start);
        auto first_accum = mm.template get_destination_cooperative_tensor<
            decltype(first_a), decltype(first_b), int32_t>();
        first_mm.run(first_a, first_b, first_accum);
        #pragma clang loop unroll(full)
        for (uint k_tile = 1; k_tile < K_TILES_PER_GROUP; k_tile++) {
            uint k = first_k + k_tile * K_TILE;
            auto a = x.slice<ROW_TILE, K_TILE>((int)k, (int)row_start);
            auto b = w.slice<K_TILE, COLUMN_TILE>(
                (int)k, (int)column_start);
            mm.run(a, b, first_accum);
        }
        auto second_a = x.slice<ROW_TILE, K_TILE>(
            (int)second_k, (int)row_start);
        auto second_b = w.slice<K_TILE, COLUMN_TILE>(
            (int)second_k, (int)column_start);
        auto second_accum = mm.template get_destination_cooperative_tensor<
            decltype(second_a), decltype(second_b), int32_t>();
        first_mm.run(second_a, second_b, second_accum);
        #pragma clang loop unroll(full)
        for (uint k_tile = 1; k_tile < K_TILES_PER_GROUP; k_tile++) {
            uint k = second_k + k_tile * K_TILE;
            auto a = x.slice<ROW_TILE, K_TILE>((int)k, (int)row_start);
            auto b = w.slice<K_TILE, COLUMN_TILE>(
                (int)k, (int)column_start);
            mm.run(a, b, second_accum);
        }
        if (scale_group == 0)
            threadgroup_barrier(mem_flags::mem_threadgroup);
        #pragma clang loop unroll(full)
        for (ushort element = 0; element < first_accum.get_capacity();
             element++) {
            if (!first_accum.is_valid_element(element)) continue;
            auto index = first_accum.get_multidimensional_index(element);
            float value = (float)first_accum[element] *
                local_input_scales[(uint)index[1] * SCALE_GROUPS +
                                   scale_group] *
                local_weight_scales[(uint)index[0]];
            if (scale_group == 0) totals[element] = value;
            else totals[element] += value;
        }
        #pragma clang loop unroll(full)
        for (ushort element = 0; element < second_accum.get_capacity();
             element++) {
            if (!second_accum.is_valid_element(element)) continue;
            auto index = second_accum.get_multidimensional_index(element);
            uint row = row_start + (uint)index[1];
            uint column = column_start + (uint)index[0];
            float value = (float)second_accum[element] *
                local_input_scales[(uint)index[1] * SCALE_GROUPS +
                                   scale_group + 1] *
                local_weight_scales[(uint)index[0]];
            totals[element] += value;
            if (scale_group + 2 == scale_groups && row < args.rows)
                output[row * args.output_dim + column] =
                    (bfloat)totals[element];
        }
    }
}
