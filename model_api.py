"""Versioned JSON contract; complete inputs round-trip without losing chemistry."""
from __future__ import annotations
import json
from dataclasses import asdict, fields, replace
from pathlib import Path
from .calculations import (MODEL_VERSION, AcidizingParameters, AcidSystem, HorizontalSegment,
    CalculationError, build_default_segments, default_acid_systems, evaluate_horizontal_section,
    run_simulation, validate_parameters, validate_acid, validate_segments, segment_depth)

INTERFACE_VERSION = "3.0"


def _record(cls, record, label):
    if not isinstance(record, dict):
        raise CalculationError(label + "必须是对象")
    allowed = {item.name: item for item in fields(cls)}
    unknown = set(record) - set(allowed)
    if unknown:
        raise CalculationError(label + "含未知字段：" + "、".join(sorted(unknown)))
    values = {}
    string_fields = {"name", "acid_system", "segment", "kind"}
    string_fields.update(f.name for f in fields(cls) if isinstance(f.default, str))
    for key, value in record.items():
        if key in string_fields:
            if not isinstance(value, str):
                raise CalculationError(label + key + "必须是文本")
            values[key] = value
        elif key == "damage_radius" and value is None:
            values[key] = None
        else:
            if isinstance(value, bool):
                raise CalculationError(label + key + "必须为数字，不能为布尔值")
            try:
                values[key] = float(value)
            except (ValueError, TypeError):
                raise CalculationError(label + key + "必须为数字")
    try:
        return cls(**values)
    except TypeError as exc:
        raise CalculationError(label + "缺少必要字段：" + str(exc))


def default_request():
    params = AcidizingParameters()
    return {"interface_version": INTERFACE_VERSION, "model_version": MODEL_VERSION,
            "parameters": asdict(params),
            "acid_systems": {key: asdict(value) for key, value in default_acid_systems().items()},
            "radial_acid_system": next(iter(default_acid_systems())),
            "horizontal_segments": [asdict(s) for s in build_default_segments(params)]}


def parse_request(payload):
    if not isinstance(payload, dict):
        raise CalculationError("接口输入必须是 JSON 对象")
    version = payload.get("interface_version", "1.0")
    if version not in ("1.0", "2.0", INTERFACE_VERSION):
        raise CalculationError("不支持的接口版本：%s" % version)
    params = _record(AcidizingParameters, payload.get("parameters", {}), "工程参数")
    validate_parameters(params)
    raw_acids = payload.get("acid_systems")
    acids = default_acid_systems() if raw_acids is None else {}
    if raw_acids is None and version == "1.0":
        # Preserve usable legacy fluid values; ambiguous legacy kinetic units are not reused.
        first_name = next(iter(acids))
        acids[first_name] = replace(acids[first_name], hcl_fraction=params.CHCl, hf_fraction=params.Coo,
                                   density=params.pHCl, viscosity=params.ua, reference_temperature=params.T0,
                                   treatment_formula="旧版数值迁移：HCl %.3g%% + HF %.3g%%；请核对配方" % (params.CHCl * 100, params.Coo * 100),
                                   calibration_note="旧版浓度、密度、黏度已迁移；旧动力学单位不明确，使用新版示例系数，需重新标定")
        validate_acid(acids[first_name])
    if raw_acids is not None:
        if not isinstance(raw_acids, dict) or not raw_acids:
            raise CalculationError("酸液库必须是非空对象")
        for key, record in raw_acids.items():
            acid = _record(AcidSystem, record, "酸液" + str(key))
            if key != acid.name:
                raise CalculationError("酸液库键名必须与酸液名称相同")
            validate_acid(acid)
            acids[key] = acid
    raw_segments = payload.get("horizontal_segments")
    if raw_segments is None:
        segments = build_default_segments(params)
    else:
        if not isinstance(raw_segments, list):
            raise CalculationError("水平段必须是数组")
        segments = []
        for i, record in enumerate(raw_segments):
            segment = _record(HorizontalSegment, record, "第%d段" % (i + 1))
            if segment.damage_radius is not None:
                depth = segment_depth(segment, params)
                if "damage_depth" in record and abs(float(record["damage_depth"]) - depth) > 1e-6:
                    raise CalculationError("污染半径与污染深度不一致")
                segment = replace(segment, damage_radius=None, damage_depth=depth)
            segments.append(segment)
    if params.well_type == "水平井":
        validate_segments(params, segments, acids)
    radial_name = payload.get("radial_acid_system", next(iter(acids)))
    if radial_name not in acids:
        raise CalculationError("直井酸液体系不在酸液库中")
    return params, segments, acids, radial_name


def parse_workflow(payload):
    from .workflow import (active_segments, default_completions, default_stages, CompletionInterval,
        ConstructionStage, Economics, OptimizationConstraints, validate_completions, validate_stages,
        validate_economics)
    p, stored_segments, acids, name = parse_request(payload)
    segments = active_segments(p, stored_segments, name)
    raw = payload.get("completion_intervals")
    if raw is not None and not isinstance(raw,list):
        raise CalculationError("开放区间必须为数组或null")
    intervals = default_completions(p,segments) if raw is None else [_record(CompletionInterval,x,"开放区间") for x in raw]
    validate_completions(p,segments,intervals)
    raw = payload.get("construction_stages")
    if raw is not None and not isinstance(raw,list):
        raise CalculationError("施工段塞必须为数组或null")
    stages = default_stages(p,segments,acids,intervals) if raw is None else [_record(ConstructionStage,x,"施工段塞") for x in raw]
    validate_stages(stages,segments,acids)
    economic = _record(Economics,payload.get("economics",{}),"经济参数")
    validate_economics(economic)
    constraints = _record(OptimizationConstraints,payload.get("optimization_constraints",{}),"施工约束")
    return p, segments, acids, name, intervals, stages, economic, constraints


def calculate_design(payload, return_objects=False):
    from .workflow import simulate_schedule, economic_evaluation
    from .calculations import water_analysis
    params, segments, acids, radial_name = parse_request(payload)
    _, active, _, _, intervals, stages, economic, constraints = parse_workflow(payload)
    horizontal, pressure, stage_results = simulate_schedule(params,active,acids,stages,intervals)
    from .calculations import BasicResults, SimulationResult
    first=horizontal.segments[0]
    volumes=horizontal.stage_volumes
    basic=BasicResults(first.skin_before,params.limit_p,max((s.allowed_rate for s in horizontal.segments),default=0.),
        max((s.required_rate for s in horizontal.segments),default=0.),volumes['preflush'],volumes['treatment'],
        volumes['postflush'],volumes['displacement'],horizontal.total_fluid_volume,params.alpha*params.vertical_depth)
    radial=SimulationResult(basic,first.predicted_radius,[],[],list(horizontal.conclusions),first.temperature_profile,first.reaction)
    summary = asdict(horizontal)
    summary.pop("segments")
    migration = []
    if payload.get("interface_version", "1.0") == "1.0":
        migration.append("旧版导入：未提供的分段酸量按100m³、时间按120min、矿物及新动力学按示例值补齐；请核对后使用")
    if payload.get("interface_version", "1.0") != INTERFACE_VERSION:
        migration.append("旧版导入：新增井形默认水平井、完井默认射孔；未提供的开放位置按各处理段补齐。摩阻梯度现按1m³/min参考排量解释，需复核。")
    response = {"interface_version": INTERFACE_VERSION, "model_version": MODEL_VERSION,
            "migration_warnings": migration,
            "radial_summary": {**asdict(radial.basic), "scope": "兼容字段：当前方案汇总及首个活动段反应；不是额外直井方案", "effective_radius": radial.effective_radius,
                               "penetration_depth": radial.effective_radius - params.rw,
                               "warnings": radial.warnings, "reaction": asdict(radial.reaction)},
            "radial_temperature_profile": [asdict(p) for p in radial.temperature_profile],
            "horizontal_summary": summary,
            "active_well_type": params.well_type,
            "pressure_curve": pressure,
            "construction_stage_results": stage_results,
            "water_analysis": water_analysis(params),
            "economics": economic_evaluation(economic,horizontal.expected_productivity_ratio,horizontal.stage_volumes),
            "segment_results": [asdict(s) for s in horizontal.segments],
            "input_snapshot": {"interface_version": INTERFACE_VERSION, "model_version": MODEL_VERSION,
                               "parameters": asdict(params), "horizontal_segments": [asdict(s) for s in segments],
                               "acid_systems": {key: asdict(value) for key, value in acids.items()},
                               "radial_acid_system": radial_name,
                               "completion_intervals": [asdict(x) for x in intervals],
                               "construction_stages": [asdict(x) for x in stages],
                               "economics": asdict(economic), "optimization_constraints": asdict(constraints)},
            "assumptions": ["沿用旧版2m作用深度上限；集总反应/热量平衡；沉淀风险代理模型；系数待标定",
                            "全井产能指数为各段之和，假设共用压差、无段间干扰；不是三维水平井模型"]}
    return (radial, horizontal, response) if return_objects else response


def save_request(path, payload):
    parse_workflow(payload)
    return save_response(path, payload)


def load_request(path):
    def reject(value):
        raise CalculationError("JSON 包含非有限数字：" + value)
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject)
    parse_workflow(payload)
    return payload


def save_response(path, response):
    target = Path(path)
    target.write_text(json.dumps(response, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return target
