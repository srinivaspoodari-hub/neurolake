"""
Setup script for building Cython extensions for NCF

Usage:
    python setup_cython.py build_ext --inplace
"""

from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

extensions = [
    Extension(
        "neurolake.ncf.format.serializers",
        ["neurolake/ncf/format/serializers.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=[
            "/O2",  # Maximum optimization (Windows)
            "/fp:fast",  # Fast floating point
        ] if __import__('sys').platform == 'win32' else [
            "-O3",  # Maximum optimization (Unix)
            "-march=native",  # Use CPU-specific optimizations
            "-ffast-math",  # Fast math
        ],
        define_macros=[
            ("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION"),
        ],
    )
]

setup(
    name="neurolake-ncf-cython",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'boundscheck': False,  # Disable bounds checking for speed
            'wraparound': False,   # Disable negative indexing
            'cdivision': True,     # Use C division (faster)
            'initializedcheck': False,  # Disable initialization checks
            'nonecheck': False,    # Disable None checks
        },
        annotate=True,  # Generate HTML annotation files
    ),
    zip_safe=False,
)
