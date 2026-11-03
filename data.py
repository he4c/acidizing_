from dataclasses import dataclass
from typing import Optional

# Field metadata below is also used by the acid-system editor.
ACID_FIELD_LABELS = {
    "name": "体系名称", "preflush_type": "前置液类型", "preflush_formula": "前置液配方",
    "treatment_type": "处理液类型", "treatment_formula": "处理液配方（与下方数值核对）",
    "postflush_type": "后置液类型", "postflush_formula": "后置液配方",
    "displacement_type": "顶替液类型", "displacement_formula": "顶替液配方",
    "hcl_fraction": "处理液 HCl 质量分数 (0–1)", "hf_fraction": "处理液 HF 质量分数 (0–1)",
    "organic_fraction": "处理液有机酸质量分数 (乙酸当量)", "density": "密度 (kg/m³)",
    "viscosity": "黏度 (mPa·s)", "heat_capacity": "比热 (J/kg/K)",
    "reference_temperature": "参考温度 (℃)", "rate_constant": "参考集总速率 (1/min，需标定)",
    "activation_energy": "表观活化能 (kJ/mol，需标定)", "reaction_heat": "放热量 (kJ/mol 酸，需标定)",
    "dissolving_capacity": "HF 溶蚀能力 (kg岩石/kg HF)", "retardation_factor": "缓速因子 (>0，1为不缓速)",
    "preflush_efficiency": "前置液最大有效系数 (0–1)", "flowback_efficiency": "后置液最大携出系数 (0–1)",
    "max_temperature": "实验支持的最高温度 (℃)", "calibration_note": "实验/文献/标定依据（必填）",
}


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    unit: str
    default: str


@dataclass(frozen=True)
class StageSpec:
    key: str
    label: str
    fluid_type: str
    concentration: str
    volume_key: Optional[str] = None
    volume_default: str = ""


WELL_FIELDS = [
    FieldSpec("rw", "井筒半径 rw", "m", "0.05221"),
    FieldSpec("Np", "射孔孔数 Np", "个", "250"),
    FieldSpec("Dp", "射孔孔眼直径 Dp", "m", "0.012"),
    FieldSpec("aM", "孔眼流量系数 αM", "-", "0.82"),
    FieldSpec("rti", "油管内半径 rti", "m", "0.033755"),
    FieldSpec("dti", "油管外半径 dti", "m", "0.0366"),
    FieldSpec("dce", "套管外径 rce", "m", "0.0889"),
    FieldSpec("Xt", "油管壁厚 Xt", "m", "0.00551"),
    FieldSpec("Xc", "套管壁厚 Xc", "m", "0.00587"),
    FieldSpec("Xan", "环空厚度 Xan", "m", "0.04643"),
    FieldSpec("Tb", "恒温点温度 Tb", "℃", "25"),
    FieldSpec("Zb", "恒温点深度 Zb", "m", "20"),
    FieldSpec("aT", "地温梯度 αT", "℃/m", "0.02"),
    FieldSpec("Khs", "钢材导热系数 Khs", "kcal/(m.min.℃)", "0.62"),
    FieldSpec("h", "产层厚度 H", "m", "17.5"),
    FieldSpec("re", "泄油半径 Re", "m", "200"),
    FieldSpec("Zh", "井深 Zh", "m", "4969"),
    FieldSpec("Ps", "地层压力 Ps", "MPa", "47.1062"),
    FieldSpec("alpha", "破裂压力梯度 α", "MPa/m", "0.029"),
]


RESERVOIR_FIELDS = [
    FieldSpec("kav", "地层平均渗透率 kav", "mD", "36.12"),
    FieldSpec("o", "初始孔隙度 Φ0", "-", "0.145"),
    FieldSpec("ko", "初始渗透率 k0", "10^-3 μm2", "36.12"),
    FieldSpec("Rd", "伤害带半径 Rd", "m", "1"),
    FieldSpec("kd", "伤害带渗透率 Kd", "10^-3 μm2", "12.3"),
    FieldSpec("lambd", "地层导热系数 λ", "kcal/(m.min.℃)", "0.03467"),
    FieldSpec("limit_p", "施工限压", "MPa", "70"),
    FieldSpec("CMo", "初始矿物浓度 CM0", "mol/cm3", "0.00458438"),
    FieldSpec("CMi", "残余矿物浓度 CMi", "mol/cm3", "0.00196474"),
    FieldSpec("pr", "矿物密度 ρr", "g/cm3", "2.6"),
    FieldSpec("Wr", "矿物摩尔重量 Wr", "g/mol", "397"),
    FieldSpec("pCaCO3", "碳酸盐岩密度 ρCaCO3", "g/cm3", "2.7"),
]


FLUID_FIELDS = [
    FieldSpec("CM", "盐酸可溶物百分浓度 CM", "-", "0.03"),
    FieldSpec("Xhcl", "盐酸体积溶解能力 XHCl", "-", "0.053"),
    FieldSpec("ua", "酸液粘度 μa", "MPa.s", "0.8"),
    FieldSpec("f", "摩阻系数 f", "-", "0.003"),
    FieldSpec("C", "液体比热 C", "kcal/(kg.℃)", "1"),
    FieldSpec("pHCl", "盐酸密度 ρHCl", "kg/m3", "1017.4"),
    FieldSpec("CHCl", "盐酸百分浓度 CHCl", "-", "0.1"),
    FieldSpec("T0", "试验温度 T0", "℃", "25"),
    FieldSpec("kro", "T0 反应速度常数 Kr0", "-", "0.532"),
    FieldSpec("Coo", "初始酸浓度(HF) C00", "mol/m3", "0.015"),
    FieldSpec("Ea", "反应活化能 Ea", "kcal", "4"),
    FieldSpec("omega", "化学计量系数 ω", "molHF/molrock", "22.64"),
    FieldSpec("Khan", "环空液导热系数 Khan", "kcal/(m.min.℃)", "0.00384"),
    FieldSpec("R", "气体常数 R", "kcal/(mol.K)", "1.987"),
]


STAGE_SPECS = [
    StageSpec("preflush", "前置液", "HCl+HAC", "10%HCl、3%HAC"),
    StageSpec("treatment", "处理液", "HCl+HF+HAC", "10%HCl、1.5%HF、3%HAC", "V_per_m", "1.7"),
    StageSpec("postflush", "后置液", "HCl+HAC", "10%HCl、3%HAC", "Vh_per_m", "1"),
    StageSpec("displacement", "顶替液", "清水", "/"),
]


LITHOLOGY_LIBRARY = {
    "自定义": {
        "description": "不覆盖当前参数，适合手动录入实测岩心和矿物组分数据。",
        "values": {},
    },
    "湛江常见石英砂岩": {
        "description": "以石英为主，长石和黏土矿物含量较低，适合常规土酸体系初算。",
        "values": {
            "o": 0.145,
            "kav": 36.12,
            "ko": 36.12,
            "Rd": 1.0,
            "kd": 12.3,
            "CMo": 0.00458438,
            "CMi": 0.00196474,
            "pr": 2.60,
            "Wr": 397,
            "pCaCO3": 2.70,
        },
    },
    "湛江长石质砂岩": {
        "description": "长石和黏土矿物含量偏高，酸岩反应更敏感，适合降低HF浓度后校核。",
        "values": {
            "o": 0.130,
            "kav": 28.0,
            "ko": 28.0,
            "Rd": 1.2,
            "kd": 9.5,
            "CMo": 0.00520000,
            "CMi": 0.00210000,
            "pr": 2.62,
            "Wr": 390,
            "pCaCO3": 2.70,
        },
    },
    "碳酸盐胶结砂岩": {
        "description": "碳酸盐胶结物较多，前置液消耗量和缓速体系需要重点校核。",
        "values": {
            "o": 0.120,
            "kav": 22.0,
            "ko": 22.0,
            "Rd": 1.0,
            "kd": 8.0,
            "CMo": 0.00600000,
            "CMi": 0.00250000,
            "pr": 2.65,
            "Wr": 397,
            "pCaCO3": 2.71,
        },
    },
}


ACID_SYSTEM_LIBRARY = {
    "自定义": {
        "description": "不覆盖当前参数，适合手动录入实验酸液和动力学参数。",
        "fluid": {},
        "stages": {},
    },
    "常规土酸 10%HCl+1.5%HF+3%HAC": {
        "description": "常规砂岩酸化体系，用于基础解堵和半径优化初算。",
        "fluid": {
            "CM": 0.03,
            "Xhcl": 0.053,
            "ua": 0.8,
            "f": 0.003,
            "C": 1.0,
            "pHCl": 1017.4,
            "CHCl": 0.10,
            "T0": 25,
            "kro": 0.532,
            "Coo": 0.015,
            "Ea": 4.0,
            "omega": 22.64,
            "Khan": 0.00384,
            "R": 1.987,
        },
        "stages": {
            "preflush": ("HCl+HAC", "10%HCl、3%HAC"),
            "treatment": ("HCl+HF+HAC", "10%HCl、1.5%HF、3%HAC"),
            "postflush": ("HCl+HAC", "10%HCl、3%HAC"),
            "displacement": ("清水", "/"),
            "V_per_m": 1.7,
            "Vh_per_m": 1.0,
        },
    },
    "低浓度土酸 8%HCl+1%HF": {
        "description": "适合长石和黏土敏感储层，用于降低二次沉淀风险的对比方案。",
        "fluid": {
            "CM": 0.025,
            "Xhcl": 0.048,
            "ua": 0.9,
            "f": 0.0035,
            "C": 1.0,
            "pHCl": 1008.0,
            "CHCl": 0.08,
            "T0": 25,
            "kro": 0.420,
            "Coo": 0.010,
            "Ea": 4.2,
            "omega": 22.64,
            "Khan": 0.00370,
            "R": 1.987,
        },
        "stages": {
            "preflush": ("HCl+HAC", "8%HCl、3%HAC"),
            "treatment": ("HCl+HF", "8%HCl、1%HF"),
            "postflush": ("HCl+HAC", "8%HCl、3%HAC"),
            "displacement": ("清水", "/"),
            "V_per_m": 1.5,
            "Vh_per_m": 0.9,
        },
    },
    "有机酸缓速体系": {
        "description": "用于高温或反应过快场景，反应速度常数较低，适合深部作用半径对比。",
        "fluid": {
            "CM": 0.020,
            "Xhcl": 0.040,
            "ua": 1.2,
            "f": 0.0040,
            "C": 1.0,
            "pHCl": 1030.0,
            "CHCl": 0.06,
            "T0": 25,
            "kro": 0.260,
            "Coo": 0.008,
            "Ea": 4.8,
            "omega": 22.64,
            "Khan": 0.00360,
            "R": 1.987,
        },
        "stages": {
            "preflush": ("HCl+HAC", "6%HCl、5%有机酸"),
            "treatment": ("有机酸+低浓度HF", "有机酸、0.8%HF"),
            "postflush": ("HAC", "5%有机酸"),
            "displacement": ("清水", "/"),
            "V_per_m": 1.9,
            "Vh_per_m": 1.1,
        },
    },
}


# v3 active forms. Historic field/library names above remain import-compatible.
WELL_FIELDS = [
    FieldSpec("rw", "井筒半径", "m", "0.05221"),
    FieldSpec("rti", "油管内半径", "m", "0.033755"),
    FieldSpec("Zh", "处理段底部测深（水平井填入口）", "m", "4969"),
    FieldSpec("vertical_depth", "储层垂深", "m", "3000"),
    FieldSpec("Tb", "恒温点温度", "℃", "25"),
    FieldSpec("Zb", "恒温点垂深", "m", "20"),
    FieldSpec("aT", "垂向地温梯度", "℃/m", "0.02"),
    FieldSpec("Tf", "井口注入温度", "℃", "20"),
    FieldSpec("heat_transfer_u", "井筒有效传热系数", "W/m²/K", "12"),
    FieldSpec("h", "直井参考产层厚度", "m", "17.5"),
    FieldSpec("re", "泄油半径", "m", "200"),
    FieldSpec("Ps", "地层压力", "MPa", "47.1062"),
    FieldSpec("alpha", "破裂压力梯度", "MPa/m", "0.029"),
    FieldSpec("limit_p", "井口施工限压", "MPa", "70"),
    FieldSpec("Np", "有效射孔孔数", "个", "250"),
    FieldSpec("Dp", "孔眼直径", "m", "0.012"),
    FieldSpec("aM", "孔眼流量系数", "0–1", "0.82"),
    FieldSpec("f", "1m³/min参考排量下的摩阻梯度", "MPa/m", "0.003"),
    FieldSpec("well_type", "井形", "", "水平井"),
    FieldSpec("completion_type", "完井方式", "", "射孔完井"),
    FieldSpec("inclination_deg", "处理段井斜角（相对铅垂线）", "°", "90"),
    FieldSpec("completion_resistance", "筛管/砾石附加阻力", "MPa/(m³/min)", "0"),
]
RESERVOIR_FIELDS = [
    FieldSpec("ko", "原始渗透率", "mD", "36.12"),
    FieldSpec("kd", "污染渗透率", "mD", "12.3"),
    FieldSpec("kav", "参考平均渗透率（兼容字段）", "mD", "36.12"),
    FieldSpec("o", "孔隙度", "0–1", "0.145"),
    FieldSpec("Rd", "直井污染半径（井轴起算）", "m", "1.05221"),
    FieldSpec("max_penetration", "井壁外最大作用深度", "≤2 m", "2"),
    FieldSpec("pr", "岩石颗粒密度", "g/cm³", "2.6"),
    FieldSpec("rock_cp", "岩石比热", "J/kg/K", "850"),
    FieldSpec("oil_viscosity", "产出流体黏度", "mPa·s", "2"),
    FieldSpec("oil_volume_factor", "产出流体体积系数", "-", "1.1"),
    FieldSpec("damage_solid_fraction", "等效伤害固相体积分数", "需标定", "0.005"),
    FieldSpec("water_saturation", "含水饱和度", "0–1", "0.3"),
    FieldSpec("oil_saturation", "含油饱和度", "0–1", "0.7"),
    FieldSpec("gas_saturation", "含气饱和度", "0–1", "0"),
    FieldSpec("oil_relative_permeability", "油相相对渗透率（实验输入）", "0–1", "1"),
]
MINERAL_FIELDS = [
    FieldSpec("quartz", "石英（SiO₂）质量分数", "0–1", "0.70"),
    FieldSpec("feldspar", "长石（铝硅酸盐）质量分数", "0–1", "0.15"),
    FieldSpec("clay", "黏土矿物质量分数", "0–1", "0.10"),
    FieldSpec("carbonate", "碳酸盐（CaCO₃当量）质量分数", "0–1", "0.03"),
    FieldSpec("other_minerals", "其他矿物（按惰性）质量分数", "0–1", "0.02"),
    FieldSpec("calcium_mg_l", "地层水 Ca²⁺", "mg/L", "1000"),
    FieldSpec("sodium_mg_l", "地层水 Na⁺", "mg/L", "5000"),
    FieldSpec("potassium_mg_l", "地层水 K⁺", "mg/L", "200"),
    FieldSpec("magnesium_mg_l", "地层水 Mg²⁺", "mg/L", "200"),
    FieldSpec("chloride_mg_l", "地层水 Cl⁻", "mg/L", "10000"),
    FieldSpec("sulfate_mg_l", "地层水 SO₄²⁻", "mg/L", "200"),
    FieldSpec("bicarbonate_mg_l", "地层水 HCO₃⁻", "mg/L", "300"),
    FieldSpec("salinity_mg_l", "实测矿化度", "mg/L", "16000"),
    FieldSpec("water_mode", "地层水处理：ions仅离子/normalize_tds归一化", "", "ions"),
    FieldSpec("precipitation_enabled", "考虑二次沉淀（1开/0关）", "0 或 1", "1"),
    FieldSpec("precipitation_yield", "沉淀质量系数", "需标定", "0.6"),
    FieldSpec("plugging_sensitivity", "孔喉堵塞敏感系数", "需标定", "30"),
]
FLUID_FIELDS = [
    FieldSpec("preflush_ratio", "每段前置液/处理液体积比", "m³/m³", "0.25"),
    FieldSpec("postflush_ratio", "每段后置液/处理液体积比", "m³/m³", "0.20"),
]

ACID_FIELD_LABELS.update({"reaction_model":"反应模型：arrhenius动力学 / transport_limited动力学与传质串联",
                         "mass_transfer_rate":"等效传质速率（1/min，需岩心标定）"})

PARAMETER_CHOICES = {"well_type":("直井","斜井","定向井","水平井"),
    "completion_type":("射孔完井","裸眼完井","筛管完井","砾石充填"),
    "water_mode":("ions","normalize_tds")}
