#!/usr/bin/env python

from setuptools import setup

setup(
    name="fnargc",
    version="0.1.0",
    description="Count C/C++ functions and their args.",
    packages=["fnargc"],
    install_requires=[
        "libclang==16.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fnargc=fnargc.fnargc:main",
            "fnargc-stats=fnargc.stats:main",
        ]
    },
)
