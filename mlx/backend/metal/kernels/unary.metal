// Copyright © 2024 Apple Inc.

// clang-format off
#include "mlx/backend/metal/kernels/utils.h"
#include "mlx/backend/metal/kernels/unary_ops.h"
#include "mlx/backend/metal/kernels/unary.h"

#define instantiate_unary_work_per_thread(op, in_tname, out_tname, in_type, out_type) \
  instantiate_kernel("vn_" #op #in_tname #out_tname, unary_v, in_type, out_type, op)

#define instantiate_unary_base(op, in_tname, out_tname, in_type, out_type)             \
  instantiate_kernel("v_" #op #in_tname #out_tname, unary_v, in_type, out_type, op, 1) \
  instantiate_kernel("v2_" #op #in_tname #out_tname, unary_v2, in_type, out_type, op)  \
  instantiate_kernel(                                                                  \
      "gn1_" #op #in_tname #out_tname, unary_g, in_type, out_type, op, 1, int)         \
  instantiate_kernel(                                                                  \
      "gn4large_" #op #in_tname #out_tname, unary_g, in_type, out_type, op, 4)

#define instantiate_unary_all(op, in_tname, out_tname, in_type, out_type)       \
  instantiate_unary_base(op, in_tname, out_tname, in_type, out_type)            \
  instantiate_unary_work_per_thread(op, in_tname, out_tname, in_type, out_type)

#define instantiate_unary_all_same(op, tname, type)   \
  instantiate_unary_all(op, tname, tname, type, type)

#define instantiate_unary_base_same(op, tname, type)   \
  instantiate_unary_base(op, tname, tname, type, type)

#define instantiate_unary_float(op)                    \
  instantiate_unary_all_same(op, float16, half)        \
  instantiate_unary_all_same(op, float32, float)       \
  instantiate_unary_all_same(op, bfloat16, bfloat16_t)

#define instantiate_unary_int(op)                   \
  instantiate_unary_all_same(op, uint8, uint8_t)    \
  instantiate_unary_all_same(op, uint16, uint16_t)  \
  instantiate_unary_all_same(op, uint32, uint32_t)  \
  instantiate_unary_base_same(op, uint64, uint64_t) \
  instantiate_unary_all_same(op, int8, int8_t)      \
  instantiate_unary_all_same(op, int16, int16_t)    \
  instantiate_unary_all_same(op, int32, int32_t)    \
  instantiate_unary_base_same(op, int64, int64_t)

#define instantiate_unary_types(op)                \
  instantiate_unary_all_same(op, bool_, bool)      \
  instantiate_unary_int(op)                        \
  instantiate_unary_float(op)

instantiate_unary_types(Abs)
instantiate_unary_float(ArcCos)
instantiate_unary_float(ArcCosh)
instantiate_unary_float(ArcSin)
instantiate_unary_float(ArcSinh)
instantiate_unary_float(ArcTan)
instantiate_unary_float(ArcTanh)
instantiate_unary_types(Ceil)
instantiate_unary_float(Cos)
instantiate_unary_float(Cosh)
instantiate_unary_float(Exp)
instantiate_unary_float(Expm1)
instantiate_unary_types(Floor)
instantiate_unary_float(Log)
instantiate_unary_float(Log2)
instantiate_unary_float(Log10)
instantiate_unary_float(Log1p)
instantiate_unary_types(Negative)
instantiate_unary_float(Sigmoid)
instantiate_unary_float(Erf)
instantiate_unary_float(ErfInv)
instantiate_unary_types(Sign)
instantiate_unary_float(Sin)
instantiate_unary_float(Sinh)
instantiate_unary_types(Square)
instantiate_unary_float(Sqrt)
instantiate_unary_float(Rsqrt)
instantiate_unary_float(Tan)
instantiate_unary_float(Tanh)
instantiate_unary_float(Round)
instantiate_unary_int(BitwiseInvert)

instantiate_unary_base_same(Abs, complex64, complex64_t)
instantiate_unary_base_same(ArcCos, complex64, complex64_t)
instantiate_unary_base_same(ArcSin, complex64, complex64_t)
instantiate_unary_base_same(ArcTan, complex64, complex64_t)
instantiate_unary_base_same(Conjugate, complex64, complex64_t)
instantiate_unary_base_same(Cos, complex64, complex64_t)
instantiate_unary_base_same(Cosh, complex64, complex64_t)
instantiate_unary_base_same(Exp, complex64, complex64_t)
instantiate_unary_base_same(Log, complex64, complex64_t)
instantiate_unary_base_same(Log1p, complex64, complex64_t)
instantiate_unary_base_same(Log2, complex64, complex64_t)
instantiate_unary_base_same(Log10, complex64, complex64_t)
instantiate_unary_base_same(Negative, complex64, complex64_t)
instantiate_unary_base_same(Sign, complex64, complex64_t)
instantiate_unary_base_same(Sin, complex64, complex64_t)
instantiate_unary_base_same(Sinh, complex64, complex64_t)
instantiate_unary_base_same(Square, complex64, complex64_t)
instantiate_unary_base_same(Sqrt, complex64, complex64_t)
instantiate_unary_base_same(Rsqrt, complex64, complex64_t)
instantiate_unary_base_same(Tan, complex64, complex64_t)
instantiate_unary_base_same(Tanh, complex64, complex64_t)
instantiate_unary_base_same(Round, complex64, complex64_t)
instantiate_unary_base(Real, complex64, float32, complex64_t, float)
instantiate_unary_base(Imag, complex64, float32, complex64_t, float)

instantiate_unary_all_same(LogicalNot, bool_, bool) // clang-format on
