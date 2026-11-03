"""Portable CSV/JSON and printable HTML reports; no Office dependency."""
from __future__ import annotations
import csv
import html
import json
from datetime import datetime
from dataclasses import asdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "acidizing_outputs"

REFERENCES = [
    ("Ramey, 1962. Wellbore Heat Transmission", "https://doi.org/10.2118/96-PA"),
    ("Li et al., 2016. Kinetic mechanics of the reactions between HCl/HF acid mixtures and sandstone minerals", "https://doi.org/10.1016/j.jngse.2016.07.044"),
    ("Wang et al., 2020. Study on reservoir damage during acidizing for high-temperature and ultra-deep tight sandstone", "https://doi.org/10.1016/j.petrol.2020.107231"),
    ("Portier & Vuataz, 2010. Developing the ability to model acid-rock interactions and mineral dissolution...", "https://doi.org/10.1016/j.crte.2010.04.002"),
]


def _cell(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, allow_nan=False)
    # Text originating from user names/formulae should not become spreadsheet formulas.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _write_csv(path, headers, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow([_cell(x) for x in headers])
        writer.writerows([_cell(x) for x in row] for row in rows)
    return path


def _records_csv(path, records):
    records = list(records)
    keys = list(records[0]) if records else []
    return _write_csv(path, keys, ([r.get(k, "") for k in keys] for r in records))


def _folder(prefix):
    folder = OUTPUT_DIR / (prefix + "_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def export_inputs(params, stage_rows, segments=None, payload=None):
    folder = _folder("输入")
    _write_csv(folder / "工程参数.csv", ["参数", "数值"], asdict(params).items())
    _records_csv(folder / "直井参考阶段.csv", stage_rows)
    _records_csv(folder / "水平段输入.csv", (asdict(s) for s in (segments or [])))
    if payload:
        from .model_api import save_request
        save_request(str(folder / "完整方案含酸液库.json"), payload)
    return "已导出输入文件：%s" % folder


def export_results(result, stage_rows, horizontal=None):
    folder = _folder("结果")
    _write_csv(folder / "直井参考汇总.csv", ["参数", "数值"], asdict(result.basic).items())
    _records_csv(folder / "直井反应时序.csv", (asdict(s) for s in result.profile_rows))
    _records_csv(folder / "直井产能时序.csv", (asdict(s) for s in result.productivity_rows))
    _records_csv(folder / "直井温度剖面.csv", (asdict(s) for s in result.temperature_profile))
    _records_csv(folder / "直井参考阶段.csv", stage_rows)
    if horizontal:
        records = []
        temperatures = []
        for segment in horizontal.segments:
            record = asdict(segment)
            record.pop("temperature_profile")
            reaction = record.pop("reaction")
            record.update({"reaction_" + k: v for k, v in reaction.items()})
            records.append(record)
            temperatures.extend({"segment": segment.name, **asdict(t)} for t in segment.temperature_profile)
        _records_csv(folder / "水平段结果.csv", records)
        _records_csv(folder / "分段温度剖面.csv", temperatures)
        _write_csv(folder / "水平井施工总液量.csv", ["阶段", "体积m3"], horizontal.stage_volumes.items())
        (folder / "完整水平井结果.json").write_text(json.dumps(asdict(horizontal), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return "已导出全部结果（CSV可用Excel打开）：%s" % folder


def export_optimization(rows):
    folder = _folder("直井半径优化")
    _records_csv(folder / "直井半径优化.csv", (asdict(s) for s in rows))
    return "已导出优化结果：%s" % folder


def _e(value):
    return html.escape(str(value), quote=True)


def _fmt(value):
    return "%.3f" % value if isinstance(value, float) else str(value)


def _table(headers, rows):
    return '<div class="table"><table><thead><tr>' + ''.join('<th>' + _e(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + _e(_fmt(v)) + '</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def _temperature_svg(horizontal):
    selected = [horizontal.segments[0]]
    if len(horizontal.segments) > 1:
        selected.append(horizontal.segments[-1])
    max_md = max(p.measured_depth for s in selected for p in s.temperature_profile)
    min_t = min(p.fluid_temperature for s in selected for p in s.temperature_profile) - 5
    max_t = max(max(p.fluid_temperature, p.formation_temperature) for s in selected for p in s.temperature_profile) + 5
    def coords(md, temp):
        return (65 + md / max_md * 830, 285 - (temp - min_t) / max(max_t - min_t, 1) * 225)
    svg = ['<svg viewBox="0 0 960 345" role="img" aria-label="沿井筒温度曲线">', '<rect width="960" height="345" fill="#f3f7fa"/>']
    for i in range(6):
        temp = min_t + (max_t - min_t) * i / 5
        _, y = coords(0, temp)
        svg.append('<path d="M65 %.1f H895" stroke="#d9e2e9"/><text x="12" y="%.1f">%.0f℃</text>' % (y, y + 4, temp))
        x, _ = coords(max_md * i / 5, min_t)
        svg.append('<text x="%.1f" y="306">%.0f</text>' % (x - 15, max_md * i / 5))
    for i, seg in enumerate(selected):
        points = ' '.join('%.2f,%.2f' % coords(p.measured_depth, p.fluid_temperature) for p in seg.temperature_profile)
        color = ['#087f8c', '#b36728'][i]
        svg.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="3"/><text x="%d" y="25" fill="%s">%s 酸液</text>' % (points, color, 70 + i * 245, color, _e(seg.name)))
    points = ' '.join('%.2f,%.2f' % coords(p.measured_depth, p.formation_temperature) for p in selected[-1].temperature_profile)
    svg.append('<polyline points="%s" fill="none" stroke="#697685" stroke-dasharray="7 4" stroke-width="2"/><text x="660" y="25">地层温度（虚线）</text>' % points)
    svg.append('<text x="320" y="335">距井口测深 MD (m)；水平段地层温度恒定</text></svg>')
    return ''.join(svg)


def export_analysis_report(path, case_name, payload, radial, horizontal):
    from .model_api import parse_request
    params, segments, acids, radial_name = parse_request(payload)
    h = horizontal
    body = ['<h1>砂岩酸化分析报告与施工方案初稿</h1>', '<p class="muted">方案：%s · 模型：%s · 导出：%s</p>' % (_e(case_name), _e(h.model_version), datetime.now().strftime("%Y-%m-%d %H:%M")),
            '<div class="notice">本报告使用可标定的简化模型。默认反应、传热、沉淀系数是示例值；结果用于方案比较。施工排量、配方及阶段顺序需结合实际完井、岩心实验和现场压力曲线复核。</div>',
            '<div class="metrics"><div><b>%.2f m³</b>处理液</div><div><b>%.2f m³</b>全部施工液</div><div><b>%.3f ×</b>J后/J污染</div><div><b>%d 段</b>高风险</div></div>' % (h.total_treatment_volume, h.total_fluid_volume, h.expected_productivity_ratio, h.risk_segment_count),
            '<h2>1. 评价结论</h2><ul>' + ''.join('<li>' + _e(x) + '</li>' for x in h.conclusions) + '</ul>',
            '<h2>2. 储层、矿物与温度依据</h2>',
            _table(['参数', '值'], [('入口测深(m)', params.Zh), ('储层垂深(m)', params.vertical_depth), ('井口注入温度(℃)', params.Tf), ('储层温度(℃)', params.Tb + params.aT * (params.vertical_depth - params.Zb)), ('井壁外作用上限(m)', params.max_penetration), ('井筒有效传热系数(W/m²/K)', params.heat_transfer_u), ('矿物质量分数：石英/长石/黏土/碳酸盐/其他', ' / '.join('%.3f' % getattr(params, k) for k in ('quartz','feldspar','clay','carbonate','other_minerals'))), ('Ca / Na / K (mg/L)', ' / '.join(str(getattr(params,k)) for k in ('calcium_mg_l','sodium_mg_l','potassium_mg_l')))]),
            _temperature_svg(h), '<p>曲线为各段按自身注入排量、沿相应流路计算的准稳态温度。反应放热另以酸液与接触岩石的集总热容估算，未加入井筒曲线。</p>',
            '<h2>3. 分段产能与污染解除</h2>',
            _table(['段','相对MD(m)','污染深度(m)','处理液(m³)','作用深度(m)','覆盖率','J原始','J污染','J处理后','J后/J污染','结论'],
                   ((r.name, '%g–%g' % (r.start_md,r.end_md), r.damage_depth,r.allocated_acid,r.penetration_depth,'%.1f%%' % (r.coverage_ratio*100),r.productivity_undamaged,r.productivity_damaged,r.productivity_after,r.productivity_ratio,r.status) for r in h.segments)),
            '<p>J 单位：m³/(d·MPa)。J后/J污染表示处理前后倍比；J后/J原始表示产能恢复比例。全井先合计 J 再求比。深度从井壁起算，半径从井轴起算。</p>',
            '<h2>4. 酸岩反应与二次沉淀</h2>',
            _table(['段','到段温度℃','反应温度℃','放热温升℃','剩余酸比例','溶蚀岩石kg','溶蚀率','沉淀kg','风险代理(0–1)','无沉淀k','净k(mD)'],
                   ((r.name,r.inlet_temperature,r.reaction.temperature,r.reaction.reaction_temperature_rise,r.reaction.acid_remaining_fraction,r.reaction.dissolved_rock_kg,'%.3f%%' % (r.reaction.dissolution_fraction*100),r.reaction.precipitate_kg,r.reaction.precipitation_risk,r.reaction.permeability_without_precipitation,r.reaction.permeability_after) for r in h.segments)),
            '<p>溶蚀率=溶蚀质量/估算接触岩石质量。风险代理不是沉淀发生概率或热力学饱和指数；没有逐种定量求解 CaF₂、氟硅酸盐及硅胶。关闭沉淀仅用于敏感性对照。</p>',
            '<h2>5. 施工方案初稿</h2><p>假设可逐段封隔注入，以下按趾端到跟端列出。每段前置→处理→后置；全井最后一次顶替。实际工具串及必要的段间顶替未建模。</p>',
            _table(['阶段','全井体积(m³)'], [('前置液',h.stage_volumes['preflush']),('处理液',h.stage_volumes['treatment']),('后置液',h.stage_volumes['postflush']),('末次顶替液',h.stage_volumes['displacement']),('总计',h.total_fluid_volume)]),
            _table(['顺序/段','酸液体系','前置m³','处理m³','后置m³','输入排量m³/min','建议排量上限','井口限压MPa','按建议排量估算min'],
                   ((r.name,r.acid_system,r.stage_volumes['preflush'],r.allocated_acid,r.stage_volumes['postflush'],r.required_rate,r.allowed_rate,r.surface_pressure_limit,r.estimated_pumping_minutes) for r in reversed(h.segments))),
            '<p>估算时间按建议排量上限计算，不含转层、停泵与末次顶替。若输入排量超过建议上限，当前反应结果与建议施工时间不一致，需修改接触时间并重新计算。</p>']
    for r in h.segments:
        if r.warnings:
            body.append('<p class="risk"><b>%s：</b>%s</p>' % (_e(r.name), _e('；'.join(r.warnings))))
    body.append('<h2>6. 使用的酸液体系与标定参数</h2>')
    for name in sorted({r.acid_system for r in h.segments}):
        acid = acids[name]
        from .data import ACID_FIELD_LABELS
        body.append('<h3>' + _e(name) + '</h3>')
        body.append(_table(['参数','内容'], ((ACID_FIELD_LABELS.get(k,k),v) for k,v in asdict(acid).items())))
    body += ['<h2>7. 计算边界与参考论文</h2><p>井筒采用定有效传热系数的一维能量平衡；反应采用 Kelvin 温标 Arrhenius 关系及酸量/矿物量限制；沉淀以可调系数折减净渗透率。2m 为本项目约束。论文支持机制和建模思路，不代表这些默认数值已经验证。</p>',
             '<ul>' + ''.join('<li><a href="%s">%s</a></li>' % (_e(url),_e(title)) for title,url in REFERENCES) + '</ul>',
             '<details><summary>完整输入快照（含自定义酸液库）</summary><pre>' + _e(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False)) + '</pre></details>']
    css = 'body{font:15px/1.7 "Microsoft YaHei",sans-serif;color:#1c303e;margin:40px auto;max-width:1250px;padding:0 24px}h1{color:#087f8c;font-size:30px}h2{margin-top:36px;border-bottom:2px solid #dce9ef}h3{color:#087f8c}.muted{color:#677b89}.notice{background:#fff5db;padding:18px;border-left:4px solid #c98524}.metrics{display:flex;gap:14px;margin:24px 0}.metrics div{flex:1;background:#eef7f8;padding:18px}.metrics b{display:block;font-size:25px;color:#087f8c}table{border-collapse:collapse;width:100%;font-size:12px}th,td{padding:8px;border:1px solid #d7e1e7;text-align:left;overflow-wrap:anywhere}th{background:#edf3f6}tr:nth-child(even){background:#fafcfd}.table{overflow-x:auto}svg{width:100%;font:14px sans-serif}.risk{color:#a33b2f}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media print{@page{size:A4 landscape;margin:12mm}body{margin:0;padding:0;max-width:none;font-size:11px}table{font-size:9px}.table{overflow:visible}thead{display:table-header-group}tr{break-inside:avoid}h2,h3{break-after:avoid}.metrics{break-inside:avoid}details{display:none}a{color:inherit;text-decoration:none}}'
    document = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + _e(case_name) + ' - 酸化分析报告</title><style>' + css + '</style><body>' + ''.join(body) + '</body></html>'
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding='utf-8')
    return target
