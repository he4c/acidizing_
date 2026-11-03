"""Transparent screening model, not a calibrated geochemical simulator.

Units: m, m3, min, mD, MPa, Celsius; kinetics internally use Kelvin and J/mol.
See MODEL_NOTES.md for derivations, empirical closures and literature scope.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, fields, replace
from typing import List, Optional, Tuple, Dict

PI = math.pi
MAX_PROFILE_ROWS = 8000
MODEL_VERSION = "4.0-discussion-20261015"
DEFAULT_ACID_NAME = "常规土酸（示例）"


class CalculationError(ValueError):
    pass


@dataclass(frozen=True)
class AcidizingParameters:
    rw: float = 0.05221
    Np: float = 250
    Dp: float = 0.012
    aM: float = 0.82
    rti: float = 0.033755
    dti: float = 0.0366
    dce: float = 0.0889
    Xt: float = 0.00551
    Xc: float = 0.00587
    Xan: float = 0.04643
    Tb: float = 25
    Zb: float = 20
    aT: float = 0.02
    Khs: float = 0.62
    h: float = 17.5
    re: float = 200
    Zh: float = 4969
    Ps: float = 47.1062
    alpha: float = 0.029
    kav: float = 36.12
    o: float = 0.145
    ko: float = 36.12
    Rd: float = 1.05221
    kd: float = 12.3
    lambd: float = 0.03467
    limit_p: float = 70
    CMo: float = 0.00458438
    CMi: float = 0.00196474
    pr: float = 2.6
    Wr: float = 397
    pCaCO3: float = 2.7
    CM: float = 0.03
    Xhcl: float = 0.053
    ua: float = 0.8
    f: float = 0.003
    C: float = 1
    pHCl: float = 1017.4
    CHCl: float = 0.1
    T0: float = 25
    kro: float = 0.532
    Coo: float = 0.015
    Ea: float = 4
    omega: float = 22.64
    Khan: float = 0.00384
    R: float = 1.987
    V_per_m: float = 1.7
    Vh_per_m: float = 1
    Tf: float = 20
    vertical_depth: float = 3000
    max_penetration: float = 2.0
    heat_transfer_u: float = 12.0
    fluid_cp: float = 4180.0
    rock_cp: float = 850.0
    quartz: float = 0.70
    feldspar: float = 0.15
    clay: float = 0.10
    carbonate: float = 0.03
    other_minerals: float = 0.02
    calcium_mg_l: float = 1000.0
    sodium_mg_l: float = 5000.0
    potassium_mg_l: float = 200.0
    precipitation_enabled: float = 1.0
    precipitation_yield: float = 0.6
    plugging_sensitivity: float = 30.0
    damage_solid_fraction: float = 0.005
    preflush_ratio: float = 0.25
    postflush_ratio: float = 0.20
    oil_viscosity: float = 2.0
    oil_volume_factor: float = 1.1
    well_type: str = "水平井"
    completion_type: str = "射孔完井"
    inclination_deg: float = 90.0
    completion_resistance: float = 0.0  # MPa / (m3/min), screen/gravel calibration
    water_mode: str = "ions"
    salinity_mg_l: float = 16000.0
    magnesium_mg_l: float = 200.0
    chloride_mg_l: float = 10000.0
    sulfate_mg_l: float = 200.0
    bicarbonate_mg_l: float = 300.0
    water_saturation: float = 0.3
    oil_saturation: float = 0.7
    gas_saturation: float = 0.0
    oil_relative_permeability: float = 1.0


@dataclass(frozen=True)
class AcidSystem:
    name: str = DEFAULT_ACID_NAME
    preflush_type: str = "盐酸前置液"
    preflush_formula: str = "10% HCl；配伍添加剂另行实验确定"
    treatment_type: str = "土酸"
    treatment_formula: str = "10% HCl + 1.5% HF（质量分数）"
    postflush_type: str = "弱酸后置液"
    postflush_formula: str = "3% HCl（示例）"
    displacement_type: str = "配伍盐水"
    displacement_formula: str = "与地层水配伍、低钙盐水（实验确定）"
    hcl_fraction: float = 0.10
    hf_fraction: float = 0.015
    organic_fraction: float = 0.0
    density: float = 1030.0
    viscosity: float = 1.0
    heat_capacity: float = 4180.0
    reference_temperature: float = 25.0
    rate_constant: float = 0.015
    activation_energy: float = 20.0
    reaction_heat: float = 25.0
    dissolving_capacity: float = 0.50
    retardation_factor: float = 1.0
    preflush_efficiency: float = 0.50
    flowback_efficiency: float = 0.60
    max_temperature: float = 120.0
    calibration_note: str = "示例系数，未用目标储层岩心实验标定"
    reaction_model: str = "arrhenius"
    mass_transfer_rate: float = 0.05  # effective lumped 1/min, requires calibration


def default_acid_systems() -> Dict[str, AcidSystem]:
    normal = AcidSystem()
    mild = replace(normal, name="低氟土酸（示例）", hcl_fraction=0.08,
                   hf_fraction=0.01, treatment_formula="8% HCl + 1% HF（质量分数）")
    retarded = replace(normal, name="有机缓速酸（示例）", hcl_fraction=0.06,
                       hf_fraction=0.008, organic_fraction=0.05,
                       treatment_type="有机缓速酸", treatment_formula="6% HCl + 0.8% HF + 5% 有机酸（质量分数）",
                       retardation_factor=0.35, viscosity=1.5, max_temperature=150.0)
    pre = replace(normal, name="前置盐酸10%（示例）", hf_fraction=0,
                  treatment_formula="10% HCl", treatment_type="盐酸")
    post = replace(pre, name="后置盐酸3%（示例）", hcl_fraction=.03, treatment_formula="3% HCl")
    salt = replace(normal, name="配伍盐水（示例）", hcl_fraction=0, hf_fraction=0,
                   rate_constant=0, reaction_heat=0, treatment_type="配伍盐水", treatment_formula="配伍盐水；离子配伍另行验证")
    return {item.name: item for item in (normal, mild, retarded, pre, post, salt)}


@dataclass(frozen=True)
class BasicResults:
    skin_factor: float
    fracture_pressure: float  # historical key: safe surface pressure ceiling, MPa
    max_rate: float
    construction_rate: float
    preflush_volume: float
    treatment_volume: float
    postflush_volume: float
    displacement_volume: float
    total_acid_volume: float  # historical key: total fluids including displacement
    formation_fracture_pressure: float = 0.0


@dataclass(frozen=True)
class ProfileRow:
    tj_min: float
    radius: float
    acid_concentration: float
    mineral_concentration: float
    porosity: float
    permeability: float
    temperature: float


@dataclass(frozen=True)
class ProductivityRow:
    tj_min: float
    radius: float
    productivity_ratio: float


@dataclass(frozen=True)
class TemperaturePoint:
    measured_depth: float
    vertical_depth: float
    formation_temperature: float
    fluid_temperature: float
    fluid_gradient: float


@dataclass(frozen=True)
class ReactionResult:
    acid_remaining_fraction: float
    dissolved_rock_kg: float
    dissolution_fraction: float
    precipitate_kg: float
    precipitation_risk: float
    temperature: float
    reaction_temperature_rise: float
    average_rate: float
    porosity_after: float
    permeability_after: float
    permeability_without_precipitation: float
    warnings: List[str]
    dissolved_silicate_kg: float = 0.0
    dissolved_carbonate_kg: float = 0.0


@dataclass(frozen=True)
class SimulationResult:
    basic: BasicResults
    effective_radius: float
    profile_rows: List[ProfileRow]
    productivity_rows: List[ProductivityRow]
    warnings: List[str]
    temperature_profile: List[TemperaturePoint] = field(default_factory=list)
    reaction: Optional[ReactionResult] = None


@dataclass(frozen=True)
class EconomicParameters:
    base_daily_income: float = 10000.0
    acid_unit_cost: float = 1200.0
    effective_days: float = 180.0


@dataclass(frozen=True)
class RadiusScenario:
    target_radius: float
    effective_radius: float
    productivity_ratio: float
    total_acid_volume: float
    revenue: float
    cost: float
    net_benefit: float


@dataclass(frozen=True)
class HorizontalSegment:
    name: str
    start_md: float
    end_md: float
    permeability: float
    damaged_permeability: float
    damage_radius: Optional[float] = None  # v1 compatibility: distance from well axis
    porosity: float = 0.145
    contact_time: float = 120.0  # acid pumping / exposure time, not drilling exposure
    damage_depth: float = 1.0  # distance from well wall
    acid_volume: float = 100.0
    acid_system: str = DEFAULT_ACID_NAME
    drilling_exposure_days: float = 1.0


@dataclass(frozen=True)
class SegmentEvaluation:
    name: str
    start_md: float
    end_md: float
    length: float
    skin_before: float
    allocated_acid: float
    predicted_radius: float
    coverage_ratio: float
    skin_after: float
    productivity_ratio: float
    feasibility_score: float
    status: str
    recommendation: str
    damage_depth: float
    penetration_depth: float
    acid_system: str
    productivity_undamaged: float
    productivity_damaged: float
    productivity_after: float
    recovery_ratio: float
    inlet_temperature: float
    reaction: ReactionResult
    stage_volumes: Dict[str, float]
    temperature_profile: List[TemperaturePoint]
    required_rate: float
    allowed_rate: float
    surface_pressure_limit: float
    estimated_pumping_minutes: float
    warnings: List[str]


@dataclass(frozen=True)
class HorizontalEvaluation:
    model_version: str
    mode: str
    total_length: float
    heterogeneity_cv: float
    average_coverage: float
    expected_productivity_ratio: float
    risk_segment_count: int
    segments: List[SegmentEvaluation]
    conclusions: List[str]
    total_treatment_volume: float
    stage_volumes: Dict[str, float]
    total_fluid_volume: float
    productivity_undamaged: float
    productivity_damaged: float
    productivity_after: float


def get_val(text: object) -> float:
    """Strict parsing: do not silently turn invalid engineering data into zero."""
    try:
        value = float(str(text).strip().replace(",", ""))
    except (TypeError, ValueError):
        raise CalculationError("请输入有效数字：%r" % text)
    if not math.isfinite(value):
        raise CalculationError("数值必须有限，不能为 NaN 或无穷大")
    return value


def _range(value, lo, hi, name, strict_low=False):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise CalculationError("%s 必须是有限数字" % name)
    if value < lo or value > hi or (strict_low and value == lo):
        raise CalculationError("%s 必须%s %g 且不超过 %g" % (name, "大于" if strict_low else "不小于", lo, hi))


def validate_parameters(p: AcidizingParameters):
    for item in fields(p):
        value = getattr(p, item.name)
        if isinstance(item.default, str):
            if not isinstance(value, str):
                raise CalculationError(item.name + "必须是文本")
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise CalculationError("%s 必须是有限数字" % item.name)
    for key in ("rw", "rti", "h", "ko", "kd", "kav", "ua", "pHCl", "pr", "oil_viscosity", "oil_volume_factor", "fluid_cp", "rock_cp"):
        _range(getattr(p, key), 0, 1e7, key, True)
    _range(p.o, 0, 0.8, "孔隙度", True)
    _range(p.Rd - p.rw, 0.1, 10, "直井污染深度 Rd-rw")
    if p.re <= max(p.Rd, p.rw + p.max_penetration):
        raise CalculationError("泄油半径必须大于污染半径及最大作用半径")
    _range(p.max_penetration, 0, 2, "最大酸液作用深度(m)", True)
    _range(p.vertical_depth, 0, 15000, "储层垂深", True)
    _range(p.Zh, p.vertical_depth, 50000, "井口至水平段入口测深 Zh")
    _range(p.Zb, 0, p.vertical_depth, "恒温点垂深 Zb")
    for key in ("aT", "heat_transfer_u", "f", "Ps", "V_per_m", "Vh_per_m", "preflush_ratio", "postflush_ratio", "calcium_mg_l", "sodium_mg_l", "potassium_mg_l", "plugging_sensitivity"):
        _range(getattr(p, key), 0, 1e6, key)
    _range(p.alpha, 0, 1, "破裂压力梯度", True)
    _range(p.limit_p, 0, 1000, "井口限压", True)
    if p.well_type not in ("直井", "斜井", "定向井", "水平井"):
        raise CalculationError("井形请选择直井、斜井、定向井或水平井")
    if p.completion_type not in ("射孔完井", "裸眼完井", "筛管完井", "砾石充填"):
        raise CalculationError("完井方式无效")
    _range(p.inclination_deg, 0, 90, "处理段井斜角（相对铅垂线）")
    if p.well_type == "直井" and (abs(p.Zh-p.vertical_depth) > 0.01 or p.inclination_deg != 0):
        raise CalculationError("直井要求测深等于垂深且井斜角为0°")
    if p.well_type == "水平井" and p.inclination_deg < 80:
        raise CalculationError("水平段井斜角应为80–90°，其他井段请选择斜井或定向井")
    _range(p.completion_resistance, 0, 1e6, "筛管/砾石充填附加阻力")
    if p.rti > p.rw:
        raise CalculationError("管柱内半径不能大于井眼半径")
    if p.completion_type == "射孔完井":
        _range(p.Np, 1, 100000, "射孔孔数")
        if p.Np != int(p.Np):
            raise CalculationError("射孔孔数必须为整数")
        _range(p.Dp, 0, 1, "孔眼直径", True)
        _range(p.aM, 0, 1, "孔眼流量系数", True)
    _range(p.Tf, -20, 250, "井口注入温度")
    _range(p.Tb, -20, 250, "恒温点温度")
    _range(formation_temperature(p), -20, 250, "储层温度")
    _range(p.precipitation_enabled, 0, 1, "沉淀开关")
    if p.precipitation_enabled not in (0, 1):
        raise CalculationError("沉淀开关只接受 0 或 1")
    _range(p.precipitation_yield, 0, 2, "沉淀质量系数")
    _range(p.damage_solid_fraction, 0, 0.2, "伤害固相体积分数", True)
    minerals = [p.quartz, p.feldspar, p.clay, p.carbonate, p.other_minerals]
    for value in minerals:
        _range(value, 0, 1, "矿物质量分数")
    if abs(sum(minerals) - 1) > 1e-6:
        raise CalculationError("石英、长石、黏土、碳酸盐及其他矿物质量分数之和必须为 1（当前 %.6f）" % sum(minerals))
    for key in ("water_saturation", "oil_saturation", "gas_saturation", "oil_relative_permeability"):
        _range(getattr(p, key), 0, 1, key)
    if abs(p.water_saturation + p.oil_saturation + p.gas_saturation - 1) > 1e-6:
        raise CalculationError("水、油、气饱和度之和必须为1")
    _range(p.oil_relative_permeability, 0, 1, "油相相对渗透率", True)
    water_analysis(p)


def water_analysis(p):
    """Mass normalization is explicit; it does not repair ionic charge imbalance."""
    ions = {key: getattr(p, key) for key in ("calcium_mg_l", "sodium_mg_l", "potassium_mg_l",
            "magnesium_mg_l", "chloride_mg_l", "sulfate_mg_l", "bicarbonate_mg_l")}
    for key, value in ions.items():
        _range(value, 0, 1e6, key)
    _range(p.salinity_mg_l, 0, 1e6, "实测矿化度")
    total = sum(ions.values())
    if p.water_mode not in ("ions", "normalize_tds"):
        raise CalculationError("地层水模式应为 ions 或 normalize_tds")
    factor = 1.0
    if p.water_mode == "normalize_tds":
        if total <= 0 or p.salinity_mg_l <= 0:
            raise CalculationError("按矿化度归一化需要正的离子总量和实测矿化度")
        factor = p.salinity_mg_l / total
    normalized = {key: value * factor for key, value in ions.items()}
    cations = sum(normalized[k] / equivalent for k, equivalent in
                  (("calcium_mg_l",20.039),("sodium_mg_l",22.990),
                   ("potassium_mg_l",39.098),("magnesium_mg_l",12.1525)))
    anions = sum(normalized[k] / equivalent for k, equivalent in
                 (("chloride_mg_l",35.453),("sulfate_mg_l",48.03),("bicarbonate_mg_l",61.017)))
    balance = 100*(cations-anions)/(cations+anions) if cations+anions else 0.0
    return {"mode": p.water_mode, "measured_tds_mg_l": p.salinity_mg_l,
            "input_ion_sum_mg_l": total, "normalization_factor": factor,
            "used_ions_mg_l": normalized, "charge_balance_error_percent": balance,
            "warnings": (["阴阳离子电荷不平衡超过5%；质量归一化不能修复电荷不平衡"] if abs(balance)>5 else [])}


def validate_acid(acid: AcidSystem):
    for item in fields(acid):
        value = getattr(acid, item.name)
        if isinstance(item.default, str):
            if not isinstance(value, str) or not value.strip():
                raise CalculationError("酸液 %s 不能为空" % item.name)
        else:
            _range(value, 0, 1e6, "酸液 " + item.name)
    for key in ("hcl_fraction", "hf_fraction", "organic_fraction", "preflush_efficiency", "flowback_efficiency"):
        _range(getattr(acid, key), 0, 1, key)
    if acid.hcl_fraction + acid.hf_fraction + acid.organic_fraction > 1:
        raise CalculationError("酸组分质量分数之和不能大于 1")
    for key in ("density", "viscosity", "heat_capacity", "dissolving_capacity", "retardation_factor"):
        _range(getattr(acid, key), 0, 1e6, key, True)
    _range(acid.activation_energy, 0, 150, "活化能(kJ/mol)")
    _range(acid.rate_constant, 0, 100, "参考速率(1/min)")
    _range(acid.reaction_heat, 0, 200, "放热量(kJ/mol 酸)")
    _range(acid.reference_temperature, 0, 250, "参考温度")
    _range(acid.max_temperature, 0, 250, "酸液适用最高温度")
    if acid.reaction_model not in ("arrhenius", "transport_limited"):
        raise CalculationError("反应模型请选择 arrhenius 或 transport_limited")
    _range(acid.mass_transfer_rate, 0, 100, "等效传质速率(1/min)", True)


def segment_depth(row: HorizontalSegment, p: AcidizingParameters) -> float:
    return row.damage_radius - p.rw if row.damage_radius is not None else row.damage_depth


def validate_segments(p, segments, acid_systems):
    if not 1 <= len(segments) <= 100:
        raise CalculationError("水平井分段数量应在 1 到 100 之间")
    previous_end = 0.0
    names = set()
    for row in segments:
        if not row.name.strip() or row.name in names:
            raise CalculationError("分段名称不能为空或重复")
        names.add(row.name)
        _range(row.start_md, previous_end, 100000, row.name + "起点（须按顺序且不重叠）")
        _range(row.end_md, row.start_md, 100000, row.name + "终点", True)
        previous_end = row.end_md
        for key in ("permeability", "damaged_permeability", "contact_time"):
            _range(getattr(row, key), 0, 1e6, row.name + key, True)
        _range(row.porosity, 0, 0.8, row.name + "孔隙度", True)
        _range(segment_depth(row, p), 0.1, 10, row.name + "污染深度")
        if p.rw + segment_depth(row, p) >= p.re:
            raise CalculationError(row.name + "污染半径必须小于泄油半径")
        _range(row.acid_volume, 0, 1e6, row.name + "处理液量")
        _range(row.drilling_exposure_days, 0, 10000, row.name + "钻井液暴露天数")
        if row.acid_system not in acid_systems:
            raise CalculationError("%s：找不到酸液体系 %s" % (row.name, row.acid_system))
        validate_acid(acid_systems[row.acid_system])


def formation_temperature(p):
    return p.Tb + p.aT * (p.vertical_depth - p.Zb)


def wellbore_temperature_profile(p, rate, horizontal_distance=0.0, acid=None):
    """Piecewise-linear formation T along MD; TVD is constant in the lateral.

    Solve dTf/ds = U*2*pi*r/(mass_flow*cp)*(Tformation-Tf) exactly per cell.
    Constant effective U is a user calibration, not Ramey's transient solution.
    """
    _range(rate, 0, 1e6, "温度计算排量", True)
    acid = acid or AcidSystem(density=p.pHCl, heat_capacity=p.fluid_cp)
    _range(horizontal_distance, 0, 100000, "水平段位置")
    mass_flow = acid.density * rate / 60.0
    coefficient = p.heat_transfer_u * 2 * PI * p.rti / (mass_flow * acid.heat_capacity)
    points = [TemperaturePoint(0, 0, p.Tb - p.aT * p.Zb, p.Tf, coefficient * (p.Tb - p.aT * p.Zb - p.Tf))]
    steps = [(p.Zh / 60, p.vertical_depth / 60)] * 60
    if horizontal_distance:
        dz = horizontal_distance * math.cos(math.radians(p.inclination_deg))
        steps += [(horizontal_distance / 30, dz / 30)] * 30
    md, tvd, temp = 0.0, 0.0, p.Tf
    for ds, dz in steps:
        earth0 = p.Tb + p.aT * (tvd - p.Zb)
        gradient = p.aT * dz / ds
        if coefficient > 1e-12:
            decay = math.exp(-coefficient * ds)
            temp = earth0 + gradient * ds - gradient / coefficient + (temp - earth0 + gradient / coefficient) * decay
        md += ds
        tvd += dz
        earth = p.Tb + p.aT * (tvd - p.Zb)
        points.append(TemperaturePoint(md, tvd, earth, temp, coefficient * (earth - temp)))
    return points


def _hydraulics(p, length, permeability, damaged_k, damage_radius, viscosity, density, md):
    skin = (permeability / damaged_k - 1) * math.log(damage_radius / p.rw)
    resistance = math.log(p.re / p.rw) + skin
    # Radial Darcy flow conversion: mD, m, MPa, mPa.s -> m3/min.
    conductance = 3.720e-4 * permeability * length / (viscosity * resistance)
    fracture = p.alpha * p.vertical_depth
    bottom_limit = 0.90 * fracture
    hydrostatic = density * 9.80665 * p.vertical_depth / 1e6
    if min(bottom_limit - p.Ps, p.limit_p + hydrostatic - p.Ps) <= 0:
        raise CalculationError("压力窗口不足：地层压力、90%破裂压力和井口限压不能支持基质注入")
    # Orifice loss with total open area; legacy alpha (fracture gradient) was incorrect here.
    perf_factor = 0.0
    if p.completion_type == "射孔完井":
        area = p.Np * PI * p.Dp ** 2 / 4
        perf_factor = density / (2e6 * (60 * p.aM * area) ** 2)
    linear = 1 / conductance + (p.completion_resistance if p.completion_type in ("筛管完井", "砾石充填") else 0)
    def solve(window, quadratic):
        return 2 * window / (linear + math.sqrt(linear ** 2 + 4 * quadratic * window))
    rate = min(solve(bottom_limit-p.Ps, perf_factor),
               solve(p.limit_p+hydrostatic-p.Ps, perf_factor+p.f*md))
    # f is the calibrated tubing gradient at reference rate 1 m3/min.
    surface_limit = min(p.limit_p, bottom_limit - hydrostatic + p.f * md * rate ** 2)
    return skin, fracture, surface_limit, rate


def calculate_basic(p: AcidizingParameters) -> BasicResults:
    validate_parameters(p)
    skin, fracture, limit, rate = _hydraulics(p, p.h, p.ko, p.kd, p.Rd, p.ua, p.pHCl, p.Zh)
    treatment = p.h * p.V_per_m
    preflush = treatment * p.preflush_ratio
    postflush = p.h * p.Vh_per_m
    displacement = PI * p.rti ** 2 * p.Zh
    return BasicResults(skin, limit, rate, .9 * rate, preflush, treatment, postflush,
                        displacement, preflush + treatment + postflush + displacement, fracture)


def _arrhenius(acid, temperature):
    exponent = acid.activation_energy * 1000 / 8.314462618 * (1 / (acid.reference_temperature + 273.15) - 1 / (temperature + 273.15))
    chemical = acid.rate_constant * acid.retardation_factor * math.exp(min(exponent, 50))
    if acid.reaction_model == "transport_limited":
        return chemical * acid.mass_transfer_rate / (chemical + acid.mass_transfer_rate)
    return chemical


def react(p, acid, volume, duration, bulk_volume, porosity, k0, kd, inlet_temperature,
          available_silicate=None, available_carbonate=None):
    """Lumped mass-limited acid consumption + adiabatic rock/fluid heat balance.

    Mineral fractions and all calibration closures are documented in MODEL_NOTES.
    HCl/organic carbonate capacity and HF silicate capacity are separate budgets.
    No claim of equilibrium species / saturation-index resolution is made.
    """
    used = water_analysis(p)["used_ions_mg_l"]
    p = replace(p, **used, water_mode="ions")
    rock_mass = bulk_volume * (1 - porosity) * p.pr * 1000
    fluid_mass = volume * acid.density
    heat_capacity = fluid_mass * acid.heat_capacity + rock_mass * p.rock_cp
    earth = formation_temperature(p)
    temp = ((fluid_mass * acid.heat_capacity * inlet_temperature + rock_mass * p.rock_cp * earth)
            / heat_capacity if heat_capacity else inlet_temperature)
    initial_temp = temp
    silicate = p.quartz + p.feldspar + p.clay
    hf_initial = fluid_mass * acid.hf_fraction
    hcl_initial = fluid_mass * acid.hcl_fraction
    organic_initial = fluid_mass * acid.organic_fraction
    pools = [hf_initial, hcl_initial, organic_initial]
    remaining_silicate = rock_mass * silicate
    remaining_carbonate = rock_mass * p.carbonate
    if available_silicate is not None:
        remaining_silicate = min(remaining_silicate, available_silicate)
    if available_carbonate is not None:
        remaining_carbonate = min(remaining_carbonate, available_carbonate)
    dissolved_silicate = dissolved_carbonate = 0.0
    rates = []
    dt = duration / 120.0
    # Relative reactivities are illustrative calibration weights, not constants from papers.
    hf_weight = (0.02 * p.quartz + 0.6 * p.feldspar + p.clay) * (1 + 2 * acid.hcl_fraction)
    carbonate_weight = 4 * p.carbonate
    for _ in range(120):
        rate = _arrhenius(acid, temp)
        rates.append(rate * max(hf_weight if hf_initial else 0, carbonate_weight if hcl_initial + organic_initial else 0))
        consumed_hf = min(pools[0] * (-math.expm1(-rate * hf_weight * dt)), remaining_silicate / acid.dissolving_capacity)
        consumed_hcl = min(pools[1] * (-math.expm1(-rate * carbonate_weight * dt)), remaining_carbonate / 1.372)
        # Acetic-acid equivalent: CaCO3 / (2 CH3COOH) = 0.833 kg/kg.
        consumed_organic = min(pools[2] * (-math.expm1(-0.5 * rate * carbonate_weight * dt)), max(0, remaining_carbonate - consumed_hcl * 1.372) / .833)
        consumed = [consumed_hf, consumed_hcl, consumed_organic]
        pools = [max(0, a - b) for a, b in zip(pools, consumed)]
        ds = consumed_hf * acid.dissolving_capacity
        dc = consumed_hcl * 1.372 + consumed_organic * .833
        dissolved_silicate += ds
        dissolved_carbonate += dc
        remaining_silicate = max(0, remaining_silicate - ds)
        remaining_carbonate = max(0, remaining_carbonate - dc)
        moles = consumed_hf / .020006 + consumed_hcl / .03646 + consumed_organic / .06005
        temp += moles * acid.reaction_heat * 1000 / heat_capacity if heat_capacity else 0
    total_acid = hf_initial + hcl_initial + organic_initial
    remaining = sum(pools) / total_acid if total_acid else 1.0
    # Proxy only: calcium/alkali availability + aluminosilicates + acid spending.
    # Preflush effectiveness scales with planned preflush volume; no free protection at zero volume.
    protection = acid.preflush_efficiency * (1 - math.exp(-p.preflush_ratio / .25))
    calcium = p.calcium_mg_l + dissolved_carbonate * .4004 / max(volume, 1e-12) * 1000
    ionic = .6 * calcium / (calcium + 1000) + .25 * p.sodium_mg_l / (p.sodium_mg_l + 5000) + .15 * p.potassium_mg_l / (p.potassium_mg_l + 200)
    risk = min(1.0, (ionic + .4 * (p.feldspar + p.clay)) * (1 - protection) * (1 + .5 * (1 - remaining))) if hf_initial else 0.0
    flushing = acid.flowback_efficiency * (1 - math.exp(-p.postflush_ratio / .2))
    precipitate = dissolved_silicate * p.precipitation_yield * risk * (1 - flushing) if p.precipitation_enabled else 0.0
    dissolved = dissolved_silicate + dissolved_carbonate
    mineral_density = p.pr * 1000
    phi_clean = min(.8, porosity + dissolved / max(bulk_volume * mineral_density, 1e-12))
    phi_after = max(.001, phi_clean - precipitate / max(bulk_volume * mineral_density, 1e-12))
    removal = -math.expm1(-dissolved / max(bulk_volume * mineral_density * p.damage_solid_fraction, 1e-12))
    restored = kd + (k0 - kd) * removal
    kc = (phi_clean / porosity) ** 3 * ((1 - porosity) / (1 - phi_clean)) ** 2
    clean_k = restored * kc
    clog = p.plugging_sensitivity * precipitate / max(bulk_volume * porosity * mineral_density, 1e-12)
    final_k = max(kd * 1e-6, clean_k * math.exp(-min(clog, 50)))
    notes = []
    if max(earth, temp) > acid.max_temperature:
        notes.append("温度超过该酸液标注的适用上限 %.0f℃" % acid.max_temperature)
    if max(earth, temp) >= 100:
        notes.append("高温条件：需复核酸耗、腐蚀、颗粒迁移与二次沉淀实验")
    if final_k < kd:
        notes.append("预测净渗透率低于处理前，存在酸化负效应")
    if phi_clean >= .8:
        notes.append("溶蚀预测触及孔隙度上限，当前体积/反应系数需校核")
    return ReactionResult(remaining, dissolved, dissolved / rock_mass if rock_mass else 0,
                          precipitate, risk, temp, temp - initial_temp,
                          sum(rates) / len(rates), phi_after, final_k, clean_k, notes,
                          dissolved_silicate, dissolved_carbonate)


def _treatment(p, acid, volume, duration, length, porosity, k0, kd, inlet):
    if volume == 0 or acid.hf_fraction + acid.hcl_fraction + acid.organic_fraction == 0 or acid.rate_constant == 0:
        reaction = ReactionResult(1, 0, 0, 0, 0, inlet, 0, 0, porosity, kd, kd, [])
        return p.rw, reaction
    hydraulic_radius = math.sqrt(p.rw ** 2 + volume / (PI * length * porosity))
    radius = min(p.rw + p.max_penetration, hydraulic_radius)
    bulk = PI * (radius ** 2 - p.rw ** 2) * length
    first = react(p, acid, volume, duration, bulk, porosity, k0, kd, inlet)
    # First-order survival cutoff C/C0=0.1 -> residence time ln(10)/k.
    reachable_volume = min(volume, volume / duration * math.log(10) / max(first.average_rate, 1e-12))
    radius = min(radius, math.sqrt(p.rw ** 2 + reachable_volume / (PI * length * porosity)))
    bulk = PI * (radius ** 2 - p.rw ** 2) * length
    reaction = react(p, acid, volume, duration, bulk, porosity, k0, kd, inlet)
    if reaction.dissolved_rock_kg <= 1e-12:
        return p.rw, reaction
    return radius, reaction


def _indices(p, length, k0, kd, damage_radius, treated_radius, treated_k):
    log_base = math.log(p.re / p.rw)
    skin_before = (k0 / kd - 1) * math.log(damage_radius / p.rw)
    before_den = log_base + skin_before
    # Integrate concentric zones exactly, rather than summing resistance over time.
    treatment_end = min(treated_radius, damage_radius)
    resistance = math.log(max(treatment_end, p.rw) / p.rw) / treated_k
    resistance += math.log(damage_radius / max(treatment_end, p.rw)) / kd
    if treated_radius > damage_radius:
        resistance += math.log(treated_radius / damage_radius) / treated_k
    resistance += math.log(p.re / max(damage_radius, treated_radius)) / k0
    after_den = k0 * resistance
    # Steady single-phase radial PI (m3/day/MPa), common pressure and fluid assumptions.
    factor = 0.5357 * k0 * length * p.oil_relative_permeability / (p.oil_viscosity * p.oil_volume_factor)
    return skin_before, after_den - log_base, factor / log_base, factor / before_den, factor / after_den


def run_simulation(p: AcidizingParameters, acid: Optional[AcidSystem] = None) -> SimulationResult:
    basic = calculate_basic(p)
    acid = acid or AcidSystem(hcl_fraction=p.CHCl, hf_fraction=p.Coo, density=p.pHCl,
                             viscosity=p.ua, heat_capacity=p.fluid_cp)
    validate_acid(acid)
    _, fracture, limit, rate = _hydraulics(p, p.h, p.ko, p.kd, p.Rd, acid.viscosity, acid.density, p.Zh)
    basic = replace(basic, max_rate=rate, construction_rate=.9 * rate,
                    fracture_pressure=limit, formation_fracture_pressure=fracture)
    temps = wellbore_temperature_profile(p, basic.construction_rate, acid=acid)
    duration = basic.treatment_volume / basic.construction_rate
    radius, reaction = _treatment(p, acid, basic.treatment_volume, duration, p.h, p.o, p.ko, p.kd, temps[-1].fluid_temperature)
    profile, productivity = [], []
    if duration > 0:
        # Snapshots are independently evaluated at cumulative injection volume.
        for i in range(1, 25):
            fraction = i / 24.0
            r, rx = _treatment(p, acid, basic.treatment_volume * fraction, duration * fraction,
                               p.h, p.o, p.ko, p.kd, temps[-1].fluid_temperature)
            _, _, _, jd, ja = _indices(p, p.h, p.ko, p.kd, p.Rd, r, rx.permeability_after)
            profile.append(ProfileRow(duration * fraction, r, rx.acid_remaining_fraction,
                                      1 - rx.dissolution_fraction, rx.porosity_after,
                                      rx.permeability_after, rx.temperature))
            productivity.append(ProductivityRow(duration * fraction, r, ja / jd))
    notes = ["简化筛选模型；酸液默认动力学、放热和沉淀系数需岩心实验标定。",
             "2 m 为本项目的井壁外作用深度上限，并非所有储层的普适常数。"] + reaction.warnings
    return SimulationResult(basic, radius, profile, productivity, notes, temps, reaction)


def simulate_profile(params, basic=None):
    result = run_simulation(params)
    return result.profile_rows, result.effective_radius, result.warnings


def calculate_productivity_rows(params, basic=None, effective_radius=None):
    return run_simulation(params).productivity_rows


def build_default_segments(params, total_length=1000.0, count=30, mode="均质"):
    _range(total_length, 0, 100000, "水平段长度", True)
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 100:
        raise CalculationError("分段数量应为 1 到 100 的整数")
    if mode not in ("均质", "非均质"):
        raise CalculationError("储层模式须为均质或非均质")
    length = total_length / count
    result = []
    for index in range(count):
        heel = 1 - index / max(count - 1, 1)
        k = params.ko if mode == "均质" else max(.01, params.ko * (.8 + .3 * math.sin(index * 1.47)))
        kd = params.kd if mode == "均质" else k * (.25 + .25 * (1 - heel))
        result.append(HorizontalSegment("第%d段" % (index + 1), index * length, (index + 1) * length,
                                        k, kd, porosity=params.o, damage_depth=1.0,
                                        drilling_exposure_days=1 + 19 * heel))
    return result


def evaluate_horizontal_section(p, segments, base_result=None, acid_systems=None):
    validate_parameters(p)
    acid_systems = acid_systems if acid_systems is not None else default_acid_systems()
    validate_segments(p, segments, acid_systems)
    evaluations = []
    total_length = sum(s.end_md - s.start_md for s in segments)
    mean_k = sum(s.permeability * (s.end_md - s.start_md) for s in segments) / total_length
    variance = sum((s.permeability - mean_k) ** 2 * (s.end_md - s.start_md) for s in segments) / total_length
    cv = math.sqrt(variance) / mean_k
    for row in segments:
        acid = acid_systems[row.acid_system]
        length = row.end_md - row.start_md
        depth = segment_depth(row, p)
        md = p.Zh + (row.start_md + row.end_md) / 2
        _, _, surface_limit, allowed = _hydraulics(p, length, row.permeability, row.damaged_permeability,
                                       p.rw + depth, acid.viscosity, acid.density, md)
        required_rate = row.acid_volume / row.contact_time
        temps = wellbore_temperature_profile(p, required_rate or .9 * allowed, (row.start_md + row.end_md) / 2, acid)
        inlet = temps[-1].fluid_temperature
        radius, reaction = _treatment(p, acid, row.acid_volume, row.contact_time, length,
                                      row.porosity, row.permeability, row.damaged_permeability, inlet)
        sb, sa, j0, jd, ja = _indices(p, length, row.permeability, row.damaged_permeability,
                                     p.rw + depth, radius, reaction.permeability_after)
        coverage = min(1.0, max(0.0, (radius - p.rw) / depth))
        ratio = ja / jd
        notes = list(reaction.warnings)
        if depth > p.max_penetration:
            notes.append("污染深度大于作用上限，增加酸量也不能保证全部解除")
        if required_rate > .9 * allowed:
            notes.append("输入酸量/接触时间所需排量超过该段建议排量；须延长时间后重算")
        if row.acid_volume == 0:
            notes.append("本段未注入处理液，产能保持处理前值")
        if row.damaged_permeability > row.permeability:
            notes.append("输入污染渗透率高于原始值，请核对是否为已改造井段")
        if ratio < 1 or required_rate > .9 * allowed or coverage < .72 or max(formation_temperature(p), reaction.temperature) > acid.max_temperature:
            status = "高风险"
        elif coverage >= .99 and ratio >= 1.12:
            status = "有效"
        else:
            status = "可改善"
        recommendation = "；".join(notes) if notes else "按该段配方和用量设计，结合岩心实验校准后复核"
        volumes = {"preflush": row.acid_volume * p.preflush_ratio, "treatment": row.acid_volume,
                   "postflush": row.acid_volume * p.postflush_ratio, "displacement": 0.0}
        evaluations.append(SegmentEvaluation(row.name, row.start_md, row.end_md, length, sb,
                            row.acid_volume, radius, coverage, sa, ratio,
                            65 * coverage + 35 * min(max((ratio - 1) / .35, 0), 1), status,
                            recommendation, depth, radius - p.rw, acid.name, j0, jd, ja, ja / j0,
                            inlet, reaction, volumes, temps, required_rate, .9 * allowed, surface_limit,
                            sum(volumes.values()) / (.9 * allowed), notes))
    # One final common-tubing displacement, not one whole-well volume per segment.
    displacement = PI * p.rti ** 2 * (p.Zh + segments[-1].end_md) if any(s.acid_volume for s in segments) else 0.0
    volumes = {key: sum(s.stage_volumes[key] for s in evaluations) for key in ("preflush", "treatment", "postflush", "displacement")}
    volumes["displacement"] = displacement
    j0 = sum(s.productivity_undamaged for s in evaluations)
    jd = sum(s.productivity_damaged for s in evaluations)
    ja = sum(s.productivity_after for s in evaluations)
    coverage = sum(s.coverage_ratio * s.length for s in evaluations) / total_length
    risks = sum(s.status == "高风险" for s in evaluations)
    conclusions = ["%d 段，处理液合计 %.2f m³，全部施工液 %.2f m³。" % (len(segments), volumes["treatment"], sum(volumes.values())),
                   "长度加权污染覆盖率 %.1f%%；全井 J后/J污染=%.3f（先合计各段产能指数再求比）。" % (coverage * 100, ja / jd),
                   "J原始=%.3f，J污染=%.3f，J处理后=%.3f m³/(d·MPa)。" % (j0, jd, ja),
                   "产能按共用压差、无段间干扰的单相径向近似；未解析水平井三维流动。",
                   "作用深度从井壁起算，上限 %.2f m；钻井暴露天数仅作记录，污染深度须独立解释。" % p.max_penetration,
                   "放热采用集总绝热估算，沉淀采用风险代理系数；默认值未经本储层实验标定。"]
    if risks:
        conclusions.append("高风险 %d 段：%s。" % (risks, "、".join(s.name for s in evaluations if s.status == "高风险")))
    if cv >= .25:
        conclusions.append("渗透率非均质性较强，需复核分段封隔及转向效果。")
    return HorizontalEvaluation(MODEL_VERSION, "非均质" if cv >= .25 else "近似均质", total_length,
                                cv, coverage, ja / jd, risks, evaluations, conclusions,
                                volumes["treatment"], volumes, sum(volumes.values()), j0, jd, ja)


def optimize_radius(p, min_radius, max_radius, step, economics, acid=None):
    validate_parameters(p)
    _range(min_radius, p.rw, p.rw + p.max_penetration, "最小目标半径", True)
    _range(max_radius, min_radius, p.rw + p.max_penetration, "最大目标半径")
    _range(step, 0, 10, "半径步长", True)
    for item in fields(economics):
        _range(getattr(economics, item.name), 0, 1e12, item.name)
    count = int(math.floor((max_radius - min_radius) / step + 1e-9)) + 1
    if count > 200:
        raise CalculationError("优化方案超过 200 个，请增大步长")
    rows = []
    for i in range(count):
        target = min_radius + i * step
        # Sweep injected pore volume for a fixed damage radius (do not change damage itself).
        volume = PI * (target ** 2 - p.rw ** 2) * p.h * p.o
        scenario = replace(p, V_per_m=volume / p.h, Vh_per_m=volume / p.h * p.postflush_ratio)
        result = run_simulation(scenario, acid)
        ratio = result.productivity_rows[-1].productivity_ratio if result.productivity_rows else 1.0
        revenue = (ratio - 1) * economics.base_daily_income * economics.effective_days
        cost = result.basic.total_acid_volume * economics.acid_unit_cost
        rows.append(RadiusScenario(target, result.effective_radius, ratio, result.basic.total_acid_volume,
                                   revenue, cost, revenue - cost))
    return rows


