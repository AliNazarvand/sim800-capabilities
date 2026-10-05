"""Generate a C++ header from the capability database."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .generate import generate as _generate_doc


_FAMILIES = ("SIM800", "SIM808", "SIM868")

_STATUSES = (
    "documented",
    "not_documented",
    "not_supported",
    "inferred",
    "conflict",
    "not_in_scope",
)


def _status_cpp(status: Any) -> str:
    s = str(status) if status is not None else "not_documented"
    if s not in _STATUSES:
        s = "not_documented"
    return "Status::" + s


def _family_cpp(family: Any) -> str:
    f = str(family) if family is not None else "SIM800"
    if f not in _FAMILIES:
        f = "SIM800"
    return "Family::" + f


def _str_cpp(s: Any) -> str:
    if s is None:
        return '""'
    text = str(s)
    text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"' + text + '"'


def _int_or(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return int(v)
    return default


def _bool_or_false(v: Any) -> bool:
    return bool(v) if v is not None else False


def _volts_to_mv(v: Any) -> int:
    if v is None:
        return 0
    try:
        return int(round(float(v) * 1000.0))
    except (TypeError, ValueError):
        return 0


def _node(d: Any, key: str) -> Dict[str, Any]:
    if isinstance(d, dict):
        n = d.get(key)
        if isinstance(n, dict):
            return n
    return {}


def _val(node: Any) -> Any:
    if isinstance(node, dict):
        return node.get("value")
    return None


def _sta(node: Any) -> str:
    if isinstance(node, dict):
        return _status_cpp(node.get("status"))
    return "Status::not_documented"


def _bool_field(node: Any) -> str:
    b = "true" if _bool_or_false(_val(node)) else "false"
    return "{" + b + ", " + _sta(node) + "}"


def _int_field(node: Any) -> str:
    return "{" + str(_int_or(_val(node))) + ", " + _sta(node) + "}"


def _str_field(node: Any) -> str:
    return "{" + _str_cpp(_val(node)) + ", " + _sta(node) + "}"


def _band_list(node: Any) -> str:
    v = _val(node)
    items: List[int] = []
    if isinstance(v, list):
        for x in v:
            try:
                items.append(int(x))
            except (TypeError, ValueError):
                pass
    count = len(items)
    if count < 4:
        padded = items + [0] * (4 - count)
    else:
        padded = items[:4]
    vals = ", ".join(str(x) for x in padded)
    return "{{" + vals + "}, " + str(count) + ", " + _sta(node) + "}"


def _render_model(model: Dict[str, Any]) -> str:
    caps = model.get("capabilities") or {}
    name = model.get("model", "")
    family = model.get("family", "SIM800")

    bands = _node(caps, "bands")
    bluetooth = _node(caps, "bluetooth")
    pcm = _node(caps, "pcm")
    usb = _node(caps, "usb")
    gnss = _node(caps, "gnss")
    gpio = _node(caps, "gpio")
    adc = _node(caps, "adc")
    sim = _node(caps, "sim_interface")
    uart = _node(caps, "uart_serial")
    env = _node(caps, "environmental")
    power = _node(caps, "power")

    vmin = _node(power, "vbat_min_v")
    vmax = _node(power, "vbat_max_v")
    vbat_min_mv = _volts_to_mv(_val(vmin))
    vbat_max_mv = _volts_to_mv(_val(vmax))

    lines: List[str] = []
    lines.append("    Model{")
    lines.append("        " + _str_cpp(name) + ", " + _family_cpp(family) + ",")
    lines.append("        " + _band_list(_node(bands, "gsm")) + ",   // bands_gsm")
    lines.append("        " + _band_list(_node(bands, "gprs")) + ",  // bands_gprs")
    lines.append("        " + _str_field(_node(bands, "type")) + ",  // band_type")
    lines.append("        " + _bool_field(_node(bluetooth, "supported")) + ",  // bluetooth_supported")
    lines.append("        " + _str_field(_node(bluetooth, "version")) + ",    // bluetooth_version")
    lines.append("        " + _bool_field(_node(pcm, "supported")) + ",  // pcm_supported")
    lines.append("        " + _int_field(_node(pcm, "channels")) + ",    // pcm_channels")
    lines.append("        " + _str_field(_node(pcm, "mode")) + ",        // pcm_mode")
    lines.append("        " + _bool_field(_node(usb, "supported")) + ",  // usb_supported")
    lines.append("        " + _str_field(_node(usb, "version")) + ",     // usb_version")
    lines.append("        " + _str_field(_node(usb, "speed")) + ",       // usb_speed")
    lines.append("        " + _bool_field(_node(gnss, "supported")) + ", // gnss_supported")
    lines.append("        " + _int_field(_node(gnss, "channels")) + ",   // gnss_channels")
    lines.append("        " + _str_field(_node(gnss, "antenna_interface")) + ",  // gnss_antenna_interface")
    lines.append("        " + _int_field(_node(gpio, "count")) + ",      // gpio_count")
    lines.append("        " + _int_field(_node(adc, "count")) + ",       // adc_count")
    lines.append("        " + _int_field(_node(adc, "resolution_bits")) + ",  // adc_resolution_bits")
    lines.append("        " + _int_field(_node(sim, "count")) + ",       // sim_count")
    lines.append("        " + _int_field(_node(uart, "ports")) + ",      // uart_ports")
    lines.append("        " + _str_field(_node(uart, "flow_control")) + ",  // uart_flow_control")
    lines.append("        {" + str(vbat_min_mv) + ", " + _sta(vmin) + "},  // vbat_min_mv")
    lines.append("        {" + str(vbat_max_mv) + ", " + _sta(vmax) + "},  // vbat_max_mv")
    lines.append("        " + _int_field(_node(env, "operating_temperature_min_c")) + ",  // op_temp_min_c")
    lines.append("        " + _int_field(_node(env, "operating_temperature_max_c")) + ",  // op_temp_max_c")
    lines.append("    },")
    return "\n".join(lines) + "\n"


_HEADER = """\
// AUTO-GENERATED by sim800-capabilities. DO NOT EDIT BY HAND.
// Source: data/models/*.yaml
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

namespace sim800_capabilities {

enum class Family : std::uint8_t {
    SIM800 = 0,
    SIM808 = 1,
    SIM868 = 2,
};

enum class Status : std::uint8_t {
    documented = 0,
    not_documented = 1,
    not_supported = 2,
    inferred = 3,
    conflict = 4,
    not_in_scope = 5,
};

struct BandList {
    std::array<std::uint16_t, 4> values;
    std::uint8_t count;
    Status status;
};

struct FieldBool {
    bool value;
    Status status;
};

struct FieldInt {
    std::int32_t value;
    Status status;
};

struct FieldStr {
    std::string_view value;
    Status status;
};

struct Model {
    std::string_view name;
    Family family;
    BandList bands_gsm;
    BandList bands_gprs;
    FieldStr  band_type;
    FieldBool bluetooth_supported;
    FieldStr  bluetooth_version;
    FieldBool pcm_supported;
    FieldInt  pcm_channels;
    FieldStr  pcm_mode;
    FieldBool usb_supported;
    FieldStr  usb_version;
    FieldStr  usb_speed;
    FieldBool gnss_supported;
    FieldInt  gnss_channels;
    FieldStr  gnss_antenna_interface;
    FieldInt  gpio_count;
    FieldInt  adc_count;
    FieldInt  adc_resolution_bits;
    FieldInt  sim_count;
    FieldInt  uart_ports;
    FieldStr  uart_flow_control;
    FieldInt  vbat_min_mv;
    FieldInt  vbat_max_mv;
    FieldInt  operating_temperature_min_c;
    FieldInt  operating_temperature_max_c;
};

inline constexpr Model kModels[] = {
"""

_FOOTER = """\
};

inline constexpr std::size_t kModelCount = sizeof(kModels) / sizeof(kModels[0]);

}  // namespace sim800_capabilities
"""


def render_header(models: List[Dict[str, Any]]) -> str:
    body = "".join(_render_model(m) for m in models)
    return _HEADER + body + _FOOTER


def render_from_root(root: Path) -> str:
    doc = _generate_doc(Path(root))
    return render_header(doc["models"])


def write_cpp_header(root: Path, out_path: Path | None = None) -> Path:
    root = Path(root)
    doc = _generate_doc(root)
    text = render_header(doc["models"])
    if out_path is None:
        out_path = root / "include" / "sim800_capabilities.hpp"
    else:
        out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return out_path