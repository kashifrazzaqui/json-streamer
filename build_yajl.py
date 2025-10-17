#!/usr/bin/env python3
"""
Build script to compile yajl from source and bundle it with jsonstreamer.

This script is used during wheel building to compile yajl and include
the shared library in the wheel.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_yajl_lib_name():
    """Get the platform-specific library name for yajl."""
    system = platform.system()
    if system == "Darwin":
        return "libyajl.dylib"
    elif system == "Windows":
        return "yajl.dll"
    else:  # Linux and others
        return "libyajl.so.2"


def build_yajl():
    """
    Download, compile, and install yajl from source.

    Returns:
        Path to the compiled library file
    """
    print("=" * 60)
    print("Building yajl from source for bundling")
    print("=" * 60)

    # Create build directory
    build_dir = Path("build/yajl_build")
    build_dir.mkdir(parents=True, exist_ok=True)

    yajl_dir = build_dir / "yajl"

    # Clone yajl if not already there
    if not yajl_dir.exists():
        print("Cloning yajl repository...")
        subprocess.run(
            ["git", "clone", "https://github.com/lloyd/yajl.git", str(yajl_dir)],
            check=True,
        )

    # Build yajl
    print("Configuring yajl...")
    os.chdir(yajl_dir)

    if platform.system() == "Windows":
        # Windows build with cmake
        subprocess.run(["cmake", "."], check=True)
        subprocess.run(["cmake", "--build", ".", "--config", "Release"], check=True)
        lib_path = yajl_dir / "Release" / "yajl.dll"
    else:
        # Unix build with configure
        subprocess.run(["./configure"], check=True)
        subprocess.run(["make"], check=True)

        # Find the compiled library
        lib_name = get_yajl_lib_name()
        possible_paths = [
            yajl_dir / "build" / "yajl-2.1.0" / "lib" / lib_name,
            yajl_dir / "build" / "yajl-2.1.0" / "lib" / "libyajl.so",
            yajl_dir / "build" / "yajl-2.1.0" / "lib" / "libyajl.dylib",
        ]

        lib_path = None
        for path in possible_paths:
            if path.exists():
                lib_path = path
                break

        if not lib_path or not lib_path.exists():
            raise FileNotFoundError(f"Could not find compiled yajl library. Searched: {possible_paths}")

    print(f"✅ Built yajl at: {lib_path}")

    # Return to original directory
    os.chdir(Path(__file__).parent)

    # Copy to package directory
    package_dir = Path("jsonstreamer/yajl")
    package_dir.mkdir(parents=True, exist_ok=True)

    dest_path = package_dir / get_yajl_lib_name()
    shutil.copy2(lib_path, dest_path)
    print(f"✅ Copied library to: {dest_path}")

    return dest_path


if __name__ == "__main__":
    try:
        lib_path = build_yajl()
        print(f"\n✅ Success! yajl library ready at: {lib_path}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error building yajl: {e}", file=sys.stderr)
        sys.exit(1)
