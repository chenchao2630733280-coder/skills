"""关卡战役配置（campaign.json）的加载、校验与特征派生。

设计约定：
1. 关卡难度用 8 个 [0,1] 标准化维度描述，权重与 difficulty_scorer.py 保持一致。
2. 设计师可以只填 params（步数/目标量/颜色数…），由 feature_model 派生特征；
   也可以直接填 features 覆盖派生值。派生规则必须项目校准，不可当作通用公式。
3. 阶段（phase）用"参考分层的首次通关率"表达目标，比抽象分数更好沟通。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

FEATURES = (
    "resource_pressure",
    "mechanic_load",
    "strategy_depth",
    "randomness",
    "operation_pressure",
    "time_pressure",
    "space_pressure",
    "goal_complexity",
)

FEATURE_LABELS = {
    "resource_pressure": "资源压力",
    "mechanic_load": "机制负荷",
    "strategy_depth": "策略深度",
    "randomness": "随机性",
    "operation_pressure": "操作压力",
    "time_pressure": "时间压力",
    "space_pressure": "空间压力",
    "goal_complexity": "目标复杂度",
}

DEFAULT_WEIGHTS = {
    "resource_pressure": 0.20,
    "mechanic_load": 0.15,
    "strategy_depth": 0.20,
    "randomness": 0.10,
    "operation_pressure": 0.10,
    "time_pressure": 0.10,
    "space_pressure": 0.10,
    "goal_complexity": 0.05,
}

DEFAULT_THRESHOLDS = {
    "jump_score": 0.08,
    "jump_winrate": 0.10,
    "band_tolerance": 0.05,
    "min_sample": 30,
    "unstable_sd": 0.09,
    "near_unwinnable": 0.35,
    "overload_dims": 3,
    "overload_dim_rise": 0.12,
}

# 参数 -> 难度维度的默认映射。per_unit 为"每 1 个单位参数变化带来的维度变化"，
# 符号表示：参数增加时维度升高(+)或降低(-)。step 是最小可调粒度。
DEFAULT_KNOBS = {
    "match3": [
        {"param": "moves", "dim": "resource_pressure", "per_unit": -0.045, "step": 1, "max_delta": 6, "label": "可用步数", "note": "加步数=减压，但会拉长单局并削弱紧张感"},
        {"param": "target_amount", "dim": "goal_complexity", "per_unit": 0.00004, "step": 100, "max_delta": 600, "label": "目标量", "note": "目标量按比例缩放，注意奖励节奏与数值通胀"},
        {"param": "obstacle_kinds", "dim": "mechanic_load", "per_unit": 0.20, "step": 1, "max_delta": 1, "label": "障碍种类数", "note": "增加机制数量，教学成本同步上升"},
        {"param": "colors", "dim": "randomness", "per_unit": 0.12, "step": 1, "max_delta": 1, "label": "棋子颜色数", "note": "影响匹配可达性方差，过少会降低策略空间"},
        {"param": "time_limit", "dim": "time_pressure", "per_unit": -0.01, "step": 5, "max_delta": 15, "label": "时限(秒)", "note": "仅限时玩法；与思考型玩家体验冲突"},
    ],
    "merge": [
        {"param": "energy_cost", "dim": "resource_pressure", "per_unit": 0.03, "step": 1, "max_delta": 3, "label": "单次产出能量消耗", "note": "直接影响会话长度与付费感"},
        {"param": "orders", "dim": "goal_complexity", "per_unit": 0.08, "step": 1, "max_delta": 2, "label": "并行订单数", "note": "并行目标增加认知切换成本"},
        {"param": "generator_kinds", "dim": "mechanic_load", "per_unit": 0.18, "step": 1, "max_delta": 1, "label": "产出器种类", "note": "种类越多，产出链规划越复杂"},
        {"param": "board_size", "dim": "space_pressure", "per_unit": 0.06, "step": 1, "max_delta": 4, "label": "棋盘格数", "note": "空间越小，卡死风险越高"},
    ],
    "puzzle": [
        {"param": "steps", "dim": "strategy_depth", "per_unit": 0.05, "step": 1, "max_delta": 3, "label": "允许步数", "note": "步数上升通常提高规划深度需求"},
        {"param": "rule_kinds", "dim": "mechanic_load", "per_unit": 0.20, "step": 1, "max_delta": 1, "label": "规则数量", "note": "规则叠加带来的理解成本非线性"},
        {"param": "hints", "dim": "resource_pressure", "per_unit": -0.06, "step": 1, "max_delta": 2, "label": "提示次数", "note": "提示是软辅助，影响资源压力与挫败感"},
    ],
    "time_management": [
        {"param": "arrival_rate", "dim": "time_pressure", "per_unit": 0.05, "step": 0.2, "max_delta": 0.6, "label": "顾客到达率", "note": "到达率对掉单率是非线性影响"},
        {"param": "queue_slots", "dim": "space_pressure", "per_unit": -0.07, "step": 1, "max_delta": 2, "label": "队列容量", "note": "扩容降低排队压力，但可能让关卡失去张力"},
        {"param": "task_kinds", "dim": "mechanic_load", "per_unit": 0.16, "step": 1, "max_delta": 1, "label": "任务种类", "note": "切换成本随种类上升"},
    ],
}


class ConfigError(ValueError):
    """配置不合法时抛出，便于 CLI 给出可读报错。"""


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


@dataclass
class Segment:
    name: str
    theta: float
    theta_sd: float
    target_first_try: float | None = None


@dataclass
class Phase:
    name: str
    from_index: int
    to_index: int
    shape: str = "ramp"
    start_win: float | None = None
    end_win: float | None = None
    mechanics_intro: list = field(default_factory=list)

    def contains(self, index: int) -> bool:
        return self.from_index <= index <= self.to_index


@dataclass
class Level:
    level_id: str
    index: int
    tag: str
    features: dict
    params: dict
    legal_ranges: dict
    new_mechanics: list
    notes: str
    feature_source: str = "explicit"

    def feature(self, name: str) -> float:
        return float(self.features.get(name, 0.0))


@dataclass
class Campaign:
    campaign_id: str
    genre: str
    version: str
    data_source: str
    spread: float
    ref_segment: str
    segments: dict
    simulation: dict
    thresholds: dict
    weights: dict
    phases: list
    levels: list
    knobs: list
    micro_rhythm: bool
    raw: dict

    # ---------- 加载 ----------
    @classmethod
    def load(cls, path) -> "Campaign":
        path = Path(path)
        if not path.exists():
            raise ConfigError(f"找不到配置文件: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"JSON 解析失败 ({path}): {exc}") from exc
        return cls.from_dict(data, source=str(path))

    @classmethod
    def from_dict(cls, data: dict, source: str = "<inline>") -> "Campaign":
        for key in ("campaign_id", "genre", "levels", "segments"):
            if key not in data:
                raise ConfigError(f"{source}: 缺少必填字段 `{key}`")

        segments = {}
        for name, seg in data["segments"].items():
            if "theta" not in seg:
                raise ConfigError(f"玩家分层 `{name}` 缺少 theta")
            segments[name] = Segment(
                name=name,
                theta=float(seg["theta"]),
                theta_sd=float(seg.get("theta_sd", 0.5)),
                target_first_try=seg.get("target_first_try"),
            )
        if not segments:
            raise ConfigError("segments 不能为空")

        mapping = data.get("mapping", {})
        ref_segment = mapping.get("ref_segment", "regular" if "regular" in segments else next(iter(segments)))
        if ref_segment not in segments:
            raise ConfigError(f"mapping.ref_segment=`{ref_segment}` 不在 segments 中")

        thresholds = dict(DEFAULT_THRESHOLDS)
        thresholds.update(data.get("thresholds", {}))

        weights = dict(DEFAULT_WEIGHTS)
        weights.update(data.get("weights", {}))
        if abs(sum(weights.values()) - 1.0) > 1e-6:
            raise ConfigError(f"weights 之和必须为 1，当前为 {sum(weights.values()):.3f}")

        feature_model = data.get("feature_model", {})
        campaign_ranges = data.get("legal_ranges", {})
        levels = []
        seen_ids = set()
        for item in data["levels"]:
            lv = _build_level(item, feature_model, campaign_ranges)
            if lv.level_id in seen_ids:
                raise ConfigError(f"level_id 重复: {lv.level_id}")
            seen_ids.add(lv.level_id)
            levels.append(lv)
        levels.sort(key=lambda x: x.index)
        _validate_indexes(levels)

        phases = [Phase(**{k: v for k, v in p.items() if k in Phase.__dataclass_fields__}) for p in data.get("phases", [])]
        if not phases:
            # 无阶段时退化为单阶段，覆盖全部关卡
            phases = [Phase(name="默认阶段", from_index=levels[0].index, to_index=levels[-1].index)]
        _validate_phases(phases, levels)

        knobs = data.get("knobs") or DEFAULT_KNOBS.get(data["genre"], [])

        sim = {
            "players_per_segment": 400,
            "batches": 8,
            "max_attempts": 5,
            "learning_logit": 0.22,
            "booster_rate": 0.35,
            "booster_logit_gain": 0.45,
            "retry_prob": 0.55,
            "seed_jitter_k": 0.55,
            "base_seed": 17,
        }
        sim.update(data.get("simulation", {}))

        return cls(
            campaign_id=data["campaign_id"],
            genre=data["genre"],
            version=str(data.get("version", "0.0.0")),
            data_source=data.get("data_source", "unspecified"),
            spread=float(mapping.get("spread", 4.0)),
            ref_segment=ref_segment,
            segments=segments,
            simulation=sim,
            thresholds=thresholds,
            weights=weights,
            phases=phases,
            levels=levels,
            knobs=knobs,
            micro_rhythm=bool(data.get("micro_rhythm", True)),
            raw=data,
        )

    # ---------- 便捷查询 ----------
    def phase_of(self, index: int) -> Phase:
        for p in self.phases:
            if p.contains(index):
                return p
        return self.phases[-1]

    def ref_theta(self) -> float:
        return self.segments[self.ref_segment].theta

    def at(self, index: int) -> Level:
        for lv in self.levels:
            if lv.index == index:
                return lv
        raise KeyError(index)


def _build_level(item: dict, feature_model: dict, campaign_ranges: dict) -> Level:
    if "level_id" not in item:
        raise ConfigError("每条关卡配置都需要 level_id")
    params = dict(item.get("params", {}))
    given = item.get("features", {})
    derived = _derive_features(params, feature_model)
    features = {}
    for name in FEATURES:
        if name in given:
            features[name] = float(given[name])
        elif name in derived:
            features[name] = derived[name]
        else:
            features[name] = 0.0
    for name, value in features.items():
        if not -1e-9 <= value <= 1 + 1e-9:
            raise ConfigError(f"{item.get('level_id')}: 维度 {name}={value} 超出 [0,1]，请检查 feature_model 或 features")
        features[name] = _clamp(value)
    ranges = dict(campaign_ranges)
    ranges.update(item.get("legal_ranges", {}))
    provided = sum(1 for name in FEATURES if name in given)
    if provided == len(FEATURES):
        source = "explicit"
    elif provided:
        source = "mixed"
    elif derived:
        source = "derived"
    else:
        source = "none"
    return Level(
        level_id=str(item["level_id"]),
        index=int(item.get("index", 0)),
        tag=str(item.get("tag", "STANDARD")),
        features=features,
        params=params,
        legal_ranges=ranges,
        new_mechanics=list(item.get("new_mechanics", [])),
        notes=str(item.get("notes", "")),
        feature_source=source,
    )


def _derive_features(params: dict, model: dict) -> dict:
    out = {}
    for dim, rule in (model or {}).items():
        if dim not in FEATURES:
            raise ConfigError(f"feature_model 含未知维度 `{dim}`")
        kind = rule.get("kind", "linear")
        try:
            if kind == "linear":
                raw = float(params[rule["param"]])
            elif kind == "ratio":
                den = float(params[rule["den"]])
                raw = float(params[rule["num"]]) / den if den else 0.0
            elif kind == "count":
                val = params.get(rule["param"], 0)
                raw = float(len(val)) if isinstance(val, (list, tuple)) else float(val)
            else:
                raise ConfigError(f"feature_model.{dim}.kind 不支持: {kind}")
        except KeyError as exc:
            raise ConfigError(f"feature_model.{dim} 引用了 params 中不存在的字段 {exc}") from exc
        lo, hi = float(rule["lo"]), float(rule["hi"])
        x = 0.5 if hi == lo else (raw - lo) / (hi - lo)
        if rule.get("invert"):
            x = 1 - x
        out[dim] = _clamp(x)
    return out


def _validate_indexes(levels: list) -> None:
    indexes = [lv.index for lv in levels]
    if len(set(indexes)) != len(indexes):
        raise ConfigError("关卡 index 存在重复")
    for lv in levels:
        if lv.index <= 0:
            raise ConfigError(f"{lv.level_id}: index 必须为正整数")


def _validate_phases(phases: list, levels: list) -> None:
    for p in phases:
        if p.from_index > p.to_index:
            raise ConfigError(f"阶段 `{p.name}` 的 from_index 大于 to_index")
    if phases[0].from_index > levels[0].index:
        phases[0].from_index = levels[0].index
    if phases[-1].to_index < levels[-1].index:
        phases[-1].to_index = levels[-1].index
