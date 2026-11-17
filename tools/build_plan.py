#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 36 个月 / 156 周三轨学习计划。

用法：
    python tools/build_plan.py            # 干跑：校验 + 生成周级摘要，不写 JSON
    python tools/build_plan.py --write    # 校验 + 写 plans/quant-llm-3yr.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "plan_data"
sys.path.insert(0, str(DATA_DIR))

from y1 import WEEKS as Y1  # noqa: E402
from y2 import WEEKS as Y2  # noqa: E402
from y3 import WEEKS as Y3  # noqa: E402

WEEKS = Y1 + Y2 + Y3
START = date(2026, 11, 16)
DOW = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
FORBIDDEN = ("神经网络", "LSTM", "Transformer")
COMMERCIAL_WEIGHTS = {
    "commercialViability": 0.40,
    "apiPackaging": 0.30,
    "frontendVisualization": 0.30,
}
COMMERCIAL_REQUIRED = [
    "商业可行性：谁付费、为什么现在付费、定价假设是什么",
    "API/产品化：API、CLI、SDK 或订阅服务，按调用量/席位/订阅收费",
    "前端/可视化：dashboard、报告页或落地页，3 分钟讲清价值",
    "获客/分发：目标用户在哪、本周触达几个、通过什么渠道",
]

STAGE_INFO = {
    "第一阶段：底座与双线入门": {
        "months": "第 1-12 个月",
        "weeks": "W1-W52",
        "ratio": "量化:大模型 = 6:4",
        "goals": [
            "Python、Git、NumPy/Pandas 与数学统计底座",
            "金融数据、收益风险指标、单因子与最小回测",
            "Prompt、RAG、工具调用与一次最小 LoRA 实验",
            "完成 Q1-Q4 四个可展示作品，每个作品补齐商业化三件套（商业假设/API/可视化）",
        ],
    },
    "第二阶段：交叉深化与工程化": {
        "months": "第 13-24 个月",
        "weeks": "W53-W104",
        "ratio": "量化:大模型 = 5:5",
        "goals": [
            "机器学习、树模型、特征工程与 ML 因子挖掘",
            "时间序列、波动率、组合优化与风险模型",
            "LoRA/QLoRA/DPO、推理部署与 Agent 应用",
            "把研究代码工程化为数据管道、回测引擎与研究 API，并完成 1 次定价/用户验证",
        ],
    },
    "第三阶段：深入与作品收敛": {
        "months": "第 25-36 个月",
        "weeks": "W105-W156",
        "ratio": "量化:大模型 = 5:5",
        "goals": [
            "微观结构、执行算法、另类数据与高级风险",
            "完整 AI+量化项目：LLM 事件因子 → 回测 → 模拟盘 → 风控",
            "论文/技术报告、开源仓库与作品集收敛",
            "形成可对外交付的产品/服务，完成付费或出海验证",
        ],
    },
}

MILESTONES = {
    1: "建立三轨周复盘模板 + 学习日志",
    8: "简历 v1 + GitHub 仓库上线",
    13: "Q1 作品 v0 发布（数据小报告 + RAG demo）",
    20: "GitHub 主页整理 + 1 篇技术笔记",
    26: "Q2 作品发布（单因子报告 + RAG 评测）",
    36: "RAG API 上线（本地/云）",
    39: "Q3 作品发布（多因子回测 v1 + RAG 服务 v1）",
}


def stage_of(n: int) -> str:
    if n <= 52:
        return "第一阶段：底座与双线入门"
    if n <= 104:
        return "第二阶段：交叉深化与工程化"
    return "第三阶段：深入与作品收敛"


def quarter_of(n: int) -> str:
    q = (n - 1) // 13
    return f"Y{q // 4 + 1}-Q{q % 4 + 1}"


def commercial_check(n: int) -> str:
    if n <= 52:
        return "把本周交付包装成 1 张可视化图 + 1 个可调用脚本/CLI，并写下 1 个潜在付费用户。"
    if n <= 104:
        return "为本周交付补 API/CLI 接口与使用示例，写出定价假设，并找 1 个潜在用户验证。"
    return "补齐 API 文档、落地页/定价页与前端 demo，本周触达 3 个潜在用户并记录反馈。"


def commercial_task(n: int) -> str:
    if n <= 52:
        return "【商业化】把本周交付做成 1 张可展示图 + 1 个可调用脚本/CLI；写 1 句“谁可能付费”。"
    if n <= 104:
        return "【商业化】给本周交付补 API/CLI 接口与 README 示例；写 1 个定价假设并找 1 人验证。"
    return "【商业化】补 API 文档、落地页/前端 demo；本周触达 3 个潜在用户并记录反馈。"


def meta_of(n: int) -> dict:
    if n <= 39:
        if n <= 13:
            action = "准备期：建立简历骨架与 GitHub，暂不投递"
        elif n <= 26:
            action = "准备期：补金融数据与 RAG 项目，维护简历项目池"
        else:
            action = "准备期：完成可展示作品，开始 JD 对照"
        due = MILESTONES.get(n, "无（内部积累，保持 GitHub 周更）")
        return {
            "internshipWindow": False,
            "internshipAction": action,
            "externalSignalDue": due,
        }

    if n <= 52:
        return {
            "internshipWindow": True,
            "internshipAction": "大模型实习：每周投递 ≥5 家，记录反馈并迭代简历",
            "externalSignalDue": f"本周投递 ≥5 家（累计 ≥{(n - 39) * 5} 家）并更新投递表",
        }

    if n <= 78:
        return {
            "internshipWindow": True,
            "internshipAction": "量化实习：每周投递 ≥5 家，保留 2 家大模型岗",
            "externalSignalDue": f"本周投递 ≥5 家（累计 ≥{(n - 52) * 5} 家），争取 1 次内推",
        }

    if n <= 104:
        return {
            "internshipWindow": True,
            "internshipAction": "第二段实习：主攻大模型/量化交叉岗，每周 ≥5 家",
            "externalSignalDue": f"本周投递 ≥5 家（累计 ≥{(n - 78) * 5} 家），完成 1 次模拟/真实面试",
        }

    return {
        "internshipWindow": True,
        "internshipAction": "转正/深度实习：锁定 3 个目标团队，争取 return offer",
        "externalSignalDue": f"本周完成 1 次 1:1/汇报，更新转正证据清单（第 {n - 104} 周）",
    }


def minutes_of(n: int, day_index: int) -> tuple[int, int]:
    if n <= 52:
        return 90, 60
    if day_index == 6:
        return 75, 75
    return 90, 90


REVIEW_MARKERS = ("复盘", "知识地图", "答辩", "三年")
CAREER_MARKERS = ("面试", "简历", "投递", "offer", "作品集", "谈判", "模拟")


def mode_of(topic: str) -> str:
    if any(k in topic for k in REVIEW_MARKERS):
        return "review"
    if any(k in topic for k in CAREER_MARKERS):
        return "career"
    return "default"


def quant_task(day_index: int, q: str, qd: str, mode: str) -> str:
    if mode == "review":
        return [
            "【盘点】列出本周要整合的 3 项量化产出、2 个缺口和 1 个可讲的项目故事。",
            "【补洞】针对最大缺口完成 1 个最小修复，记录修复前后的差异。",
            "【整合】把本周/本季量化产出整理成 5-10 页文档或答辩提纲。",
            "【预演】做一次 10 分钟讲解/答辩，记录 3 个被问住的点并补答案。",
            "【周测】完成季度自测 20 题并订正；错题写入 skills-gaps.md。",
            f"【交付】{qd}：定稿并归档，补 README、复现步骤与 1 张结果图。",
            "【复盘】更新知识地图与下季度计划；用 3 句话总结本季量化主线。",
        ][day_index]
    if mode == "career":
        return [
            "【盘点】对照 3 个目标 JD，列出匹配点、缺口和 1 个可讲的项目故事。",
            "【打磨】改 1 版简历/项目故事/题库，产出 3 条可量化的成果。",
            "【推进】完成 1 次投递/内推/模拟面试，记录渠道、版本与反馈。",
            "【加固】针对 1 个高频问题写答案并口述 3 遍，录音复盘。",
            "【周测】做 1 次 60 分钟模拟面试/笔试，记录 3 个卡点。",
            f"【交付】{qd}：定稿并归档，更新 targets.md 与投递表。",
            "【复盘】更新 gaps 清单与下周投递计划；用 3 句话总结本周求职进展。",
        ][day_index]
    return [
        f"【拆解】{q}：精读/观看 40 分钟，画 1 张概念图/流程图，写 5 条要点并标出与上周的连接。",
        f"【动手】{q}：完成一个最小可运行/可展示的产物（代码、脚本、文档或图），保存证据。",
        f"【推进】{q}：在周二产物上补一个真实输入/真实案例，记录 3 个问题。",
        f"【加固】{q}：改进一步（换参数/换方法/补边界/加测试），写 5 行含数字的结论。",
        f"【周测】完成《{q}》5 道自测题并订正；错题写入 skills-gaps.md 并标最小补救动作。",
        f"【交付】{qd}：整合本周产出，补 README、复现步骤与 1 张结果图。",
        f"【复盘】重做 1 道错题；用 3 句话总结「{q}」，更新知识地图。",
    ][day_index]


def llm_task(day_index: int, l: str, ld: str, mode: str) -> str:
    if mode == "review":
        return [
            "【盘点】列出 LLM 侧 3 项产出、2 个失败案例和 1 个可讲的技术故事。",
            "【补洞】修复最大的失败案例，记录修复前后对比。",
            "【整合】把 LLM 产出整理成 demo、评测报告或模型卡。",
            "【预演】用 10 分钟讲清方案、指标与取舍，记录 3 个被问住的点。",
            "【周测】用 20 条样例做回归评测，记录通过率与 3 个失败案例。",
            f"【交付】{ld}：定稿并归档，补模型卡、评测记录与复现命令。",
            "【复盘】更新提示词库与下季度 LLM 计划；用 3 句话总结本季主线。",
        ][day_index]
    if mode == "career":
        return [
            "【盘点】对照 3 个 LLM JD，列出匹配点、缺口和 1 个可讲的技术故事。",
            "【打磨】改 1 版 LLM 简历/项目故事/题库，补 3 条量化指标。",
            "【推进】完成 1 次投递/内推/模拟面试，记录反馈。",
            "【加固】针对 1 个高频 LLM 问题写答案并口述 3 遍。",
            "【周测】做 1 次 60 分钟 LLM 模拟面试/笔试，记录 3 个卡点。",
            f"【交付】{ld}：定稿并归档，更新 targets.md 与投递表。",
            "【复盘】更新 LLM 题库与下周计划；用 3 句话总结本周求职进展。",
        ][day_index]
    return [
        f"【拆解】{l}：精读/观看 30 分钟，画 1 张流程图，写 3 条要点 + 1 个可落地场景。",
        f"【动手】{l}：跑通最小调用/示例，保存输入、输出与关键参数。",
        f"【推进】{l}：用一份真实文档/任务跑通，记录 2 个失败案例。",
        f"【加固】{l}：设计 3 条评测样例，记录命中/失败原因与 1 条改进。",
        f"【周测】用 10 条样例评测《{l}》，记录 3 个失败案例；写入 skills-gaps.md。",
        f"【交付】{ld}：整合本周产出，补模型卡/评测记录与复现命令。",
        f"【复盘】重跑 1 个失败案例；用 3 句话总结「{l}」，更新提示词库。",
    ][day_index]


def track_deliverable(mode: str, day_index: int, topic: str, final_dl: str, track: str) -> str:
    if mode == "review":
        return [
            "3 项产出清单 + 2 个缺口",
            "缺口修复记录",
            "5-10 页整合文档/答辩提纲",
            "10 分钟预演记录 + 3 个问题",
            "季度自测卷 + 错题" if track == "quant" else "20 条回归评测记录",
            final_dl,
            "季度量化复盘 + 下季度计划" if track == "quant" else "季度 LLM 复盘 + 下季度计划",
        ][day_index]
    if mode == "career":
        return [
            "3 个 JD 对照表 + 1 个项目故事" if track == "quant" else "3 个 LLM JD 对照表 + 1 个技术故事",
            "简历/题库修订版",
            "投递/模拟记录",
            "高频问题答案卡",
            "模拟面试复盘",
            final_dl,
            "量化求职复盘 + 下周投递计划" if track == "quant" else "LLM 求职复盘 + 下周投递计划",
        ][day_index]
    return [
        f"{topic} 概念图/流程图 + 5 条要点" if track == "quant" else f"{topic} 流程图 + 3 条要点",
        f"{topic} 最小产物" if track == "quant" else f"{topic} 最小调用/示例",
        f"{topic} 真实案例记录" if track == "quant" else f"{topic} 真实任务记录",
        f"{topic} 加固结论 5 行" if track == "quant" else f"{topic} 评测记录 3 条",
        "周测卷 + 错题" if track == "quant" else "周测卷 + 失败案例",
        final_dl,
        "量化周复盘 200 字 + 知识地图更新" if track == "quant" else "LLM 周复盘 200 字 + 提示词库更新",
    ][day_index]


def track_exercises(mode: str, day_index: int, topic: str, track: str) -> list[str]:
    if mode == "review":
        return [
            ["列出 3 项产出与 2 个缺口", "写 1 个可讲的项目故事"],
            ["完成 1 个缺口修复", "记录修复前后差异"],
            ["完成整合文档/答辩提纲", "以面试官视角挑 3 个问题"],
            ["做 1 次 10 分钟预演", "补 3 个被问住的答案"],
            ["完成季度自测 20 题", "整理 3 个失败案例"],
            ["定稿并归档交付物", "检查 README/复现步骤"],
            ["写 300 字季度复盘", "列出下季度 3 个目标"],
        ][day_index]
    if mode == "career":
        return [
            ["列出 3 个 JD 的匹配点与缺口", "写 1 个 90 秒项目故事"],
            ["完成 1 版简历/题库修订", "补 3 条量化成果"],
            ["完成 1 次投递/内推/模拟", "记录 3 条反馈"],
            ["写 3 个高频问题的答案", "口述并录音复盘"],
            ["做 1 次 60 分钟模拟面试", "整理 3 个卡点"],
            ["更新 targets.md 与投递表", "归档本轮材料"],
            ["更新 skills-gaps.md", "列出下周 5 个投递目标"],
        ][day_index]
    return [
        [f"复述《{topic}》的 5 条要点", "写下 1 个真实应用场景"],
        [f"提交《{topic}》最小产物", "写 3 行运行/复现说明"],
        [f"给《{topic}》补一个真实输入/案例", "记录 3 个问题"],
        [f"完成《{topic}》的加固实验", "写 5 行含数字的结论"],
        [f"完成《{topic}》5 道自测题并订正", "整理 3 个失败案例"],
        ["按 README 从零复现一次", "以读者视角检查交付物是否自解释"],
        ["重做 1 道错题", "写 200 字周复盘并更新下周计划"],
    ][day_index]


def build() -> dict:
    weeks: list[dict] = []
    days: list[dict] = []

    for expected, (n, q, l, qd, ld) in enumerate(WEEKS, start=1):
        if n != expected:
            raise ValueError(f"周次不连续：期望 {expected}，实际 {n}")

        stage = stage_of(n)
        quarter = quarter_of(n)
        ws = START + timedelta(weeks=n - 1)
        we = ws + timedelta(days=6)

        weeks.append(
            {
                "week": n,
                "stage": stage,
                "quarter": quarter,
                "startDate": ws.isoformat(),
                "endDate": we.isoformat(),
                "theme": f"量化：{q}；大模型：{l}",
                "quantTopic": q,
                "llmTopic": l,
                "quantDeliverable": qd,
                "llmDeliverable": ld,
                "deliverable": f"量化：{qd}；大模型：{ld}",
                "commercialCheck": commercial_check(n),
                "meta": meta_of(n),
            }
        )

        for i, dow in enumerate(DOW):
            d = ws + timedelta(days=i)
            qmin, lmin = minutes_of(n, i)
            q_mode = mode_of(q)
            l_mode = mode_of(l)
            day = {
                "week": n,
                "dayOfWeek": dow,
                "date": d.isoformat(),
                "stage": stage,
                "quantTask": quant_task(i, q, qd, q_mode),
                "llmTask": llm_task(i, l, ld, l_mode),
                "quantMin": qmin,
                "llmMin": lmin,
                "deliverable": (
                    f"量化：{track_deliverable(q_mode, i, q, qd, 'quant')}；"
                    f"LLM：{track_deliverable(l_mode, i, l, ld, 'llm')}"
                ),
                "exercises": (
                    [f"量化：{x}" for x in track_exercises(q_mode, i, q, "quant")]
                    + [f"LLM：{x}" for x in track_exercises(l_mode, i, l, "llm")]
                ),
            }
            if i == 5:
                day["commercialTask"] = commercial_task(n)
                if n % 13 == 0:
                    day["packagingGuide"] = (
                        "本周项目交付必须附《商业变现包装指南》："
                        "目标客户、卖点、定价、云部署 Demo 链接。"
                    )
            days.append(day)

    return {
        "title": "36 个月三轨并行学习计划：量化 × 大模型 × 技术商业化（实习为阶段杠杆）",
        "startDate": START.isoformat(),
        "endDate": (START + timedelta(weeks=156) - timedelta(days=1)).isoformat(),
        "totalMonths": 36,
        "totalWeeks": 156,
        "dailyHours": "2.5-3",
        "timezone": "Asia/Shanghai",
        "generatedAt": date.today().isoformat(),
        "principles": [
            "每天两条任务线：先量化后大模型，单条 60-90 分钟，中间至少休息 10 分钟。",
            "每周六必须形成可复现交付物；没有交付物的一周视为未完成。",
            "每周日复盘错题/失败案例，并把缺口写进 skills-gaps.md。",
            "每 13 周一个季度作品；每 52 周一次年度答辩。",
            "所有项目产出必须补齐商业化三件套：商业可行性假设、API/CLI 封装、前端/可视化展示。",
            "每天至少做 1 个 15 分钟变现微动作：发布作品、接触潜在客户、投递外包或调研真实需求。",
            "所有项目作业必须附《商业变现包装指南》：目标客户、卖点、定价、云部署 Demo 链接；只有功能实现不算完成。",
            "每季度至少做 1 次外部用户/付费验证；没有商业化假设的项目只算练习，不进入 Portfolio 主叙事。",
            "实习仍保留，但定位为现金流、行业信息与渠道杠杆，不是唯一终点。",
        ],
        "commercialization": {
            "positioning": "高杠杆技术变现 / 独立开发 / 出海业务",
            "weights": COMMERCIAL_WEIGHTS,
            "requiredPerProject": COMMERCIAL_REQUIRED,
            "monetizationPaths": [
                "API/订阅",
                "SaaS/工具",
                "模板/课程",
                "数据/研究报告",
                "咨询/外包",
                "出海小产品",
            ],
            "dailyMicroAction": "每天 15 分钟变现微动作：发布作品、接触潜在客户、投递外包或调研真实需求；必须具体到平台与动作。",
            "packagingGuide": {
                "requiredFor": ["RAG", "Agent", "量化回测框架", "所有项目作业"],
                "requiredSections": ["目标客户", "卖点", "定价", "云部署 Demo 链接", "获客验证"],
                "template": "templates/commercial-packaging-guide.md",
                "rule": "项目作业只有功能实现不算完成；必须附《商业变现包装指南》并给出可访问 Demo 链接。",
            },
            "tracking": {
                "daily": "side-income.md 的“每日变现动作”表",
                "weekly": "side-income.md 的“每周收支”表",
            },
            "portfolioRule": "没有商业化假设的项目只算练习，不进入 Portfolio 主叙事。",
            "validationCadence": "每季度至少 1 次外部用户/付费验证；每周复盘检查潜在商业变现价值。",
            "integration": "商业化检查并入周六交付，不额外增加每日 2.5-3 小时上限。",
        },
        "stages": [
            {
                "stage": name,
                "months": info["months"],
                "weeks": info["weeks"],
                "ratio": info["ratio"],
                "goals": info["goals"],
            }
            for name, info in STAGE_INFO.items()
        ],
        "internshipPolicy": [
            {
                "window": "W40-W52",
                "weeks": [40, 52],
                "track": "大模型实习",
                "action": "启动投递：每周 ≥5 家，优先 RAG/Agent/微调应用岗",
                "signal": "投递记录、面试复盘、简历迭代版本",
            },
            {
                "window": "W53-W78",
                "weeks": [53, 78],
                "track": "量化实习",
                "action": "主攻量化研究/因子/回测岗，保留 2 家大模型岗",
                "signal": "量化面试题复盘、项目报告、内推记录",
            },
            {
                "window": "W79-W104",
                "weeks": [79, 104],
                "track": "第二段实习",
                "action": "冲击大模型/量化交叉岗，形成第二段可写简历的经历",
                "signal": "第二段 offer、跨栈项目、作品集更新",
            },
            {
                "window": "W105-W156",
                "weeks": [105, 156],
                "track": "转正/深度实习",
                "action": "锁定 3 个目标团队，争取 return offer 或深度实习",
                "signal": "转正答辩、return offer、论文/开源/作品集",
            },
        ],
        "constraints": {
            "dailyTotalMinutes": [150, 180],
            "singleTaskMinutes": [60, 90],
            "year1Ratio": "量化:大模型 = 6:4",
            "forbiddenQuantKeywordsWeeks1to24": list(FORBIDDEN),
            "internshipWindows": {
                "W40-W52": "大模型实习投递",
                "W53-W78": "量化实习",
                "W79-W104": "第二段实习",
                "W105-W156": "转正/深度实习",
            },
        },
        "weeks": weeks,
        "days": days,
    }


def validate(plan: dict) -> None:
    weeks = plan["weeks"]
    days = plan["days"]

    assert len(weeks) == 156, f"周数应为 156，实际 {len(weeks)}"
    assert len(days) == 156 * 7, f"天数应为 1092，实际 {len(days)}"
    assert [w["week"] for w in weeks] == list(range(1, 157)), "周次必须为 1..156"
    assert [d["week"] for d in days] == [n for n in range(1, 157) for _ in range(7)], "天序错误"

    stage_counts = Counter(w["stage"] for w in weeks)
    assert stage_counts["第一阶段：底座与双线入门"] == 52
    assert stage_counts["第二阶段：交叉深化与工程化"] == 52
    assert stage_counts["第三阶段：深入与作品收敛"] == 52

    for w in weeks:
        n = w["week"]
        assert w.get("commercialCheck"), f"W{n} 缺少商业化检查"
        assert w["meta"]["internshipWindow"] == (n >= 40), f"W{n} 实习窗口标记错误"
        if 40 <= n <= 52:
            assert "大模型实习" in w["meta"]["internshipAction"]
        elif 53 <= n <= 78:
            assert "量化实习" in w["meta"]["internshipAction"]
        elif 79 <= n <= 104:
            assert "第二段实习" in w["meta"]["internshipAction"]
        elif n >= 105:
            assert "转正" in w["meta"]["internshipAction"] or "深度实习" in w["meta"]["internshipAction"]

    for d in days:
        n = d["week"]
        if d["dayOfWeek"] == "周六":
            assert d.get("commercialTask"), f"W{n} 周六缺少商业化任务"
            if n % 13 == 0:
                assert d.get("packagingGuide"), f"W{n} 季度项目缺少商业变现包装指南"
        assert 60 <= d["quantMin"] <= 90, f"W{n} {d['dayOfWeek']} 量化时长越界"
        assert 60 <= d["llmMin"] <= 90, f"W{n} {d['dayOfWeek']} LLM 时长越界"
        total = d["quantMin"] + d["llmMin"]
        assert 150 <= total <= 180, f"W{n} {d['dayOfWeek']} 总时长 {total} 越界"
        if n <= 24:
            for text in [d["quantTask"], d["deliverable"], d.get("commercialTask", ""), *d["exercises"]]:
                for kw in FORBIDDEN:
                    assert kw not in text, f"W{n} 量化侧出现禁用词 {kw}: {text}"

    for n in range(1, 13):
        for d in days[(n - 1) * 7 : n * 7]:
            assert 60 <= d["quantMin"] <= 90
            assert 60 <= d["llmMin"] <= 90

    assert plan["startDate"] == "2026-11-16"
    assert plan["endDate"] == "2029-11-11"
    assert abs(sum(plan["commercialization"]["weights"].values()) - 1.0) < 1e-9, "商业化权重之和必须为 1"

    # 日期连续性与星期对齐
    all_dates = [date.fromisoformat(d["date"]) for d in days]
    assert all_dates[0] == date(2026, 11, 16)
    assert all_dates[-1] == date(2029, 11, 11)
    assert all_dates == [all_dates[0] + timedelta(days=i) for i in range(len(all_dates))]
    for w in weeks:
        ws = date.fromisoformat(w["startDate"])
        assert ws.weekday() == 0, f"W{w['week']} 不是周一开始"
        assert date.fromisoformat(w["endDate"]) == ws + timedelta(days=6)


def build_summary(weeks: list[dict]) -> str:
    lines = [
        "# 36 个月计划 · 156 周摘要",
        "",
        "> 每周一句话：左侧是量化主题与交付，右侧是 LLM 交付；实习窗口在 W40/W53/W79/W105 标注。",
        "> 每周六交付需附商业化三件套：商业可行性、API/CLI 封装、前端/可视化。",
        "> 项目作业必须附《商业变现包装指南》，并给出可访问的云上 Demo 链接。",
        "",
    ]
    current_stage = None
    current_quarter = None
    for w in weeks:
        if w["stage"] != current_stage:
            if current_stage is not None:
                lines.append("")
            lines.append(f"## {w['stage']}")
            lines.append("")
            current_stage = w["stage"]
            current_quarter = None

        if w["quarter"] != current_quarter:
            if current_quarter is not None:
                lines.append("")
            q_weeks = [x for x in weeks if x["quarter"] == w["quarter"]]
            lines.append(f"### {w['quarter']}（W{q_weeks[0]['week']}–W{q_weeks[-1]['week']}）")
            lines.append("")
            current_quarter = w["quarter"]

        n = w["week"]
        marker = {
            40: "【大模型实习投递开启】",
            53: "【量化实习投递开启】",
            79: "【第二段实习投递开启】",
            105: "【转正/深度实习开启】",
        }.get(n, "")
        lines.append(
            f"- W{n}{marker}：{w['quantTopic']} → {w['quantDeliverable']}；"
            f"LLM：{w['llmDeliverable']}。"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="写入 plans/quant-llm-3yr.json")
    args = parser.parse_args()

    plan = build()
    validate(plan)

    summary = build_summary(plan["weeks"])
    summary_path = ROOT / "plans" / "weekly-summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    print("VALIDATION OK")
    print(f"weeks={len(plan['weeks'])} days={len(plan['days'])}")
    print(f"years={plan['startDate']}..{plan['endDate']}")
    print("stage_counts=" + json.dumps(Counter(w["stage"] for w in plan["weeks"]), ensure_ascii=False))
    print(f"summary={summary_path}")

    if args.write:
        out = ROOT / "plans" / "quant-llm-3yr.json"
        out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"written={out}")
        print(f"json_bytes={out.stat().st_size}")
    else:
        print("DRY RUN：未写 JSON；确认阶段划分后加 --write。")


if __name__ == "__main__":
    main()
