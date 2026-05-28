"""Shared helpers for dataset migration, validation, and pipeline loading."""

from __future__ import annotations

import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    lowered = re.sub(r"[^a-zA-Z0-9]+", "_", (value or "").strip().lower())
    return lowered.strip("_") or "item"


def normalize_signal_name(value: str) -> str:
    return slugify(value)


def summarize_requirement_payload(payload: Dict[str, Any]) -> str:
    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    scenario = payload.get("scenario") if isinstance(payload.get("scenario"), dict) else {}
    criteria = payload.get("acceptance_criteria") if isinstance(payload.get("acceptance_criteria"), list) else []
    signals = payload.get("signals_of_interest") if isinstance(payload.get("signals_of_interest"), list) else []

    parts: List[str] = []
    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if scenario:
        scenario_bits: List[str] = []
        if "t_start_s" in scenario and "t_end_s" in scenario:
            scenario_bits.append(f"time window {scenario.get('t_start_s')}s to {scenario.get('t_end_s')}s")
        inputs = scenario.get("inputs")
        if isinstance(inputs, dict) and inputs:
            scenario_bits.append("inputs: " + ", ".join(sorted(str(k) for k in inputs)))
        initial = scenario.get("initial_conditions")
        if isinstance(initial, dict) and initial:
            scenario_bits.append("initial conditions: " + ", ".join(sorted(str(k) for k in initial)))
        if scenario_bits:
            parts.append("Scenario " + "; ".join(scenario_bits))
    if criteria:
        crit_text = []
        for entry in criteria[:6]:
            if not isinstance(entry, dict):
                continue
            metric = str(entry.get("metric") or "").strip()
            op = str(entry.get("operator") or "").strip()
            value = entry.get("value")
            if metric and op:
                crit_text.append(f"{metric} {op} {value}")
        if crit_text:
            parts.append("Acceptance criteria: " + "; ".join(crit_text))
    if signals:
        parts.append("Signals of interest: " + ", ".join(str(s) for s in signals))
    return ". ".join(part for part in parts if part)


def ensure_symlink(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    rel = os.path.relpath(src, start=dst.parent)
    dst.symlink_to(rel)


def _coerce_scalar(value: Optional[str]) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return text
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer() and text.isdigit():
        return int(number)
    return number


def _fmi_bool(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() == "true"


def _scalar_type_name(variable: ET.Element) -> str:
    for child in variable:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in {"Real", "Integer", "Boolean", "String", "Enumeration", "Binary"}:
            return tag
    return "Real"


def parse_fmu_metadata(*, fmu_path: Path, asset_id: str, fallback_name: str = "", fallback_description: str = "") -> Dict[str, Any]:
    with zipfile.ZipFile(fmu_path) as archive:
        root = ET.fromstring(archive.read("modelDescription.xml"))

    ports: List[Dict[str, Any]] = []
    model_variables = root.find("ModelVariables")
    if model_variables is not None:
        for variable in model_variables.findall("ScalarVariable"):
            name = str(variable.attrib.get("name") or "").strip()
            if not name:
                continue
            scalar = next(iter(variable), None)
            ports.append(
                {
                    "name": name,
                    "causality": str(variable.attrib.get("causality") or "local"),
                    "variability": str(variable.attrib.get("variability") or "continuous"),
                    "type": _scalar_type_name(variable),
                    "unit": str(scalar.attrib.get("unit") or "") if scalar is not None else "",
                    "description": str(variable.attrib.get("description") or ""),
                }
            )

    default_experiment: Dict[str, Any] = {}
    default_node = root.find("DefaultExperiment")
    if default_node is not None:
        for key in ("startTime", "stopTime", "stepSize", "tolerance"):
            coerced = _coerce_scalar(default_node.attrib.get(key))
            if coerced is not None:
                default_experiment[key] = coerced

    cs = root.find("CoSimulation")
    me = root.find("ModelExchange")
    fmi_types: List[str] = []
    if cs is not None:
        fmi_types.append("CoSimulation")
    if me is not None:
        fmi_types.append("ModelExchange")

    if cs is not None:
        needs_execution_tool = _fmi_bool(cs.attrib.get("needsExecutionTool"))
        can_handle_variable_step = _fmi_bool(cs.attrib.get("canHandleVariableCommunicationStepSize"))
        can_interpolate_inputs = _fmi_bool(cs.attrib.get("canInterpolateInputs"))
        can_run_asynchronously = _fmi_bool(cs.attrib.get("canRunAsynchronuously"))
        cs_single_instance = _fmi_bool(cs.attrib.get("canBeInstantiatedOnlyOncePerProcess"))
        cs_directional = _fmi_bool(cs.attrib.get("providesDirectionalDerivatives")) or _fmi_bool(cs.attrib.get("providesDirectionalDerivative"))
        fixed_internal_step_size = _coerce_scalar(cs.attrib.get("fixedInternalStepSize"))
    else:
        needs_execution_tool = False
        can_handle_variable_step = False
        can_interpolate_inputs = False
        can_run_asynchronously = False
        cs_single_instance = False
        cs_directional = False
        fixed_internal_step_size = None

    me_needs_execution_tool = _fmi_bool(me.attrib.get("needsExecutionTool")) if me is not None else False
    me_single_instance = _fmi_bool(me.attrib.get("canBeInstantiatedOnlyOncePerProcess")) if me is not None else False
    me_directional = (
        _fmi_bool(me.attrib.get("providesDirectionalDerivatives")) or _fmi_bool(me.attrib.get("providesDirectionalDerivative"))
    ) if me is not None else False

    capabilities = {
        "needs_execution_tool": needs_execution_tool or me_needs_execution_tool,
        "can_handle_variable_communication_step_size": can_handle_variable_step,
        "can_interpolate_inputs": can_interpolate_inputs,
        "can_run_asynchronously": can_run_asynchronously,
        "can_be_instantiated_only_once_per_process": cs_single_instance or me_single_instance,
        "provides_directional_derivatives": cs_directional or me_directional,
        "fixed_internal_step_size": fixed_internal_step_size,
    }

    return {
        "schema": "UNIFIED_FMU_METADATA_V1",
        "asset_id": asset_id,
        "name": str(root.attrib.get("modelName") or fallback_name or fmu_path.stem),
        "description": str(root.attrib.get("description") or fallback_description or ""),
        "fmi_version": str(root.attrib.get("fmiVersion") or "2.0"),
        "fmi_types": fmi_types,
        "ports": ports,
        "inputs": [port["name"] for port in ports if port["causality"] == "input"],
        "outputs": [port["name"] for port in ports if port["causality"] == "output"],
        "capabilities": capabilities,
        "default_experiment": default_experiment,
    }


def resolve_fmu_signal_name(reference: str, port_names: Sequence[str]) -> str:
    text = str(reference or "").strip()
    if not text:
        return ""
    known = {str(name) for name in port_names if str(name)}
    if text in known:
        return text
    parts = text.split(".")
    for index in range(1, len(parts)):
        suffix = ".".join(parts[index:])
        if suffix in known:
            return suffix
    tail = parts[-1]
    if tail in known:
        return tail
    return text


def iter_named_blocks(text: str, prefix: str) -> Iterator[Tuple[str, str]]:
    lines = text.splitlines()
    pattern = re.compile(rf"^\s*{re.escape(prefix)}\s+([A-Za-z0-9_]+).*?\{{\s*$")
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        match = pattern.match(line)
        if not match:
            idx += 1
            continue
        name = match.group(1)
        block_lines = [line]
        depth = line.count("{") - line.count("}")
        idx += 1
        while idx < len(lines):
            cur = lines[idx]
            block_lines.append(cur)
            depth += cur.count("{") - cur.count("}")
            idx += 1
            if depth <= 0:
                break
        yield name, "\n".join(block_lines)


def _collect_port_definitions(text: str) -> Dict[str, List[Dict[str, str]]]:
    defs: Dict[str, List[Dict[str, str]]] = {}
    direct_port_re = re.compile(
        r"^\s*(in|out)\s+(?:item\s+)?([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_:.<>~]+))?\s*;"
    )
    for name, block in iter_named_blocks(text, "port def"):
        entries: List[Dict[str, str]] = []
        for line in block.splitlines():
            match = direct_port_re.match(line)
            if not match:
                continue
            direction, signal_name, signal_type = match.groups()
            entries.append(
                {
                    "name": signal_name,
                    "direction": direction,
                    "type": signal_type or "",
                }
            )
        defs[name] = entries
    return defs


def _collect_interface_definitions(text: str) -> Dict[str, Dict[str, Any]]:
    defs: Dict[str, Dict[str, Any]] = {}
    end_re = re.compile(r"^\s*end\s+([A-Za-z0-9_]+)\s*:\s*~?([A-Za-z0-9_]+)\s*;", flags=re.MULTILINE)
    flow_re = re.compile(
        r"^\s*flow\s+([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s+to\s+([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*;",
        flags=re.MULTILINE,
    )
    for name, block in iter_named_blocks(text, "interface def"):
        defs[name] = {
            "end_types": {alias: port_type for alias, port_type in end_re.findall(block)},
            "flows": [
                {
                    "source_end": src_end,
                    "source_signal": src_signal,
                    "target_end": dst_end,
                    "target_signal": dst_signal,
                }
                for src_end, src_signal, dst_end, dst_signal in flow_re.findall(block)
            ],
        }
    return defs


def _parse_part_block_ports(block: str, port_defs: Dict[str, List[Dict[str, str]]]) -> Tuple[List[Dict[str, str]], List[str], Dict[str, str]]:
    ports: List[Dict[str, str]] = []
    constraints: List[str] = []
    port_alias_to_type: Dict[str, str] = {}

    direct_var_re = re.compile(r"^\s*(in|out)\s+([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_:.<>~]+)\s*;")
    shorthand_port_re = re.compile(r"^\s*(in|out)\s+port\s+([A-Za-z0-9_]+)\s*;")
    typed_port_re = re.compile(r"^\s*port\s+([A-Za-z0-9_]+)\s*:\s*~?([A-Za-z0-9_]+)\s*;")
    constraint_re = re.compile(r"assert\s+constraint\s+([A-Za-z0-9_]+)")

    for line in block.splitlines():
        constraint_match = constraint_re.search(line)
        if constraint_match:
            constraints.append(constraint_match.group(1))

        direct = direct_var_re.match(line)
        if direct:
            direction, signal_name, signal_type = direct.groups()
            ports.append(
                {
                    "name": signal_name,
                    "direction": direction,
                    "type": signal_type,
                    "qualified_name": signal_name,
                }
            )
            continue

        shorthand = shorthand_port_re.match(line)
        if shorthand:
            direction, signal_name = shorthand.groups()
            ports.append(
                {
                    "name": signal_name,
                    "direction": direction,
                    "type": "",
                    "qualified_name": signal_name,
                }
            )
            continue

        typed = typed_port_re.match(line)
        if typed:
            alias, port_type = typed.groups()
            port_alias_to_type[alias] = port_type
            template_entries = port_defs.get(port_type)
            if template_entries:
                for entry in template_entries:
                    signal_name = entry["name"]
                    ports.append(
                        {
                            "name": signal_name,
                            "direction": entry["direction"],
                            "type": entry.get("type", ""),
                            "qualified_name": f"{alias}.{signal_name}",
                            "port_alias": alias,
                            "port_type": port_type,
                        }
                    )
            else:
                ports.append(
                    {
                        "name": alias,
                        "direction": "unknown",
                        "type": port_type,
                        "qualified_name": alias,
                        "port_alias": alias,
                        "port_type": port_type,
                    }
                )
    return ports, constraints, port_alias_to_type


def _parse_interface_endpoint(text: str) -> Optional[Dict[str, str]]:
    match = re.fullmatch(
        r"(?:(?P<end_alias>[A-Za-z0-9_]+)\s*::>\s*)?(?P<component>[A-Za-z0-9_]+)\.(?P<port_alias>[A-Za-z0-9_]+)",
        str(text or "").strip(),
    )
    if not match:
        return None
    return {
        "end_alias": str(match.group("end_alias") or "").strip(),
        "component": str(match.group("component") or "").strip(),
        "port_alias": str(match.group("port_alias") or "").strip(),
    }


def _infer_interface_end_alias(
    endpoint: Dict[str, str],
    *,
    end_types: Dict[str, str],
    instance_map: Dict[str, str],
    part_defs: Dict[str, Dict[str, Any]],
    used_aliases: set[str],
) -> str:
    explicit = str(endpoint.get("end_alias") or "").strip()
    if explicit in end_types:
        return explicit

    component = str(endpoint.get("component") or "").strip()
    port_alias = str(endpoint.get("port_alias") or "").strip()
    part_type = instance_map.get(component, "")
    port_type = str((part_defs.get(part_type, {}).get("port_alias_to_type") or {}).get(port_alias) or "").strip()
    if not port_type:
        return ""

    unmatched = [alias for alias, expected_type in end_types.items() if expected_type == port_type and alias not in used_aliases]
    if len(unmatched) == 1:
        return unmatched[0]

    all_matches = [alias for alias, expected_type in end_types.items() if expected_type == port_type]
    if len(all_matches) == 1:
        return all_matches[0]
    return ""


def _collect_interface_connections(
    block: str,
    *,
    interface_defs: Dict[str, Dict[str, Any]],
    instance_map: Dict[str, str],
    part_defs: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, str]], set[Tuple[str, str, str, str]]]:
    normalized = re.sub(r"\s+", " ", block)
    statement_re = re.compile(
        r"interface(?:\s+connect)?\s+([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_]+)\s+connect\s+([^;]+?)\s+to\s+([^;]+?)\s*;"
    )
    connections: List[Dict[str, str]] = []
    consumed_edges: set[Tuple[str, str, str, str]] = set()

    for _name, interface_name, left_text, right_text in statement_re.findall(normalized):
        interface_def = interface_defs.get(interface_name)
        if not interface_def:
            continue

        left = _parse_interface_endpoint(left_text)
        right = _parse_interface_endpoint(right_text)
        if left is None or right is None:
            continue

        end_types = dict(interface_def.get("end_types") or {})
        if not end_types:
            continue

        endpoints = [left, right]
        end_bindings: Dict[str, Dict[str, str]] = {}
        used_aliases: set[str] = set()
        for endpoint in endpoints:
            end_alias = _infer_interface_end_alias(
                endpoint,
                end_types=end_types,
                instance_map=instance_map,
                part_defs=part_defs,
                used_aliases=used_aliases,
            )
            if not end_alias:
                continue
            used_aliases.add(end_alias)
            end_bindings[end_alias] = {
                "component": endpoint["component"],
                "port_alias": endpoint["port_alias"],
            }

        if len(end_bindings) < 2:
            continue

        for flow in interface_def.get("flows", []):
            source_binding = end_bindings.get(str(flow.get("source_end") or ""))
            target_binding = end_bindings.get(str(flow.get("target_end") or ""))
            if source_binding is None or target_binding is None:
                continue
            connections.append(
                {
                    "source_component": source_binding["component"],
                    "source_signal": str(flow.get("source_signal") or ""),
                    "target_component": target_binding["component"],
                    "target_signal": str(flow.get("target_signal") or ""),
                }
            )
            consumed_edges.add(
                (
                    source_binding["component"],
                    source_binding["port_alias"],
                    target_binding["component"],
                    target_binding["port_alias"],
                )
            )

    return connections, consumed_edges


def _parse_bind_endpoint(text: str, *, instance_map: Dict[str, str]) -> Optional[Dict[str, str]]:
    normalized = str(text or "").strip()
    if not normalized:
        return None
    parts = [part for part in normalized.split(".") if part]
    if len(parts) < 2:
        return {"component": "", "path": normalized, "signal": normalized}
    component = parts[0]
    if component not in instance_map:
        return {"component": "", "path": normalized, "signal": parts[-1]}
    path = ".".join(parts[1:])
    return {"component": component, "path": path, "signal": parts[-1]}


def _resolve_component_signal(
    component: str,
    path: str,
    *,
    instance_map: Dict[str, str],
    part_defs: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, str]]:
    part_type = instance_map.get(component, "")
    if not part_type:
        return None
    ports = list(part_defs.get(part_type, {}).get("ports", []) or [])
    if not ports:
        return None

    exact_matches = [port for port in ports if str(port.get("qualified_name") or "") == path]
    if len(exact_matches) == 1:
        match = exact_matches[0]
        return {
            "signal": str(match.get("name") or ""),
            "direction": str(match.get("direction") or "unknown"),
        }

    signal_name = path.rsplit(".", 1)[-1]
    direct_matches = [port for port in ports if str(port.get("name") or "") == signal_name]
    if len(direct_matches) == 1:
        match = direct_matches[0]
        return {
            "signal": str(match.get("name") or ""),
            "direction": str(match.get("direction") or "unknown"),
        }

    suffix_matches = [
        port
        for port in ports
        if str(port.get("qualified_name") or "").endswith(f".{signal_name}")
    ]
    if len(suffix_matches) == 1:
        match = suffix_matches[0]
        return {
            "signal": str(match.get("name") or ""),
            "direction": str(match.get("direction") or "unknown"),
        }
    return None


def _collect_bind_connections(
    block: str,
    *,
    instance_map: Dict[str, str],
    part_defs: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    normalized = re.sub(r"\s+", " ", block)
    statement_re = re.compile(r"bind\s+([^=;]+?)\s*=\s*([^;]+?)\s*;")
    connections: List[Dict[str, str]] = []

    for left_text, right_text in statement_re.findall(normalized):
        left = _parse_bind_endpoint(left_text, instance_map=instance_map)
        right = _parse_bind_endpoint(right_text, instance_map=instance_map)
        if left is None or right is None:
            continue
        if not left.get("component") or not right.get("component"):
            continue

        left_signal = _resolve_component_signal(
            str(left["component"]),
            str(left["path"]),
            instance_map=instance_map,
            part_defs=part_defs,
        )
        right_signal = _resolve_component_signal(
            str(right["component"]),
            str(right["path"]),
            instance_map=instance_map,
            part_defs=part_defs,
        )
        if left_signal is None or right_signal is None:
            continue

        left_direction = str(left_signal.get("direction") or "unknown")
        right_direction = str(right_signal.get("direction") or "unknown")
        if left_direction == "in" and right_direction == "out":
            source_component = str(right["component"])
            source_signal = str(right_signal["signal"])
            target_component = str(left["component"])
            target_signal = str(left_signal["signal"])
        elif left_direction == "out" and right_direction == "in":
            source_component = str(left["component"])
            source_signal = str(left_signal["signal"])
            target_component = str(right["component"])
            target_signal = str(right_signal["signal"])
        else:
            source_component = str(right["component"])
            source_signal = str(right_signal["signal"])
            target_component = str(left["component"])
            target_signal = str(left_signal["signal"])

        connections.append(
            {
                "source_component": source_component,
                "source_signal": source_signal,
                "target_component": target_component,
                "target_signal": target_signal,
            }
        )
    return connections


def parse_sysml_model(text: str, *, sysml_name: str = "") -> Dict[str, Any]:
    package_match = re.search(r"package\s+([A-Za-z0-9_]+)", text)
    package_name = package_match.group(1) if package_match else Path(sysml_name).stem

    port_defs = _collect_port_definitions(text)
    interface_defs = _collect_interface_definitions(text)
    part_defs: Dict[str, Dict[str, Any]] = {}
    for name, block in iter_named_blocks(text, "part def"):
        ports, constraints, port_alias_to_type = _parse_part_block_ports(block, port_defs)
        internal_parts = re.findall(r"^\s*part\s+([A-Za-z0-9_]+)\s*:\s*([A-Za-z0-9_]+)\s*;", block, flags=re.MULTILINE)
        normalized = re.sub(r"\s+", " ", block)
        connections: List[Dict[str, str]] = []
        connect_re = re.compile(
            r"connect\s+(?:[A-Za-z0-9_]+\s*::>\s*)?([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s+to\s+(?:[A-Za-z0-9_]+\s*::>\s*)?([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)",
            flags=re.MULTILINE,
        )
        for src_comp, src_port, dst_comp, dst_port in connect_re.findall(normalized):
            connections.append(
                {
                    "source_component": src_comp,
                    "source_port": src_port,
                    "target_component": dst_comp,
                    "target_port": dst_port,
                }
            )

        part_defs[name] = {
            "definition_name": name,
            "ports": ports,
            "constraints": constraints,
            "internal_parts": [{"name": p[0], "type": p[1]} for p in internal_parts],
            "connections": connections,
            "port_alias_to_type": port_alias_to_type,
            "block": block,
        }

    system_name = ""
    system_block: Optional[Dict[str, Any]] = None
    for name, block in part_defs.items():
        if system_block is None or len(block["internal_parts"]) > len(system_block["internal_parts"]):
            system_name = name
            system_block = block

    components: List[Dict[str, Any]] = []
    connections: List[Dict[str, str]] = []
    adjacency: Dict[str, List[str]] = {}
    constraints: List[str] = []

    if system_block and system_block["internal_parts"]:
        instance_map = {entry["name"]: entry["type"] for entry in system_block["internal_parts"]}
        for alias, part_type in instance_map.items():
            part_block = part_defs.get(part_type, {})
            component_ports: List[Dict[str, str]] = []
            for port in part_block.get("ports", []):
                component_ports.append(
                    {
                        "name": port["name"],
                        "direction": port.get("direction", "unknown"),
                        "type": port.get("type", ""),
                        "qualified_name": f"{alias}.{port.get('qualified_name') or port['name']}",
                    }
                )
            components.append(
                {
                    "name": alias,
                    "component_type": part_type,
                    "ports": component_ports,
                }
            )
            constraints.extend(part_block.get("constraints", []))

        exact_connections, consumed_edges = _collect_interface_connections(
            str(system_block.get("block") or ""),
            interface_defs=interface_defs,
            instance_map=instance_map,
            part_defs=part_defs,
        )
        bind_connections = _collect_bind_connections(
            str(system_block.get("block") or ""),
            instance_map=instance_map,
            part_defs=part_defs,
        )
        for connection in [*exact_connections, *bind_connections]:
            src = connection["source_component"]
            dst = connection["target_component"]
            adjacency.setdefault(src, [])
            adjacency.setdefault(dst, [])
            if dst not in adjacency[src]:
                adjacency[src].append(dst)
            if src not in adjacency[dst]:
                adjacency[dst].append(src)
            connections.append(connection)

        for edge in system_block.get("connections", []):
            src = edge["source_component"]
            dst = edge["target_component"]
            raw_edge = (
                str(edge.get("source_component") or ""),
                str(edge.get("source_port") or ""),
                str(edge.get("target_component") or ""),
                str(edge.get("target_port") or ""),
            )
            if raw_edge in consumed_edges:
                continue
            adjacency.setdefault(src, [])
            adjacency.setdefault(dst, [])
            if dst not in adjacency[src]:
                adjacency[src].append(dst)
            if src not in adjacency[dst]:
                adjacency[dst].append(src)

            src_type = instance_map.get(src, src)
            dst_type = instance_map.get(dst, dst)
            src_port_type = (part_defs.get(src_type, {}).get("port_alias_to_type") or {}).get(edge["source_port"], "")
            dst_port_type = (part_defs.get(dst_type, {}).get("port_alias_to_type") or {}).get(edge["target_port"], "")
            src_signals = port_defs.get(src_port_type, [])
            dst_signals = port_defs.get(dst_port_type, [])
            if src_signals and dst_signals:
                for src_sig in src_signals:
                    for dst_sig in dst_signals:
                        if src_sig.get("direction") != "out" or dst_sig.get("direction") != "in":
                            continue
                        connections.append(
                            {
                                "source_component": src,
                                "source_signal": src_sig["name"],
                                "target_component": dst,
                                "target_signal": dst_sig["name"],
                            }
                        )
            else:
                connections.append(
                    {
                        "source_component": src,
                        "source_signal": edge["source_port"],
                        "target_component": dst,
                        "target_signal": edge["target_port"],
                    }
                )
        constraints.extend(system_block.get("constraints", []))
    else:
        for name, block in part_defs.items():
            component_ports = [
                {
                    "name": port["name"],
                    "direction": port.get("direction", "unknown"),
                    "type": port.get("type", ""),
                    "qualified_name": port.get("qualified_name", port["name"]),
                }
                for port in block.get("ports", [])
            ]
            components.append({"name": name, "component_type": name, "ports": component_ports})
            adjacency.setdefault(name, [])
            constraints.extend(block.get("constraints", []))
        if components:
            system_name = components[0]["name"]

    return {
        "package_name": package_name,
        "system_name": system_name or package_name,
        "components": components,
        "connections": connections,
        "adjacency": adjacency,
        "constraints": sorted(set(c for c in constraints if c)),
    }


def build_benchmark_requirement_text(*, model_name: str, description: str, inputs: Sequence[str], outputs: Sequence[str]) -> str:
    parts = [f"Verify the FMU model {model_name}."]
    if description:
        parts.append(description)
    if outputs:
        parts.append("Observe outputs: " + ", ".join(outputs[:12]))
    if inputs:
        parts.append("Provide inputs: " + ", ".join(inputs[:12]))
    return " ".join(parts)
