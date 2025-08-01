# Copyright © 2024 Apple Inc.

import gc
import os
import tempfile
import unittest

import mlx.core as mx
import mlx.nn as nn
import mlx_tests


class TestExportImport(mlx_tests.MLXTestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_dir_fid = tempfile.TemporaryDirectory()
        cls.test_dir = cls.test_dir_fid.name
        if not os.path.isdir(cls.test_dir):
            os.mkdir(cls.test_dir)

    @classmethod
    def tearDownClass(cls):
        cls.test_dir_fid.cleanup()

    def test_basic_export_import(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")

        # Function with no inputs
        def fun():
            return mx.zeros((3, 3))

        mx.export_function(path, fun)
        imported = mx.import_function(path)

        expected = fun()
        (out,) = imported()
        self.assertTrue(mx.array_equal(out, expected))

        # Simple function with inputs
        def fun(x):
            return mx.abs(mx.sin(x))

        inputs = mx.array([1.0, 2.0, 3.0, 4.0, 5.0])

        mx.export_function(path, fun, inputs)
        imported = mx.import_function(path)

        expected = fun(inputs)
        (out,) = imported(inputs)
        self.assertTrue(mx.allclose(out, expected))

        # Inputs in a list or tuple
        def fun(x):
            x = mx.abs(mx.sin(x))
            return x

        mx.export_function(path, fun, [inputs])
        imported = mx.import_function(path)

        expected = fun(inputs)
        (out,) = imported([inputs])
        self.assertTrue(mx.allclose(out, expected))

        (out,) = imported(inputs)
        self.assertTrue(mx.allclose(out, expected))

        mx.export_function(path, fun, (inputs,))
        imported = mx.import_function(path)
        (out,) = imported((inputs,))
        self.assertTrue(mx.allclose(out, expected))

        # Outputs in a list
        def fun(x):
            return [mx.abs(mx.sin(x))]

        mx.export_function(path, fun, inputs)
        imported = mx.import_function(path)
        (out,) = imported(inputs)
        self.assertTrue(mx.allclose(out, expected))

        # Outputs in a tuple
        def fun(x):
            return (mx.abs(mx.sin(x)),)

        mx.export_function(path, fun, inputs)
        imported = mx.import_function(path)
        (out,) = imported(inputs)
        self.assertTrue(mx.allclose(out, expected))

        # Check throws on invalid inputs / outputs
        def fun(x):
            return mx.abs(x)

        with self.assertRaises(ValueError):
            mx.export_function(path, fun, "hi")

        with self.assertRaises(ValueError):
            mx.export_function(path, fun, mx.array(1.0), "hi")

        def fun(x):
            return mx.abs(x[0][0])

        with self.assertRaises(ValueError):
            mx.export_function(path, fun, [[mx.array(1.0)]])

        def fun():
            return (mx.zeros((3, 3)), 1)

        with self.assertRaises(ValueError):
            mx.export_function(path, fun)

        def fun():
            return (mx.zeros((3, 3)), [mx.zeros((3, 3))])

        with self.assertRaises(ValueError):
            mx.export_function(path, fun)

        def fun(x, y):
            return x + y

        mx.export_function(path, fun, mx.array(1.0), mx.array(1.0))
        imported = mx.import_function(path)

        with self.assertRaises(ValueError):
            imported(mx.array(1.0), 1.0)

        with self.assertRaises(ValueError):
            imported(mx.array(1.0), mx.array(1.0), mx.array(1.0))

        with self.assertRaises(ValueError):
            imported(mx.array(1.0), [mx.array(1.0)])

    def test_export_random_sample(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")

        mx.random.seed(5)

        def fun():
            return mx.random.uniform(shape=(3,))

        mx.export_function(path, fun)
        imported = mx.import_function(path)

        (out,) = imported()

        mx.random.seed(5)
        expected = fun()

        self.assertTrue(mx.array_equal(out, expected))

    def test_export_with_kwargs(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")

        def fun(x, z=None):
            out = x
            if z is not None:
                out += z
            return out

        x = mx.array([1, 2, 3])
        y = mx.array([1, 1, 0])
        z = mx.array([2, 2, 2])

        mx.export_function(path, fun, (x,), {"z": z})
        imported_fun = mx.import_function(path)

        with self.assertRaises(ValueError):
            imported_fun(x, z)

        with self.assertRaises(ValueError):
            imported_fun(x, y=z)

        with self.assertRaises(ValueError):
            imported_fun((x,), {"y": z})

        out = imported_fun(x, z=z)[0]
        self.assertTrue(mx.array_equal(out, mx.array([3, 4, 5])))

        out = imported_fun((x,), {"z": z})[0]
        self.assertTrue(mx.array_equal(out, mx.array([3, 4, 5])))

        mx.export_function(path, fun, x, z=z)
        imported_fun = mx.import_function(path)
        out = imported_fun(x, z=z)[0]
        self.assertTrue(mx.array_equal(out, mx.array([3, 4, 5])))

        out = imported_fun((x,), {"z": z})[0]
        self.assertTrue(mx.array_equal(out, mx.array([3, 4, 5])))

        # Only specify kwargs
        mx.export_function(path, fun, x=x, z=z)
        imported_fun = mx.import_function(path)
        with self.assertRaises(ValueError):
            out = imported_fun(x, z=z)[0]

        out = imported_fun(x=x, z=z)[0]
        self.assertTrue(mx.array_equal(out, mx.array([3, 4, 5])))

        out = imported_fun({"x": x, "z": z})[0]
        self.assertTrue(mx.array_equal(out, mx.array([3, 4, 5])))

    def test_export_variable_inputs(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")

        def fun(x, y, z=None):
            out = x + y
            if z is not None:
                out += z
            return out

        with mx.exporter(path, fun) as exporter:
            exporter(mx.array([1, 2, 3]), mx.array([1, 1, 1]))
            exporter(mx.array([1, 2, 3]), mx.array([1, 1, 1]), z=mx.array([2]))

        with self.assertRaises(RuntimeError):
            exporter(mx.array([1, 2, 3, 4]), mx.array([1, 1, 1, 1]))

        imported_fun = mx.import_function(path)
        out = imported_fun(mx.array([1, 2, 3]), mx.array([1, 1, 1]))[0]
        self.assertTrue(mx.array_equal(out, mx.array([2, 3, 4])))

        out = imported_fun(mx.array([1, 2, 3]), mx.array([1, 1, 1]), z=mx.array([2]))[0]
        self.assertTrue(mx.array_equal(out, mx.array([4, 5, 6])))

        with self.assertRaises(ValueError):
            imported_fun(mx.array([1, 2, 3, 4]), mx.array([1, 1, 1, 1]))

        # A function with a large constant
        constant = mx.zeros((16, 2048))
        mx.eval(constant)

        def fun(*args):
            return constant + sum(args)

        with mx.exporter(path, fun) as exporter:
            for i in range(5):
                exporter(*[mx.array(1)] * i)

        # Check the exported file size < constant size + small amount
        constants_size = constant.nbytes + 8192
        self.assertTrue(os.path.getsize(path) < constants_size)

    def test_leaks(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")
        mx.synchronize()
        if mx.metal.is_available():
            mem_pre = mx.get_active_memory()
        else:
            mem_pre = 0

        def outer():
            d = {}

            def f(x):
                return d["x"]

            d["f"] = mx.exporter(path, f)
            d["x"] = mx.array([0] * 1000)

        for _ in range(5):
            outer()
            gc.collect()

        if mx.metal.is_available():
            mem_post = mx.get_active_memory()
        else:
            mem_post = 0

        self.assertEqual(mem_pre, mem_post)

    def test_export_import_shapeless(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")

        def fun(*args):
            return sum(args)

        with mx.exporter(path, fun, shapeless=True) as exporter:
            exporter(mx.array(1))
            exporter(mx.array(1), mx.array(2))
            exporter(mx.array(1), mx.array(2), mx.array(3))

        f2 = mx.import_function(path)
        self.assertEqual(f2(mx.array(1))[0].item(), 1)
        self.assertEqual(f2(mx.array(1), mx.array(1))[0].item(), 2)
        self.assertEqual(f2(mx.array(1), mx.array(1), mx.array(1))[0].item(), 3)
        with self.assertRaises(ValueError):
            f2(mx.array(10), mx.array([5, 10, 20]))

    def test_export_scatter_gather(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")

        def fun(a, b):
            return mx.take_along_axis(a, b, axis=0)

        x = mx.random.uniform(shape=(4, 4))
        y = mx.array([[0, 1, 2, 3], [1, 2, 0, 3]])
        mx.export_function(path, fun, (x, y))
        imported_fun = mx.import_function(path)
        expected = fun(x, y)
        out = imported_fun(x, y)[0]
        self.assertTrue(mx.array_equal(expected, out))

        def fun(a, b, c):
            return mx.put_along_axis(a, b, c, axis=0)

        x = mx.random.uniform(shape=(4, 4))
        y = mx.array([[0, 1, 2, 3], [1, 2, 0, 3]])
        z = mx.random.uniform(shape=(2, 4))
        mx.export_function(path, fun, (x, y, z))
        imported_fun = mx.import_function(path)
        expected = fun(x, y, z)
        out = imported_fun(x, y, z)[0]
        self.assertTrue(mx.array_equal(expected, out))

    def test_export_conv(self):
        path = os.path.join(self.test_dir, "fn.mlxfn")

        class Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.c1 = nn.Conv2d(
                    3, 16, kernel_size=3, stride=1, padding=1, bias=False
                )
                self.c2 = nn.Conv2d(
                    16, 16, kernel_size=3, stride=2, padding=1, bias=False
                )
                self.c3 = nn.Conv2d(
                    16, 16, kernel_size=3, stride=1, padding=2, bias=False
                )

            def __call__(self, x):
                return self.c3(self.c2(self.c1(x)))

        model = Model()
        mx.eval(model.parameters())

        def forward(x):
            return model(x)

        input_data = mx.random.normal(shape=(4, 32, 32, 3))
        mx.export_function(path, forward, input_data)

        imported_fn = mx.import_function(path)
        out = imported_fn(input_data)[0]
        expected = forward(input_data)
        self.assertTrue(mx.allclose(expected, out))

    def test_export_control_flow(self):

        def fun(x, y):
            if y.shape[0] <= 2:
                return x + y
            else:
                return x + 2 * y

        for y in (mx.array([1, 2, 3]), mx.array([1, 2])):
            for shapeless in (True, False):
                with self.subTest(y=y, shapeless=shapeless):
                    x = mx.array(1)
                    export_path = os.path.join(self.test_dir, "control_flow.mlxfn")
                    mx.export_function(export_path, fun, x, y, shapeless=shapeless)

                    imported_fn = mx.import_function(export_path)
                    self.assertTrue(mx.array_equal(imported_fn(x, y)[0], fun(x, y)))

    def test_export_quantized_model(self):
        for shapeless in (True, False):
            with self.subTest(shapeless=shapeless):
                model = nn.Sequential(
                    nn.Linear(1024, 512), nn.ReLU(), nn.Linear(512, 1024)
                )
                model.eval()
                mx.eval(model.parameters())
                input_data = mx.ones(shape=(512, 1024))
                nn.quantize(model)
                self.assertTrue(isinstance(model.layers[0], nn.QuantizedLinear))
                self.assertTrue(isinstance(model.layers[2], nn.QuantizedLinear))
                mx.eval(model.parameters())

                export_path = os.path.join(self.test_dir, "quantized_linear.mlxfn")
                mx.export_function(export_path, model, input_data, shapeless=shapeless)

                imported_fn = mx.import_function(export_path)
                self.assertTrue(
                    mx.array_equal(imported_fn(input_data)[0], model(input_data))
                )


if __name__ == "__main__":
    mlx_tests.MLXTestRunner()
