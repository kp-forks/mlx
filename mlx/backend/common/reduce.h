// Copyright © 2023 Apple Inc.

#pragma once

#include "mlx/backend/common/simd/simd.h"
#include "mlx/backend/common/utils.h"

namespace mlx::core {

enum ReductionOpType {
  // Self-explanatory. Read everything and produce 1 output.
  ContiguousAllReduce,

  // The input is contiguous and the last axis is reduced
  // N1xR1xN2xR2x...xNnxRn
  ContiguousReduce,

  // The input is contiguous and the last axis is not reduced
  // R1xN1xR2xN2x...xRnxNn
  ContiguousStridedReduce,

  // The input is not contiguous but the last axis is and it is reduced so we
  // need to figure out the offsets but we can call the contiguous reduce after
  // that.
  // N3xR1xN1xR4x...xRn
  GeneralContiguousReduce,

  // The input is not contiguous but the last reduction axis and the last axis
  // are so we need to figure out the offset but we can call the strided reduce
  // after that.
  GeneralStridedReduce,

  // The input is not contiguous after the reduction axis and it may contain
  // 0-stride axes or transpositions. We could copy the strides and produce a
  // transposed outcome or we can read the input out of order and write the
  // output in order.
  GeneralReduce
};

struct ReductionPlan {
  ReductionOpType type;
  Shape shape;
  Strides strides;

  ReductionPlan(ReductionOpType type_, Shape shape_, Strides strides_)
      : type(type_), shape(std::move(shape_)), strides(std::move(strides_)) {}
  ReductionPlan(ReductionOpType type_) : type(type_) {}
};

ReductionPlan get_reduction_plan(const array& x, const std::vector<int>& axes);

// Helper for the ndimensional strided loop
// Should this be in utils?
void nd_loop(
    std::function<void(int)> callback,
    const Shape& shape,
    const Strides& strides);

std::pair<Shape, Strides> shapes_without_reduction_axes(
    const array& x,
    const std::vector<int>& axes);

template <typename T, typename U, typename Op>
void strided_reduce(
    const T* x,
    U* accumulator,
    int size,
    size_t stride,
    Op op) {
  constexpr int N = std::min(simd::max_size<T>, simd::max_size<U>);
  for (int i = 0; i < size; i++) {
    U* moving_accumulator = accumulator;
    auto s = stride;
    while (s >= N) {
      auto acc = simd::load<U, N>(moving_accumulator);
      auto v = simd::Simd<U, N>(simd::load<T, N>(x));
      simd::store<U, N>(moving_accumulator, op(acc, v));
      moving_accumulator += N;
      x += N;
      s -= N;
    }
    while (s-- > 0) {
      *moving_accumulator = op(*moving_accumulator, *x);
      moving_accumulator++;
      x++;
    }
  }
};

template <typename T, typename U, typename Op>
void contiguous_reduce(const T* x, U* accumulator, int size, Op op, U init) {
  constexpr int N = std::min(simd::max_size<T>, simd::max_size<U>);
  simd::Simd<U, N> accumulator_v(init);
  while (size >= N) {
    accumulator_v = op(accumulator_v, simd::Simd<U, N>(simd::load<T, N>(x)));
    x += N;
    size -= N;
  }
  *accumulator = op(*accumulator, op(accumulator_v));
  while (size-- > 0) {
    *accumulator = op(*accumulator, *x);
    x++;
  }
}

template <typename T, typename U, typename Op>
void reduction_op(
    const array& x,
    array& out,
    const std::vector<int>& axes,
    U init,
    Op op) {
  out.set_data(allocator::malloc_or_wait(out.nbytes()));
  ReductionPlan plan = get_reduction_plan(x, axes);

  if (plan.type == ContiguousAllReduce) {
    U* out_ptr = out.data<U>();
    *out_ptr = init;
    contiguous_reduce(x.data<T>(), out_ptr, x.size(), op, init);
    return;
  }

  if (plan.type == ContiguousReduce && plan.shape.size() == 1) {
    int reduction_size = plan.shape[0];
    const T* x_ptr = x.data<T>();
    U* out_ptr = out.data<U>();
    for (int i = 0; i < out.size(); i++, out_ptr++, x_ptr += reduction_size) {
      *out_ptr = init;
      contiguous_reduce(x_ptr, out_ptr, reduction_size, op, init);
    }
    return;
  }

  if (plan.type == GeneralContiguousReduce || plan.type == ContiguousReduce) {
    int reduction_size = plan.shape.back();
    plan.shape.pop_back();
    plan.strides.pop_back();
    const T* x_ptr = x.data<T>();
    U* out_ptr = out.data<U>();
    // Unrolling the following loop (and implementing it in order for
    // ContiguousReduce) should hold extra performance boost.
    auto [shape, strides] = shapes_without_reduction_axes(x, axes);
    if (plan.shape.size() == 0) {
      for (int i = 0; i < out.size(); i++, out_ptr++) {
        int offset = elem_to_loc(i, shape, strides);
        *out_ptr = init;
        contiguous_reduce(x_ptr + offset, out_ptr, reduction_size, op, init);
      }
    } else {
      for (int i = 0; i < out.size(); i++, out_ptr++) {
        int offset = elem_to_loc(i, shape, strides);
        *out_ptr = init;
        nd_loop(
            [&](int extra_offset) {
              contiguous_reduce(
                  x_ptr + offset + extra_offset,
                  out_ptr,
                  reduction_size,
                  op,
                  init);
            },
            plan.shape,
            plan.strides);
      }
    }
    return;
  }

  if (plan.type == ContiguousStridedReduce && plan.shape.size() == 1) {
    int reduction_size = plan.shape.back();
    size_t reduction_stride = plan.strides.back();
    plan.shape.pop_back();
    plan.strides.pop_back();
    const T* x_ptr = x.data<T>();
    U* out_ptr = out.data<U>();
    for (int i = 0; i < out.size(); i += reduction_stride) {
      std::fill_n(out_ptr, reduction_stride, init);
      strided_reduce(x_ptr, out_ptr, reduction_size, reduction_stride, op);
      x_ptr += reduction_stride * reduction_size;
      out_ptr += reduction_stride;
    }
    return;
  }

  if (plan.type == GeneralStridedReduce ||
      plan.type == ContiguousStridedReduce) {
    int reduction_size = plan.shape.back();
    size_t reduction_stride = plan.strides.back();
    plan.shape.pop_back();
    plan.strides.pop_back();
    const T* x_ptr = x.data<T>();
    U* out_ptr = out.data<U>();
    auto [shape, strides] = shapes_without_reduction_axes(x, axes);
    if (plan.shape.size() == 0) {
      for (int i = 0; i < out.size(); i += reduction_stride) {
        int offset = elem_to_loc(i, shape, strides);
        std::fill_n(out_ptr, reduction_stride, init);
        strided_reduce(
            x_ptr + offset, out_ptr, reduction_size, reduction_stride, op);
        out_ptr += reduction_stride;
      }
    } else {
      for (int i = 0; i < out.size(); i += reduction_stride) {
        int offset = elem_to_loc(i, shape, strides);
        std::fill_n(out_ptr, reduction_stride, init);
        nd_loop(
            [&](int extra_offset) {
              strided_reduce(
                  x_ptr + offset + extra_offset,
                  out_ptr,
                  reduction_size,
                  reduction_stride,
                  op);
            },
            plan.shape,
            plan.strides);
        out_ptr += reduction_stride;
      }
    }
    return;
  }

  if (plan.type == GeneralReduce) {
    const T* x_ptr = x.data<T>();
    U* out_ptr = out.data<U>();
    auto [shape, strides] = shapes_without_reduction_axes(x, axes);
    for (int i = 0; i < out.size(); i++, out_ptr++) {
      int offset = elem_to_loc(i, shape, strides);
      U val = init;
      nd_loop(
          [&](int extra_offset) {
            val = op(val, *(x_ptr + offset + extra_offset));
          },
          plan.shape,
          plan.strides);
      *out_ptr = val;
    }
  }
}

} // namespace mlx::core
