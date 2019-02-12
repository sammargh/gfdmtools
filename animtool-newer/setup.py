from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize(
        [
            "imageops.pyx",
        ],
        annotate=True)
)