#!/usr/bin/env python

from setuptools import setup

setup(
    name="fnargc",
    version="dev",
    description="Count C/C++ functions and their args.",
    packages=["fnargc"],
    install_requires=[
        "libclang==16.0.0",
    ],
    entry_points={
        "console_scripts": [
            "fnargc=fnargc.fnargc:main",
        ]
    },
)
