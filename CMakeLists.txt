cmake_minimum_required(VERSION 3.16)

project(sim800-capabilities
    VERSION 0.1.0
    DESCRIPTION "Data-driven capability database for SIM800 family modules."
    LANGUAGES NONE)

# --- Python interpreter ---------------------------------------------------
find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)

set(SIM800_CAPABILITIES_ROOT "${CMAKE_CURRENT_SOURCE_DIR}"
    CACHE PATH "Repository root")
set(SIM800_CAPABILITIES_SRC "${SIM800_CAPABILITIES_ROOT}/src")

# --- CTest ----------------------------------------------------------------
enable_testing()
include(CTest)

add_test(
    NAME python_syntax
    COMMAND ${Python3_EXECUTABLE} -m compileall -q "${SIM800_CAPABILITIES_SRC}")

add_test(
    NAME pytest
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${SIM800_CAPABILITIES_SRC}"
            ${Python3_EXECUTABLE} -m pytest -q
    WORKING_DIRECTORY "${SIM800_CAPABILITIES_ROOT}")

add_test(
    NAME validate_data
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${SIM800_CAPABILITIES_SRC}"
            ${Python3_EXECUTABLE} -m sim800_capabilities.cli
            --root "${SIM800_CAPABILITIES_ROOT}" validate
    WORKING_DIRECTORY "${SIM800_CAPABILITIES_ROOT}")

add_test(
    NAME audit_smoke
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${SIM800_CAPABILITIES_SRC}"
            ${Python3_EXECUTABLE} -m sim800_capabilities.cli
            --root "${SIM800_CAPABILITIES_ROOT}" audit --format json
    WORKING_DIRECTORY "${SIM800_CAPABILITIES_ROOT}")

add_test(
    NAME generate_cpp
    COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${SIM800_CAPABILITIES_SRC}"
            ${Python3_EXECUTABLE} -m sim800_capabilities.cli
            --root "${SIM800_CAPABILITIES_ROOT}" generate
            --target cpp --out "${CMAKE_CURRENT_BINARY_DIR}/sim800_capabilities.hpp"
    WORKING_DIRECTORY "${SIM800_CAPABILITIES_ROOT}")
