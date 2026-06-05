from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


@dataclass
class IdeaBrief:
    theme: str
    core_problem: str
    concise_theme: str
    target_outcome: str
    constraints: list[str]
    non_goals: list[str]
    assumptions: list[str]
    open_questions: list[str]
    search_queries: list[str]
    primary_user_hint: str
    workflow_hint: str
    pain_hint: str
    wedge_hint: str
    markdown: str


@dataclass
class RouteDecision:
    theme: str
    route: str
    route_label: str
    confidence: str
    rationale: list[str]
    confirmation_questions: list[str]
    next_layer: str
    markdown: str


@dataclass
class ResearchPrompt:
    goal: str
    framework: str
    questions: list[str]
    search_queries: list[str]
    output_contract: list[str]
    markdown: str


def build_idea_brief(request: str) -> IdeaBrief:
    labeled = _parse_labeled_sections(request)
    theme = (
        labeled.get("主题")
        or labeled.get("任务描述")
        or labeled.get("目标")
        or _first_sentence(request)
    )
    theme = _clean_text(theme)
    concise_theme = _derive_concise_theme(theme)
    product_signals = _apply_labeled_product_context(
        theme=theme,
        concise_theme=concise_theme,
        labeled=labeled,
        product_signals=_infer_product_signals(theme, concise_theme),
    )
    target_outcome = labeled.get("目标") or labeled.get("输出") or "生成结构化调研方案和共识草稿"

    constraints = [
        value
        for value in [
            labeled.get("对象"),
            labeled.get("输入"),
            labeled.get("约束"),
        ]
        if value
    ]
    non_goals = [
        labeled.get("不做"),
        "不扩展成大而全 research 平台",
        "不把所有逻辑塞进 harvest-tool",
    ]
    assumptions = [
        f"当前主题核心是：{concise_theme}",
        "用户需要先对齐边界，再进入调研层，而不是直接搜。",
        "最终交付应同时包含可读 markdown 和结构化 JSON。",
    ]
    open_questions = [
        "这个想法后面是准备接开发工作、产品定义，还是社会/行业研究？",
        "现在最需要先对齐的是研究边界、对象，还是直接找参考材料？",
    ]

    search_queries = _build_search_queries(theme, request)
    markdown = _render_idea_brief(
        theme=theme,
        target_outcome=target_outcome,
        constraints=[item for item in constraints if item],
        non_goals=[item for item in non_goals if item],
        assumptions=[item for item in assumptions if item],
        open_questions=open_questions,
        search_queries=search_queries,
    )
    return IdeaBrief(
        theme=theme,
        core_problem=product_signals["problem"],
        concise_theme=concise_theme,
        target_outcome=_clean_text(target_outcome),
        constraints=[item for item in constraints if item],
        non_goals=[item for item in non_goals if item],
        assumptions=[item for item in assumptions if item],
        open_questions=open_questions,
        search_queries=search_queries,
        primary_user_hint=product_signals["primary_user"],
        workflow_hint=product_signals["workflow"],
        pain_hint=product_signals["pain"],
        wedge_hint=product_signals["wedge"],
        markdown=markdown,
    )


def _apply_labeled_product_context(
    *,
    theme: str,
    concise_theme: str,
    labeled: dict[str, str],
    product_signals: dict[str, str],
) -> dict[str, str]:
    primary_user = _normalize_primary_user(labeled.get("对象", "")) if labeled.get("对象") else product_signals["primary_user"]
    workflow = labeled.get("输入") or product_signals["workflow"]
    normalized_workaround = _normalize_workaround_phrase(workflow)
    workaround_with_action = _ensure_workaround_action(normalized_workaround)
    goal_phrase = _goal_phrase_from_theme(concise_theme)
    goal_display = _product_goal_display(goal_phrase)
    source_phrase = _source_phrase_from_theme(concise_theme)

    problem = product_signals["problem"]
    pain = product_signals["pain"]
    wedge = product_signals["wedge"]

    if labeled.get("输入") and primary_user != "待确认":
        problem = f"{primary_user}处理这类反馈时，主要还靠 {workaround_with_action}，很难稳定整理成{goal_display}"
        pain = f"{primary_user}还在靠 {workaround_with_action}，既费时也容易漏信息"
    elif labeled.get("输入"):
        problem = f"当前主要靠 {workaround_with_action}，很难稳定整理成{goal_display}"
        pain = f"当前主要靠 {workaround_with_action}，整理和改写成本仍然偏高"
    elif labeled.get("对象") and primary_user != "待确认":
        problem = f"{primary_user} 在“{goal_display}”这件事上仍有明显整理成本"
        pain = problem

    if labeled.get("输入") or labeled.get("对象"):
        wedge = _compose_wedge_hint(source_phrase, goal_phrase)

    return {
        "problem": _clean_text(problem or theme),
        "primary_user": _clean_text(primary_user) or "待确认",
        "workflow": normalized_workaround or product_signals["workflow"],
        "pain": _clean_text(pain or product_signals["pain"]),
        "wedge": _clean_text(wedge or product_signals["wedge"]),
    }


def build_route_decision(request: str) -> RouteDecision:
    labeled = _parse_labeled_sections(request)
    theme = (
        labeled.get("主题")
        or labeled.get("任务描述")
        or labeled.get("目标")
        or _first_sentence(request)
    )
    theme = _clean_text(theme)
    route, route_label, confidence, rationale, confirmation_questions, next_layer = _infer_route(
        request=request,
        theme=theme,
    )
    markdown = _render_route_decision(
        theme=theme,
        route=route,
        route_label=route_label,
        confidence=confidence,
        rationale=rationale,
        confirmation_questions=confirmation_questions,
        next_layer=next_layer,
    )
    return RouteDecision(
        theme=theme,
        route=route,
        route_label=route_label,
        confidence=confidence,
        rationale=rationale,
        confirmation_questions=confirmation_questions,
        next_layer=next_layer,
        markdown=markdown,
    )


def build_research_prompt(brief: IdeaBrief, route_decision: RouteDecision) -> ResearchPrompt:
    framework = _choose_framework(brief, route_decision)
    questions = _build_route_questions(brief, route_decision)
    output_contract = _build_output_contract(route_decision)
    markdown = _render_research_prompt(brief, route_decision, framework, questions, output_contract)
    return ResearchPrompt(
        goal=brief.target_outcome,
        framework=framework,
        questions=questions,
        search_queries=brief.search_queries,
        output_contract=output_contract,
        markdown=markdown,
    )


def run_pipeline(
    request: str,
    *,
    slug: str | None = None,
    discover_count: int = 8,
    harvest_top: int = 4,
    route_override: str | None = None,
    output_root: Path | None = None,
    search_fn: Callable[[str, int], list[dict[str, Any]]] | None = None,
    harvest_fn: Callable[[str, str], dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    route_decision = build_route_decision(request)
    if route_override:
        route_decision = _override_route(route_decision, route_override)
    brief = build_idea_brief(request)
    prompt = build_research_prompt(brief, route_decision)

    workspace_root = _workspace_root()
    # 默认输出目录: <workspace>/task_draft/consensus/
    # 可通过 output_root 参数自定义输出位置
    output_root = output_root or (workspace_root / "task_draft" / "consensus")
    report_dir = output_root / _build_report_slug(slug, now)
    report_dir.mkdir(parents=True, exist_ok=True)

    (report_dir / "route-decision.md").write_text(route_decision.markdown, encoding="utf-8")
    (report_dir / "idea-brief.md").write_text(brief.markdown, encoding="utf-8")
    (report_dir / "research-prompt.md").write_text(prompt.markdown, encoding="utf-8")
    route_layer_outputs = _build_route_layer_outputs(route_decision, brief, prompt, request)
    for filename, content in route_layer_outputs.items():
        (report_dir / filename).write_text(content, encoding="utf-8")

    repos: list[dict[str, Any]] = []
    harvested: list[dict[str, Any]] = []
    if route_decision.route == "github-build":
        if search_fn is None or harvest_fn is None:
            search_fn, harvest_fn = _load_harvest_dependencies()
        repos = _collect_ranked_repos(
            queries=brief.search_queries,
            request=request,
            search_fn=search_fn,
            discover_count=discover_count,
        )
        selected = repos[: max(1, harvest_top)]
        harvested = [harvest_fn(repo["url"], repo["name"]) for repo in selected]

    (report_dir / "candidates.md").write_text(
        _render_candidates(brief.search_queries, repos, route_decision),
        encoding="utf-8",
    )
    (report_dir / "analysis.md").write_text(
        _render_analysis(route_decision, brief, prompt, harvested),
        encoding="utf-8",
    )

    consensus_payload = _build_consensus_payload(route_decision, brief, prompt, harvested, request, now)
    (report_dir / "consensus.md").write_text(
        _render_consensus(consensus_payload, report_dir),
        encoding="utf-8",
    )
    (report_dir / "consensus.json").write_text(
        json.dumps(consensus_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (report_dir / "harvest-results.json").write_text(
        json.dumps(harvested, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "request": request,
        "route": route_decision.route,
        "route_label": route_decision.route_label,
        "route_layer_files": sorted(route_layer_outputs.keys()),
        "report_dir": str(report_dir),
        "queries": brief.search_queries,
        "selected_repos": [repo["project"] for repo in harvested],
        "harvest_consensus_title": consensus_payload["title"],
    }
    (report_dir / "run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def start_session(
    request: str,
    *,
    slug: str | None = None,
    output_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    route_decision = build_route_decision(request)
    brief = build_idea_brief(request)

    workspace_root = _workspace_root()
    # 默认 session 输出目录: <workspace>/task_draft/idea_sessions/
    # 可通过 output_root 参数自定义输出位置
    output_root = output_root or (workspace_root / "task_draft" / "idea_sessions")
    session_dir = output_root / _build_session_slug(slug, now)
    session_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "session_id": session_dir.name,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "request": request,
        "route": route_decision.route,
        "route_label": route_decision.route_label,
        "confidence": route_decision.confidence,
        "stage": "clarify",
        "brief_summary": brief.concise_theme,
        "session_brief": _session_brief_payload(brief, {}),
        "confirmed": {},
        "open_questions": _session_open_questions(route_decision.route, {}),
        "brainstorm_notes": _session_brainstorm_notes(brief, route_decision.route, {}),
        "transcript": [{"role": "user", "content": request}],
    }
    _write_session_files(session_dir, state)
    return {
        "session_dir": str(session_dir),
        "route": state["route"],
        "route_label": state["route_label"],
        "stage": state["stage"],
        "open_questions": state["open_questions"],
    }


def continue_session(
    session_dir: str | Path,
    reply: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    session_path = Path(session_dir).expanduser().resolve()
    state = _load_session_state(session_path)
    state["updated_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
    state["transcript"].append({"role": "user", "content": reply})

    extracted = _extract_session_answers(reply)
    state["confirmed"].update({key: value for key, value in extracted.items() if value})

    chosen_route = state["confirmed"].get("route_preference")
    if chosen_route or state["route"] == "needs-clarification":
        chosen_route = chosen_route or _infer_route_preference(reply)
        if chosen_route:
            refreshed = build_route_decision(f"{state['request']}\n{reply}")
            refreshed = _override_route(refreshed, chosen_route)
            state["route"] = refreshed.route
            state["route_label"] = refreshed.route_label
            state["confidence"] = refreshed.confidence
    brief = build_idea_brief(state["request"])
    state["session_brief"] = _session_brief_payload(brief, state["confirmed"])
    state["brief_summary"] = state["session_brief"]["problem_statement"]
    state["brainstorm_notes"] = _session_brainstorm_notes(brief, state["route"], state["confirmed"])

    state["open_questions"] = _session_open_questions(state["route"], state["confirmed"])
    state["stage"] = "research-ready" if not state["open_questions"] and state["route"] != "needs-clarification" else "clarify"
    _write_session_files(session_path, state)
    return {
        "session_dir": str(session_path),
        "route": state["route"],
        "route_label": state["route_label"],
        "stage": state["stage"],
        "open_questions": state["open_questions"],
        "confirmed": state["confirmed"],
    }


def export_session(
    session_dir: str | Path,
    *,
    slug: str | None = None,
    output_root: Path | None = None,
    search_fn: Callable[[str, int], list[dict[str, Any]]] | None = None,
    harvest_fn: Callable[[str, str], dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now()
    session_path = Path(session_dir).expanduser().resolve()
    state = _load_session_state(session_path)
    if state["route"] == "needs-clarification":
        raise ValueError("Session is still in needs-clarification stage; choose a route before export.")
    remaining = _session_open_questions(state["route"], state["confirmed"])
    if remaining:
        raise ValueError(f"Session is not research-ready yet; remaining questions: {remaining}")

    request = _compose_session_request(state)
    result = run_pipeline(
        request=request,
        slug=slug,
        route_override=state["route"],
        output_root=output_root,
        search_fn=search_fn,
        harvest_fn=harvest_fn,
        now=now,
    )
    (session_path / "export-summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _build_session_slug(slug: str | None, now: datetime) -> str:
    if slug:
        return _slugify(slug)
    return f"idea-session-{now.strftime('%Y%m%d-%H%M%S')}"


def _session_required_fields(route: str) -> list[str]:
    mapping = {
        "github-build": ["repo_goal", "reuse_type", "build_intent"],
        "product-research": ["target_user", "current_workaround", "research_focus"],
        "social-research": ["research_subject", "scope", "research_focus"],
        "needs-clarification": ["route_preference"],
    }
    return mapping.get(route, [])


def _session_question_bank(route: str) -> list[tuple[str, str]]:
    if route == "github-build":
        return [
            ("repo_goal", "你这轮抄 GitHub，最想抄的是实现方式、目录结构，还是产品思路？"),
            ("reuse_type", "你更偏向直接复用、改造复用，还是只做借鉴？"),
            ("build_intent", "后面是准备立刻接开发，还是先做技术可行性判断？"),
        ]
    if route == "product-research":
        return [
            ("target_user", "这轮最想先服务谁？"),
            ("current_workaround", "他们今天怎么凑合解决这个问题？"),
            ("research_focus", "这轮先验证需求和用户场景，还是先看竞品和市场空位？"),
        ]
    if route == "social-research":
        return [
            ("research_subject", "这轮到底在研究哪个现象或人群？"),
            ("scope", "时间、地区或样本人群边界先怎么收？"),
            ("research_focus", "这轮最先看趋势、分群差异，还是案例证据？"),
        ]
    return [
        ("route_preference", "你这轮后面更想接抄 GitHub、做产品定义，还是研究社会/行业现象？"),
        ("research_focus", "你现在最想先看实现参考、用户需求，还是趋势和分群差异？"),
        ("goal_state", "这轮是只想先把路线想清楚，还是已经准备正式进入下一层调研？"),
    ]


def _session_open_questions(route: str, confirmed: dict[str, str]) -> list[str]:
    questions: list[str] = []
    for key, question in _session_question_bank(route):
        if not confirmed.get(key):
            questions.append(question)
    return questions[:3]


def _session_brainstorm_notes(brief: IdeaBrief, route: str, confirmed: dict[str, str]) -> list[str]:
    session_brief = _session_brief_payload(brief, confirmed)
    if route == "product-research":
        return [
            f"先把“{session_brief['problem_statement']}”压成一个更具体的问题定义，而不是直接想功能清单。",
            f"优先怀疑 {session_brief['target_user']} 是否真是最痛的人，而不是默认所有人都痛。",
            f"最小切口先看：{session_brief['wedge']}",
        ]
    if route == "social-research":
        return [
            f"先把“{session_brief['problem_statement']}”拆成现象、对象、边界三层。",
            "先保留相反信号，不要一上来只收单一叙事。",
            "先决定看趋势、分群还是案例，再进正式调研。",
        ]
    if route == "github-build":
        return [
            f"先确认“{session_brief['problem_statement']}”到底要抄实现、抄交互，还是抄整体结构。",
            "先区分直接复用、改造复用和纯借鉴，不要把三者混在一起。",
            "先确认后面是否立刻接开发，再决定搜索深度。",
        ]
    return [
        f"先把“{session_brief['problem_statement']}”压到一条更清楚的下一步动作上。",
        "先决定后面更接实现、产品定义还是社会研究。",
        "先补 1 到 3 个缩边界答案，再进入正式调研层。",
    ]


def _session_brief_payload(brief: IdeaBrief, confirmed: dict[str, str]) -> dict[str, str]:
    target_user = confirmed.get("target_user") or brief.primary_user_hint
    workaround = confirmed.get("current_workaround") or brief.workflow_hint
    focus = confirmed.get("research_focus") or "先明确这轮最先要验证的问题"
    problem_statement = _session_problem_statement(brief, target_user, workaround)
    wedge = brief.wedge_hint

    if confirmed.get("current_workaround"):
        workaround = confirmed["current_workaround"]
    if confirmed.get("research_focus"):
        focus = confirmed["research_focus"]

    return {
        "target_user": target_user,
        "current_workaround": workaround,
        "research_focus": focus,
        "problem_statement": problem_statement,
        "wedge": wedge,
    }


def _session_problem_statement(brief: IdeaBrief, target_user: str, workaround: str) -> str:
    goal_phrase = _goal_phrase_from_theme(brief.concise_theme)
    if target_user != "待确认":
        if any(token in workaround for token in ["手动", "Slack", "飞书", "文档", "表格", "聊天"]):
            return f"{target_user} 现在主要靠手动整理反馈，很难稳定沉成{goal_phrase}"
        if "很难" in brief.core_problem:
            tail = brief.core_problem.split("很难", 1)[1].strip()
            return f"{target_user} 很难 {tail}"
        return f"{target_user} 在“{goal_phrase}”这件事上仍有明显整理成本"
    return brief.core_problem


def _goal_phrase_from_theme(concise_theme: str) -> str:
    if "->" in concise_theme:
        _, right = concise_theme.split("->", 1)
        phrase = _clean_text(right)
    else:
        phrase = _clean_text(concise_theme)
    phrase = re.sub(r"需求的东西$", "可执行需求", phrase)
    phrase = re.sub(r"反馈的东西$", "结构化反馈", phrase)
    return phrase


def _source_phrase_from_theme(concise_theme: str) -> str:
    if "->" in concise_theme:
        left, _ = concise_theme.split("->", 1)
        phrase = _clean_text(left)
        if phrase:
            return phrase
    return _clean_text(concise_theme)


def _compose_wedge_hint(source_phrase: str, goal_phrase: str) -> str:
    source = _clean_text(source_phrase)
    goal = _clean_text(goal_phrase)
    if not source:
        return "先服务一个高频反馈入口和一个固定需求整理场景"
    if not goal:
        return f"先只抓 {source}，自动整理成结构化草稿"
    if "可执行需求" in goal:
        return f"先把{source}自动整理成需求草稿"
    suffix = "" if goal.endswith("草稿") else "草稿"
    return f"先把{source}整理成{goal}{suffix}"


def _product_goal_display(goal_phrase: str) -> str:
    goal = _clean_text(goal_phrase)
    if "可执行需求" in goal:
        return "需求草稿"
    return goal


def _product_theme_display(brief: IdeaBrief) -> str:
    return f"{_source_phrase_from_theme(brief.concise_theme)} -> {_product_goal_display(_goal_phrase_from_theme(brief.concise_theme))}"


def _product_project_title(brief: IdeaBrief) -> str:
    source = _source_phrase_from_theme(brief.concise_theme)
    goal = _product_goal_display(_goal_phrase_from_theme(brief.concise_theme))
    if source and goal == "需求草稿":
        return f"{source}需求整理"
    if source and goal and source != goal:
        return f"{source}{goal}"
    return _product_display_title(brief)


def _product_display_title(brief: IdeaBrief) -> str:
    source = _source_phrase_from_theme(brief.concise_theme)
    goal = _product_goal_display(_goal_phrase_from_theme(brief.concise_theme))
    if source and goal and source != goal:
        return f"把{source}整理成{goal}"
    return brief.concise_theme


def _product_problem_one_liner(brief: IdeaBrief) -> str:
    source = _source_phrase_from_theme(brief.concise_theme)
    goal = _product_goal_display(_goal_phrase_from_theme(brief.concise_theme))
    workflow = _ensure_workaround_action(brief.workflow_hint)
    if brief.primary_user_hint != "待确认" and source and goal:
        return f"{brief.primary_user_hint}需要把{source}更快整理成{goal}，但现在主要还是靠 {workflow}。"
    if source and goal:
        return f"这轮要解决的是：怎样把{source}更快整理成{goal}，而不是继续靠人工手动整理。"
    return brief.core_problem


def _normalize_workaround_phrase(workflow: str) -> str:
    cleaned = _clean_text(workflow)
    cleaned = re.sub(r"^(今天|目前|现在)?主要靠", "", cleaned)
    cleaned = re.sub(r"^(今天|目前|现在)", "", cleaned)
    return _clean_text(cleaned) or _clean_text(workflow)


def _ensure_workaround_action(workflow: str) -> str:
    cleaned = _clean_text(workflow)
    if any(token in cleaned for token in ["整理", "归类", "汇总", "搬运", "改写"]):
        return cleaned
    return f"{cleaned}手动整理"


def _extract_session_answers(reply: str) -> dict[str, str]:
    labels = {
        "route_preference": ["路线", "想走", "方向"],
        "target_user": ["目标用户", "用户", "对象"],
        "current_workaround": ["当前做法", "现状", "workaround", "替代方案"],
        "research_focus": ["这轮重点", "重点", "优先", "研究重点"],
        "repo_goal": ["抄什么", "目标", "实现目标"],
        "reuse_type": ["复用方式", "复用", "借鉴方式"],
        "build_intent": ["后续动作", "开发意图", "接下来做什么"],
        "research_subject": ["研究对象", "主题", "现象"],
        "scope": ["范围", "边界", "样本"],
        "goal_state": ["目标状态", "这轮目标"],
    }
    extracted: dict[str, str] = {}
    for line in reply.splitlines():
        cleaned = line.strip().lstrip("-").strip()
        if not cleaned or "：" not in cleaned and ":" not in cleaned:
            continue
        key_raw, value_raw = re.split(r"[：:]", cleaned, maxsplit=1)
        key = _clean_text(key_raw)
        value = _clean_text(value_raw)
        for field, aliases in labels.items():
            if key in aliases and value:
                extracted[field] = _normalize_route_value(value) if field == "route_preference" else value

    if "route_preference" not in extracted:
        inferred_route = _infer_route_preference(reply)
        if inferred_route:
            extracted["route_preference"] = inferred_route
    if "target_user" not in extracted and "远程团队" in reply:
        extracted["target_user"] = "远程团队里的 PM、产品负责人或项目负责人"
    if "current_workaround" not in extracted and any(token in reply for token in ["手动", "文档", "表格", "Slack", "飞书"]):
        extracted["current_workaround"] = _clean_text(reply)
    if "research_focus" not in extracted and any(token in reply for token in ["需求", "用户", "竞品", "市场", "趋势", "分群"]):
        extracted["research_focus"] = _clean_text(reply)
    return extracted


def _infer_route_preference(reply: str) -> str | None:
    text = reply.lower()
    if any(token in text for token in ["github", "抄项目", "仓库", "实现"]):
        return "github-build"
    if any(token in text for token in ["产品", "需求", "用户", "竞品", "mvp"]):
        return "product-research"
    if any(token in text for token in ["社会", "行业", "趋势", "分群", "公众"]):
        return "social-research"
    return None


def _normalize_route_value(value: str) -> str:
    normalized = _clean_text(value).lower()
    mapping = {
        "github-build": "github-build",
        "github": "github-build",
        "抄github": "github-build",
        "抄 gitHub 项目": "github-build",
        "抄项目": "github-build",
        "github借鉴": "github-build",
        "产品调研": "product-research",
        "产品研究": "product-research",
        "product-research": "product-research",
        "产品定义": "product-research",
        "社会调研": "social-research",
        "社会研究": "social-research",
        "行业研究": "social-research",
        "social-research": "social-research",
    }
    return mapping.get(normalized, value)


def _session_export_theme(state: dict[str, Any]) -> str:
    confirmed = state.get("confirmed", {})
    if state.get("route") == "social-research" and confirmed.get("research_subject"):
        return _clean_text(confirmed["research_subject"])
    brief = build_idea_brief(state["request"])
    return brief.concise_theme


def _compose_session_request(state: dict[str, Any]) -> str:
    lines = [f"主题：{_session_export_theme(state)}", state["request"]]
    confirmed = state.get("confirmed", {})
    if state["route"] == "product-research":
        if confirmed.get("target_user"):
            lines.append(f"对象：{confirmed['target_user']}")
        if confirmed.get("current_workaround"):
            lines.append(f"输入：{confirmed['current_workaround']}")
        if confirmed.get("research_focus"):
            lines.append(f"目标：{confirmed['research_focus']}")
    elif state["route"] == "social-research":
        if confirmed.get("research_subject"):
            lines.append(f"主题：{confirmed['research_subject']}")
        if confirmed.get("scope"):
            lines.append(f"约束：{confirmed['scope']}")
        if confirmed.get("research_focus"):
            lines.append(f"目标：{confirmed['research_focus']}")
    elif state["route"] == "github-build":
        if confirmed.get("repo_goal"):
            lines.append(f"目标：{confirmed['repo_goal']}")
        if confirmed.get("reuse_type"):
            lines.append(f"约束：{confirmed['reuse_type']}")
        if confirmed.get("build_intent"):
            lines.append(f"任务描述：{confirmed['build_intent']}")
    return "\n".join(lines)


def _load_session_state(session_dir: Path) -> dict[str, Any]:
    state_file = session_dir / "session.json"
    return json.loads(state_file.read_text(encoding="utf-8"))


def _write_session_files(session_dir: Path, state: dict[str, Any]) -> None:
    (session_dir / "session.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "analysis.md").write_text(_render_session_analysis(state), encoding="utf-8")
    (session_dir / "brainstorm.md").write_text(_render_session_brainstorm(state), encoding="utf-8")
    (session_dir / "next-questions.md").write_text(_render_session_questions(state), encoding="utf-8")
    (session_dir / "transcript.md").write_text(_render_session_transcript(state), encoding="utf-8")


def _render_session_analysis(state: dict[str, Any]) -> str:
    session_brief = state.get("session_brief", {})
    lines = [
        "# Session Analysis",
        "",
        f"**原始想法：** {state['request']}",
        f"**当前路线：** {state['route_label']}",
        f"**判断置信度：** {state['confidence']}",
        f"**当前阶段：** {state['stage']}",
        f"**当前问题定义：** {session_brief.get('problem_statement', state.get('brief_summary', ''))}",
        "",
        "## 已确认",
    ]
    confirmed = state.get("confirmed", {})
    if confirmed:
        lines.extend([f"- {key}: {value}" for key, value in confirmed.items()])
    else:
        lines.append("- 暂无")
    lines.extend(
        [
            "",
            "## 当前判断",
            f"- 目标用户：{session_brief.get('target_user', '待确认')}",
            f"- 当前做法：{session_brief.get('current_workaround', '待确认')}",
            f"- 这轮重点：{session_brief.get('research_focus', '待确认')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_session_brainstorm(state: dict[str, Any]) -> str:
    lines = ["# Brainstorm", ""]
    lines.extend([f"- {item}" for item in state.get("brainstorm_notes", [])] or ["- 暂无"])
    return "\n".join(lines) + "\n"


def _render_session_questions(state: dict[str, Any]) -> str:
    lines = ["# Next Questions", ""]
    lines.extend([f"- {item}" for item in state.get("open_questions", [])] or ["- 已达到 research-ready"])
    return "\n".join(lines) + "\n"


def _render_session_transcript(state: dict[str, Any]) -> str:
    lines = ["# Transcript", ""]
    for turn in state.get("transcript", []):
        role = "用户" if turn.get("role") == "user" else turn.get("role", "system")
        lines.append(f"## {role}")
        lines.append(turn.get("content", ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _workspace_root() -> Path:
    """
    定位工作区根目录。

    默认假设技能安装在 <workspace>/shared-skills/idea-to-research/ 下，
    通过向上 3 层定位到工作区根目录。

    如果需要自定义工作区位置，可设置环境变量 WORKSPACE_ROOT。
    """
    import os
    if "WORKSPACE_ROOT" in os.environ:
        return Path(os.environ["WORKSPACE_ROOT"]).resolve()
    return Path(__file__).resolve().parents[3]


def _load_harvest_dependencies() -> tuple[
    Callable[[str, int], list[dict[str, Any]]],
    Callable[[str, str], dict[str, Any]],
]:
    """
    动态加载 harvest-tool 依赖。

    默认假设 harvest-tool 安装在 <workspace>/skills/harvest-tool/ 下。
    如果 harvest-tool 位置不同，可设置环境变量 HARVEST_TOOL_PATH。

    如果找不到 harvest-tool，会抛出 ImportError 并给出清晰提示。
    """
    import os
    harvest_root_env = os.environ.get("HARVEST_TOOL_PATH")
    if harvest_root_env:
        harvest_root = Path(harvest_root_env).resolve()
    else:
        harvest_root = _workspace_root() / "skills" / "harvest-tool"

    if not harvest_root.exists():
        raise ImportError(
            f"找不到 harvest-tool 依赖。\n"
            f"期望位置: {harvest_root}\n"
            f"请确认:\n"
            f"1. harvest-tool 已安装在 <workspace>/skills/harvest-tool/\n"
            f"2. 或设置环境变量 HARVEST_TOOL_PATH 指向正确位置\n"
            f"参考: README.md 的依赖章节"
        )

    sys.path.insert(0, str(harvest_root))
    try:
        from scripts.discover import search_github_repos  # type: ignore
        from scripts.harvest import harvest_repo  # type: ignore
    except ImportError as e:
        raise ImportError(
            f"harvest-tool 目录存在，但无法导入所需模块。\n"
            f"harvest-tool 路径: {harvest_root}\n"
            f"原始错误: {e}\n"
            f"请检查 harvest-tool 的完整性和版本兼容性"
        ) from e

    return search_github_repos, harvest_repo


def _parse_labeled_sections(request: str) -> dict[str, str]:
    labels = {"主题", "对象", "输入", "任务描述", "目标", "输出", "约束", "边界", "不做"}
    parsed: dict[str, str] = {}
    for raw_line in request.splitlines():
        line = raw_line.strip().lstrip("，,")
        if "：" not in line and ":" not in line:
            continue
        parts = re.split(r"[：:]", line, maxsplit=1)
        if len(parts) != 2:
            continue
        key = parts[0].strip()
        value = _clean_text(parts[1])
        if key in labels and value:
            parsed[key] = value
    return parsed


def _first_sentence(text: str) -> str:
    chunks = re.split(r"[。！？\n]", text)
    for chunk in chunks:
        chunk = _clean_text(chunk)
        if chunk:
            return chunk
    return _clean_text(text)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" \n\t-")


def _build_search_queries(theme: str, request: str) -> list[str]:
    theme = _clean_text(theme)
    queries = [theme]
    lowered = request.lower()
    theme_lower = theme.lower()

    if any(token in lowered for token in ["prompt", "提示词"]) and "prompt" not in theme_lower and "提示词" not in theme:
        queries.append(f"{theme} prompt")
    if "research" not in theme_lower and "调研" not in theme:
        queries.append(f"{theme} research prompt")
    if any(token in lowered for token in ["skill", "技能"]) and "skill" not in theme_lower and "技能" not in theme:
        queries.append(f"{theme} skill")
    if any(token in lowered for token in ["agent", "智能体"]) and "agent" not in theme_lower and "智能体" not in theme:
        queries.append(f"{theme} agent")
    if any(token in lowered for token in ["想法", "idea", "产品"]):
        queries.append("product idea excavator")
    if any(token in lowered for token in ["调研", "research"]):
        queries.append("deep research prompt")
        queries.append("user research skill")

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = query.lower().strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(query)
    return deduped[:5]


def _derive_concise_theme(theme: str) -> str:
    concise = _clean_text(theme)
    patterns = [
        r"[，,。 ]*先帮我做(产品|社会)?调研.*$",
        r"[，,。 ]*先帮我看看怎么研究.*$",
        r"[，,。 ]*先看看该怎么调研.*$",
        r"[，,。 ]*先判断后面该走哪条调研路线.*$",
        r"[，,。 ]*先帮我判断该走哪条调研路线.*$",
        r"[，,。 ]*后面准备直接接开发.*$",
        r"[，,。 ]*后面直接接开发.*$",
        r"[，,。 ]*准备直接接开发.*$",
    ]
    for pattern in patterns:
        concise = re.sub(pattern, "", concise)
    concise = re.sub(r"^(我有个新想法[，, ]*)", "", concise)
    concise = re.sub(r"^(我想做一个|我想做一款|我想做个|我想做|想做一个|想做个)(?=\S)", "", concise)
    transform_match = re.search(r"帮(?P<user>.+?)把(?P<input>.+?)(沉成|沉淀成|整理成|变成|收成|转成)(?P<output>.+)", concise)
    if transform_match:
        source = _clean_text(transform_match.group("input"))
        outcome = _normalize_transform_output(transform_match.group("output"))
        concise = f"{source} -> {outcome}"
    else:
        generic_transform_match = re.search(r"把(?P<input>.+?)(沉成|沉淀成|整理成|变成|收成|转成)(?P<output>.+)", concise)
        if generic_transform_match:
            source = _clean_text(generic_transform_match.group("input"))
            outcome = _normalize_transform_output(generic_transform_match.group("output"))
            concise = f"{source} -> {outcome}"
    return _clean_text(concise) or theme


def _infer_product_signals(theme: str, concise_theme: str) -> dict[str, str]:
    lowered = theme.lower()
    primary_user = "待确认"
    workflow = "用户先靠聊天记录、表格或文档手动整理"
    pain = "反馈分散、优先级不清、很难直接沉成可执行需求"
    wedge = "先服务一个高频反馈入口和一个固定需求整理场景"

    transform_match = re.search(
        r"帮(?P<user>.+?)把(?P<input>.+?)(沉成|沉淀成|整理成|变成|收成|转成)(?P<output>.+)",
        theme,
    )
    if transform_match:
        user = _clean_text(transform_match.group("user"))
        source = _clean_text(transform_match.group("input"))
        outcome = _normalize_transform_output(transform_match.group("output"))
        primary_user = _normalize_primary_user(user) or primary_user
        workflow = f"{primary_user} 先在聊天工具里收反馈，再手动搬运、归类、改写成需求"
        pain = f"{primary_user} 很难把 {source} 直接沉淀成 {outcome}"
        wedge = f"先只抓 {source}，自动整理成 {outcome} 草稿"
        return {
            "problem": pain,
            "primary_user": primary_user,
            "workflow": workflow,
            "pain": pain,
            "wedge": wedge,
        }

    if any(token in lowered for token in ["slack", "飞书", "discord", "teams", "聊天"]):
        workflow = "团队成员先在聊天工具里丢反馈，再由 PM 或负责人手动汇总"
        pain = "聊天反馈分散在多个线程里，整理成需求既慢又容易漏"
        wedge = "先把一个聊天工具里的零散反馈整理成需求草稿"

    user_match = re.search(r"(面向|给|帮)(?P<user>[^，。 ]{2,20})", theme)
    if user_match:
        primary_user = _normalize_primary_user(_clean_text(user_match.group("user")))
    elif "远程团队" in theme:
        primary_user = "远程团队里的 PM、产品负责人或项目负责人"

    problem = concise_theme
    if concise_theme.endswith("工具") or concise_theme.endswith("产品") or concise_theme.endswith("系统"):
        problem = concise_theme[:-2]
    if primary_user != "待确认" and concise_theme.startswith(primary_user):
        problem = concise_theme

    return {
        "problem": _clean_text(problem),
        "primary_user": primary_user,
        "workflow": workflow,
        "pain": pain,
        "wedge": wedge,
    }


def _normalize_primary_user(user: str) -> str:
    cleaned = _clean_text(user)
    if not cleaned:
        return "待确认"
    normalized_map = {
        "远程团队": "远程团队里的 PM、产品负责人或项目负责人",
        "团队": "团队里的 PM、产品负责人或项目负责人",
        "产品团队": "产品团队里的 PM、产品负责人或项目负责人",
    }
    return normalized_map.get(cleaned, cleaned)


def _normalize_transform_output(output: str) -> str:
    cleaned = _clean_text(output)
    patterns = [
        r"[，,。 ]*先帮我做(产品|社会)?调研.*$",
        r"[，,。 ]*先帮我看看怎么研究.*$",
        r"[，,。 ]*先看看该怎么调研.*$",
        r"[，,。 ]*先判断后面该走哪条调研路线.*$",
        r"[，,。 ]*先帮我判断该走哪条调研路线.*$",
        r"[，,。 ]*后面准备直接接开发.*$",
        r"[，,。 ]*后面直接接开发.*$",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)
    cleaned = re.sub(r"(?i)的?\s*(skill|技能|工具|产品|系统|平台)$", "", cleaned).strip()
    cleaned = re.sub(r"的?东西$", "", cleaned).strip()
    cleaned = re.sub(r"^需求$", "可执行需求", cleaned)
    cleaned = re.sub(r"^需求的东西$", "可执行需求", cleaned)
    cleaned = re.sub(r"(?i)^prd\s*草稿$", "PRD 草稿", cleaned)
    return _clean_text(cleaned)


def _infer_route(
    *,
    request: str,
    theme: str,
) -> tuple[str, str, str, list[str], list[str], str]:
    text = f"{theme}\n{request}".lower()
    github_hits = sum(
        token in text
        for token in ["github", "仓库", "开源", "抄项目", "实现", "开发", "代码", "skill", "agent", "harvest"]
    )
    product_hits = sum(
        token in text
        for token in ["产品", "用户", "需求", "mvp", "功能", "竞品", "痛点", "付费", "定位", "prd"]
    )
    social_hits = sum(
        token in text
        for token in ["社会", "行业", "公众", "舆论", "趋势", "群体", "政策", "文化", "市场现象"]
    )

    scores = {
        "github-build": github_hits,
        "product-research": product_hits,
        "social-research": social_hits,
    }
    route = max(scores, key=scores.get)
    top_score = scores[route]
    sorted_scores = sorted(scores.values(), reverse=True)
    second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0
    confidence = "高" if top_score >= second_score + 2 else "中" if top_score > second_score else "低"

    if top_score == 0 or top_score == second_score:
        route = "needs-clarification"
        route_label = "待澄清 / 先补边界"
        rationale = [
            "当前输入里没有出现足够强的单一路线信号，或者多条路线信号打平。",
            "这时如果硬选一条路，最容易把用户误送进不匹配的下游。",
        ]
        confirmation_questions = [
            "你这轮后面更想接哪一类动作：抄 GitHub 项目、定义产品，还是研究社会/行业现象？",
            "你现在最想先看的是实现参考、用户需求，还是趋势与分群差异？",
            "这轮是只想先看路线判断，还是已经准备正式进入下一层调研？",
        ]
        next_layer = "先补 1 到 3 个缩边界问题，不直接进入正式调研层"
        return route, route_label, "低", rationale, confirmation_questions, next_layer

    if route == "github-build":
        route_label = "GitHub 借鉴 / 后接开发"
        rationale = [
            "输入里明显出现了 GitHub、harvest、开源项目、实现或开发等信号。",
            "这类需求更适合先找成熟项目和实现路径，再接开发工作。",
        ]
        confirmation_questions = [
            "你是想重点抄项目结构和实现方式，还是只想借产品思路？",
            "后面是不是准备直接进入开发，而不是先做产品定义？",
        ]
        next_layer = "GitHub harvest 调研层"
    elif route == "product-research":
        route_label = "产品调研 / 后接产品定义"
        rationale = [
            "输入更像在定义功能、需求、用户和 MVP，而不是直接找代码实现。",
            "这类需求应先对齐问题、目标用户、边界和验证重点，再进入产品调研。",
        ]
        confirmation_questions = [
            "你更想验证需求和用户场景，还是更想找竞品和市场空位？",
            "后面是准备写 PRD / 定 MVP，还是仍然准备直接开做？",
        ]
        next_layer = "产品调研层（discovery / competitive）"
    else:
        route_label = "社会调研 / 后接社会或行业研究"
        rationale = [
            "输入更像是在研究社会现象、行业变化、公众态度或宏观趋势。",
            "这类需求应先明确对象、样本边界、时间范围和研究问题，再进入社会调研。",
        ]
        confirmation_questions = [
            "你要看的重点是趋势、分群差异、案例，还是公众观点分歧？",
            "研究范围是某个地区、某类人群，还是整个行业层面？",
        ]
        next_layer = "社会调研层（趋势 / 分群 / 案例）"

    return route, route_label, confidence, rationale, confirmation_questions, next_layer


def _render_route_decision(
    *,
    theme: str,
    route: str,
    route_label: str,
    confidence: str,
    rationale: list[str],
    confirmation_questions: list[str],
    next_layer: str,
) -> str:
    lines = [
        "# Route Decision",
        "",
        f"**主题：** {theme}",
        f"**推荐路线：** {route_label}",
        f"**内部标识：** `{route}`",
        f"**判断置信度：** {confidence}",
        "",
        "## 为什么这么判断",
    ]
    lines.extend([f"- {item}" for item in rationale])
    lines.append("")
    lines.append("## 还需要和用户确认")
    lines.extend([f"- {item}" for item in confirmation_questions] or ["- 无"])
    lines.append("")
    lines.append("## 后面的调研层")
    lines.append(f"- {next_layer}")
    return "\n".join(lines) + "\n"


def _choose_framework(brief: IdeaBrief, route_decision: RouteDecision) -> str:
    if route_decision.route == "needs-clarification":
        return "前置澄清 + 路线确认"
    if route_decision.route == "github-build":
        return "GitHub 借鉴 / 技术实现路径"
    if route_decision.route == "product-research":
        return "产品发现 + 用户问题定义"
    if route_decision.route == "social-research":
        mode, _ = _infer_social_mode(brief.theme)
        if mode == "explainer":
            return "概念解释 + 教学拆解"
        return "社会 / 行业现象拆解"
    return "概览 + 重点深入"


def _build_route_questions(brief: IdeaBrief, route_decision: RouteDecision) -> list[str]:
    if route_decision.route == "needs-clarification":
        return [
            f"“{brief.theme}”这轮后面到底更接近实现、产品定义，还是社会/行业研究？",
            "现在最缺的是研究边界、对象定义，还是直接可用的参考材料？",
            "如果这轮先不进入正式调研层，最想先确认哪 1 到 3 个问题？",
        ]
    if route_decision.route == "github-build":
        return [
            f"现在有哪些 skill、prompt 或 agent 已经在做“{brief.theme}”相关能力？",
            "这些项目里，哪些负责想法澄清，哪些负责 research prompt 生成，哪些负责调研执行？",
            "如果后面要接开发工作，最值得抄的是哪些实现路径、目录结构和交互方式？",
            "哪些能力可以直接复用，哪些能力只能改造用？",
        ]
    if route_decision.route == "product-research":
        return [
            f"“{brief.theme}”到底是在解决谁的什么问题？",
            "当前最值得先验证的是需求、用户场景、付费意愿，还是竞品空位？",
            "如果后面要接产品定义，最小可验证 wedge 是什么？",
            "后续应该优先走 discovery、competitive，还是两者结合？",
        ]
    mode, _ = _infer_social_mode(brief.theme)
    if mode == "explainer":
        return [
            f"“{brief.theme}”最容易被讲混的概念、边界和常见误区分别是什么？",
            "如果这是给新手讲的一轮介绍，最该先讲清楚的是为什么存在、是什么、包含什么，还是怎么做？",
            "这轮需要把哪些步骤、结构或写法拆开讲，避免用户把不同文件或要求混在一起？",
            "哪些地方应该明确区分定义、作用、流程、注意事项，而不是混成一段泛介绍？",
        ]
    return [
        f"“{brief.theme}”更像社会现象、公众态度、行业变化，还是政策/文化议题？",
        "需要先明确研究对象、时间范围、地区边界和样本人群吗？",
        "如果后面要接社会调研，最关键的是趋势、分群、叙事分歧，还是案例证据？",
        "哪些结论必须保留争议和不确定性，而不能硬下判断？",
    ]


def _build_output_contract(route_decision: RouteDecision) -> list[str]:
    if route_decision.route == "needs-clarification":
        return [
            "输出当前推荐为什么还不能直接进下游",
            "输出 1 到 3 个缩边界问题",
            "输出前置对齐版 research prompt",
            "输出共识草稿 markdown 和 consensus.json",
        ]
    if route_decision.route == "github-build":
        return [
            "输出候选项目清单并标注角色",
            "输出结构化分析，明确可直接用 / 改动用 / 借鉴用",
            "输出共识草稿 markdown",
            "输出标准化 consensus.json",
        ]
    if route_decision.route == "product-research":
        return [
            "输出问题定义、目标用户、非目标和关键假设",
            "输出适合产品调研的 research brief",
            "明确后续应该接 discovery / competitive 哪条调研层",
            "输出共识草稿 markdown 和 consensus.json",
        ]
    mode, _ = _infer_social_mode(route_decision.theme)
    if mode == "explainer":
        return [
            "输出介绍类调研的核心概念、边界、结构和常见误区",
            "输出适合介绍 / 教学 / how-to 的 research brief",
            "明确后续讲解更适合按定义、作用、步骤还是易混点来展开",
            "输出共识草稿 markdown 和 consensus.json",
        ]
    return [
        "输出社会调研的对象、边界、研究问题和风险提示",
        "输出适合社会/行业调研的 research brief",
        "明确后续更适合趋势分析、案例采样还是公众叙事拆解",
        "输出共识草稿 markdown 和 consensus.json",
    ]


def _render_idea_brief(
    *,
    theme: str,
    target_outcome: str,
    constraints: list[str],
    non_goals: list[str],
    assumptions: list[str],
    open_questions: list[str],
    search_queries: list[str],
) -> str:
    lines = [
        "# Idea Brief",
        "",
        f"**主题：** {theme}",
        f"**目标效果：** {target_outcome}",
        "",
        "## 已知约束",
    ]
    lines.extend([f"- {item}" for item in constraints] or ["- 暂无明确约束"])
    lines.append("")
    lines.append("## 本轮不做")
    lines.extend([f"- {item}" for item in non_goals] or ["- 暂无"])
    lines.append("")
    lines.append("## 当前假设")
    lines.extend([f"- {item}" for item in assumptions] or ["- 暂无"])
    lines.append("")
    lines.append("## 待确认问题")
    lines.extend([f"- {item}" for item in open_questions] or ["- 无"])
    lines.append("")
    lines.append("## 初始搜索词（如需 GitHub 借鉴时使用）")
    lines.extend([f"- {item}" for item in search_queries])
    return "\n".join(lines) + "\n"


def _render_research_prompt(
    brief: IdeaBrief,
    route_decision: RouteDecision,
    framework: str,
    questions: list[str],
    output_contract: list[str],
) -> str:
    lines = [
        "# Research Prompt",
        "",
        f"**调研主题：** {brief.theme}",
        f"**推荐路线：** {route_decision.route_label}",
        f"**研究框架：** {framework}",
        "",
        "## 研究目标",
        f"- {brief.target_outcome}",
        "",
        "## 核心研究问题",
    ]
    lines.extend([f"- {item}" for item in questions])
    lines.append("")
    if route_decision.route == "github-build":
        lines.append("## GitHub 搜索词")
        lines.extend([f"- {item}" for item in brief.search_queries])
    else:
        lines.append("## 后续调研层")
        lines.append(f"- {route_decision.next_layer}")
    lines.append("")
    lines.append("## 输出契约")
    lines.extend([f"- {item}" for item in output_contract])
    return "\n".join(lines) + "\n"


def _collect_ranked_repos(
    *,
    queries: list[str],
    request: str,
    search_fn: Callable[[str, int], Any],
    discover_count: int,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for query in queries:
        search_result = search_fn(query, discover_count)
        repos = search_result.get("repos", []) if isinstance(search_result, dict) else search_result
        for repo in repos:
            key = repo.get("name") or repo.get("full_name") or repo.get("url")
            if not key:
                continue
            candidate = {
                "name": repo.get("name") or repo.get("full_name") or key,
                "url": repo.get("url", ""),
                "description": repo.get("description", ""),
                "stars": int(repo.get("stars", 0) or 0),
                "language": repo.get("language", "") or "",
                "last_commit": repo.get("last_commit", "") or "",
            }
            candidate["score"] = _score_repo(candidate, request)
            previous = merged.get(key)
            if previous is None or candidate["score"] > previous["score"]:
                merged[key] = candidate
    return sorted(merged.values(), key=lambda item: (item["score"], item["stars"]), reverse=True)


def _score_repo(repo: dict[str, Any], request: str) -> float:
    text = " ".join([repo.get("name", ""), repo.get("description", ""), request]).lower()
    hits = 0
    for token in ["idea", "想法", "prompt", "research", "调研", "skill", "agent", "discovery"]:
        if token in text:
            hits += 1
    stars = int(repo.get("stars", 0) or 0)
    return hits * 10 + math.log10(stars + 1) * 5


def _build_report_slug(slug: str | None, now: datetime) -> str:
    if slug:
        return _slugify(slug)
    return f"idea-to-research-{now.strftime('%Y%m%d-%H%M%S')}"


def _slugify(value: str) -> str:
    value = value.strip().lower().replace(" ", "-")
    value = re.sub(r"[^a-z0-9\-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "idea-to-research"


def _render_candidates(
    queries: list[str],
    repos: list[dict[str, Any]],
    route_decision: RouteDecision,
) -> str:
    lines = [
        "# Candidates",
        "",
        f"**当前路线：** {route_decision.route_label}",
        "",
    ]
    if route_decision.route == "needs-clarification":
        lines.append("## 当前不进入候选阶段")
        lines.append("- 这轮先补边界，不直接进入 GitHub、产品或社会调研下游。")
        lines.append("- 等用户确认路线后，再决定是否需要候选仓库或更深调研包。")
        return "\n".join(lines) + "\n"

    if route_decision.route != "github-build":
        lines.append("## 当前不进入 GitHub 候选阶段")
        lines.append(f"- 先完成前置对齐，后续进入：{route_decision.next_layer}")
        lines.append("- 如果用户确认要抄项目再接开发，再回到 GitHub 借鉴路线。")
        return "\n".join(lines) + "\n"

    lines.append("## 搜索词")
    lines.extend([f"- {item}" for item in queries])
    lines.append("")
    lines.append("## 候选仓库")
    if not repos:
        lines.append("- 未发现候选仓库")
        return "\n".join(lines) + "\n"
    for index, repo in enumerate(repos, start=1):
        lines.append(f"{index}. `{repo['name']}` — ★{repo['stars']} — {repo['description'] or '无描述'}")
        lines.append(f"   链接: {repo['url']}")
    return "\n".join(lines) + "\n"


def _render_analysis(
    route_decision: RouteDecision,
    brief: IdeaBrief,
    prompt: ResearchPrompt,
    harvested: list[dict[str, Any]],
) -> str:
    lines = [
        "# Analysis",
        "",
        "## 前置对齐判断",
        f"- 当前更推荐路线：`{route_decision.route}` / {route_decision.route_label}",
        f"- 后续调研层：{route_decision.next_layer}",
    ]
    lines.extend([f"- {item}" for item in route_decision.rationale])
    lines.append("")

    if route_decision.route == "needs-clarification":
        lines.extend(
            [
                "## 说明",
                "- 当前不适合直接进入任何一条正式调研路线。",
                "- 这轮先把用户真正想接的下一步动作问清楚，再决定后面走哪条链路。",
                f"- 当前 research prompt 已按 `{prompt.framework}` 组织，适合作为前置澄清清单。",
            ]
        )
    elif route_decision.route == "github-build":
        lines.extend(
            [
                "## 本地链路判断",
                "- `research-discovery` 适合前置澄清和边界收敛。",
                "- `harvest-tool` 适合 GitHub 发现、抓取和共识输出。",
                "- 中间层需要一个显式的 `idea-brief -> research-prompt` 转换。",
                "",
                "## 候选项目分工",
            ]
        )
        if not harvested:
            lines.append("- 暂无 harvested 仓库，无法分析。")
        for repo in harvested:
            role = _classify_repo_role(repo)
            lines.append(f"- `{repo['project']}`: {role}")
            lines.append(f"  适配点: {_repo_summary(repo)}")
    else:
        lines.extend(
            [
                "## 说明",
                "- 当前阶段先停在对齐和路由，不默认进入 GitHub harvest。",
                "- 等用户确认研究对象和边界后，再进入对应调研层。",
                f"- 当前 research prompt 已按 `{prompt.framework}` 组织，适合作为下一轮调研输入。",
            ]
        )

    lines.extend(
        [
            "",
            "## 推荐链路",
            "- 先用 `route-decision.md` 和用户确认到底走哪条路线。",
            f"- 再把“{brief.theme}”收敛为 `idea-brief.md`。",
            f"- 再基于 `{prompt.framework}` 生成 `research-prompt.md`。",
            f"- 最后进入 `{route_decision.next_layer}`。",
        ]
    )
    return "\n".join(lines) + "\n"


def _repo_summary(repo: dict[str, Any]) -> str:
    readme = repo.get("readme", {}).get("raw", "")
    description = repo.get("url", "")
    snippet = _clean_text(readme[:180]).replace("\n", " ")
    return snippet or description or "见 README"


def _classify_repo_role(repo: dict[str, Any]) -> str:
    text = " ".join(
        [
            repo.get("project", ""),
            repo.get("readme", {}).get("raw", ""),
            repo.get("url", ""),
        ]
    ).lower()
    if any(token in text for token in ["interview", "discovery", "prd", "idea"]):
        return "想法澄清 / 产品发现"
    if any(token in text for token in ["survey", "synthesis", "user research"]):
        return "研究计划 / 结果综合"
    if any(token in text for token in ["deep research", "search", "report"]):
        return "调研执行引擎"
    if any(token in text for token in ["prompt", "template", "framework"]):
        return "调研提示词生成 / 研究框架"
    return "通用参考"


def _build_consensus_payload(
    route_decision: RouteDecision,
    brief: IdeaBrief,
    prompt: ResearchPrompt,
    harvested: list[dict[str, Any]],
    request: str,
    now: datetime,
) -> dict[str, Any]:
    direct = ["本地 `research-discovery` 的问题澄清和边界收敛"]
    if route_decision.route == "github-build":
        direct.append("本地 `harvest-tool` 的 discover / harvest / consensus 流程")
    adapt: list[str] = []
    borrow: list[str] = []

    for repo in harvested:
        role = _classify_repo_role(repo)
        entry = f"`{repo['project']}`：{role}"
        if "提示词" in role or "框架" in role:
            direct.append(entry)
        elif "想法澄清" in role or "产品发现" in role or "执行引擎" in role:
            adapt.append(entry)
        else:
            borrow.append(entry)

    if not harvested and route_decision.route == "github-build":
        borrow.append("本轮未找到足够候选仓库，后续需手动补充参考源")

    if route_decision.route == "needs-clarification":
        how_to_build = (
            "先生成 `route-decision.md`，明确为什么这轮还不能直接进 GitHub、产品或社会调研下游；"
            "再生成 `idea-brief.md`，把主题、边界、对象、非目标和关键假设先收拢；"
            "再生成前置澄清版 `research-prompt.md`，把最关键的 1 到 3 个缩边界问题列出来；"
            "本轮停在路线确认层，不默认进入正式调研包。"
        )
    elif route_decision.route == "github-build":
        how_to_build = (
            "先生成 `route-decision.md`，确认当前是 GitHub 借鉴并准备接开发工作；"
            "再生成 `idea-brief.md` 对齐主题、边界、假设和本轮不做；"
            "再生成 `research-prompt.md`，明确研究框架、核心问题、GitHub 搜索词和输出契约；"
            "然后调用现有 `harvest-tool` 做 discover / harvest / consensus；"
            "最终把报告统一落到 `task_draft/consensus/<slug>/`。"
        )
    else:
        how_to_build = (
            "先生成 `route-decision.md`，确认当前到底是产品调研还是社会调研；"
            "再生成 `idea-brief.md`，把主题、边界、对象、非目标和关键假设收敛清楚；"
            "再生成 route-specific 的 `research-prompt.md`，作为后续调研层输入；"
            f"本轮先停在 `{route_decision.next_layer}` 入口，不默认进入 GitHub harvest。"
        )

    return {
        "title": f"想法转调研共识 - {now.strftime('%Y-%m-%d')}",
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "做什么": f"围绕“{brief.theme}”建立一个带前置交流层的 skill，先判断是 GitHub 借鉴、产品调研还是社会调研，再进入对应调研层。",
        "为什么做": "用户输入一个想法后，不应该默认直接搜 GitHub。必须先和用户对齐边界，明确后面是接开发工作、接产品定义，还是接社会调研，再进入对应执行层。",
        "目标": [
            brief.target_outcome,
            "让用户先看到路线判断和待确认问题",
            "保留 `route-decision.md`、`idea-brief.md` 和 `research-prompt.md` 三个中间产物，方便后续迭代",
        ],
        "从哪里抄": {
            "直接用": direct,
            "改动用": adapt,
            "借鉴用": borrow,
        },
        "怎么做": how_to_build,
        "实施优先级": [
            "P0：先做薄封装 skill",
            "P1：固定 `route-decision.md`、`idea-brief.md` 和 `research-prompt.md` 产物",
            "P1：只有 GitHub 借鉴路线默认接入 `harvest-tool`",
            "P2：再考虑扩到更深的递归 research",
        ],
        "不确定性": [
            "后续是否要把产品调研直接接到 `research-discovery / research-competitive`",
            "后续是否要单独补一条社会调研模板包",
            "未来是否还要扩展为全网 deep research",
        ],
        "风险": [
            "如果把所有职责都塞给 `harvest-tool`，工具边界会发散",
            "如果没有前置交流层，用户会被错误地送进不匹配的调研链",
            "如果没有中间产物文件，后续很难复盘和重跑",
            "如果直接做重平台，会超出当前 MVP 范围",
        ],
        "request": request,
        "research_framework": prompt.framework,
        "route": route_decision.route,
        "route_label": route_decision.route_label,
    }


def _render_consensus(payload: dict[str, Any], report_dir: Path) -> str:
    lines = [
        f"# {payload['title']}",
        "",
        f"> 生成时间: {payload['generated_at']}",
        f"> 输出位置: `{report_dir}`",
        "",
        "## 一句话结论",
        payload["做什么"],
        "",
        "## 为什么做",
        payload["为什么做"],
        "",
        "## 目标",
    ]
    lines.extend([f"- {item}" for item in payload["目标"]])
    lines.append("")
    lines.append("## 从哪里抄")
    for bucket in ["直接用", "改动用", "借鉴用"]:
        lines.append(f"### {bucket}")
        values = payload["从哪里抄"].get(bucket, [])
        lines.extend([f"- {item}" for item in values] or ["- 无"])
        lines.append("")
    lines.extend(
        [
            "## 怎么做",
            payload["怎么做"],
            "",
            "## 实施优先级",
        ]
    )
    lines.extend([f"- {item}" for item in payload["实施优先级"]])
    lines.append("")
    lines.append("## 不确定性")
    lines.extend([f"- {item}" for item in payload["不确定性"]])
    lines.append("")
    lines.append("## 风险")
    lines.extend([f"- {item}" for item in payload["风险"]])
    return "\n".join(lines) + "\n"


def _override_route(route_decision: RouteDecision, route_override: str) -> RouteDecision:
    overrides = {
        "github-build": "GitHub 借鉴 / 后接开发",
        "product-research": "产品调研 / 后接产品定义",
        "social-research": "社会调研 / 后接社会或行业研究",
    }
    if route_override not in overrides:
        raise ValueError(f"Unsupported route override: {route_override}")
    if route_override == "github-build":
        rationale = [
            "这轮被显式指定为先走 GitHub 借鉴层，优先找实现路径、目录结构和可复用做法。",
            "因此这里不继续按产品定义或社会研究去展开。",
        ]
        confirmation_questions = [
            "这轮最想抄的是实现方式、项目结构，还是产品思路？",
            "后面是不是准备直接接开发，而不是先补产品定义？",
        ]
        next_layer = "GitHub harvest 调研层"
    elif route_override == "product-research":
        rationale = [
            "这轮被显式指定为先走产品调研层，优先对齐用户、问题、场景和最小切口。",
            "因此这里不继续按代码借鉴或社会现象研究去展开。",
        ]
        confirmation_questions = [
            "这轮更想先验证需求和用户场景，还是先看竞品与市场空位？",
            "后面是准备写 PRD / 定 MVP，还是仍然想直接开做？",
        ]
        next_layer = "产品调研层（discovery / competitive）"
    else:
        mode, label = _infer_social_mode(route_decision.theme)
        rationale = [
            "这轮被显式指定为先走社会 / 内容研究层，优先把主题讲法、对象和研究边界收清楚。",
            f"按当前主题判断，内部更适合先用“{label}”这一类研究展开。",
        ]
        if mode == "explainer":
            confirmation_questions = [
                "这轮最该先讲清楚的是为什么存在、是什么、包含什么，还是怎么做？",
                "哪些概念、文件或步骤最容易被新手混淆？",
            ]
            next_layer = "社会调研层（介绍拆解）"
        else:
            confirmation_questions = [
                "你要看的重点是趋势、分群差异、案例，还是公众观点分歧？",
                "研究范围是某个地区、某类人群，还是整个行业层面？",
            ]
            next_layer = "社会调研层（趋势 / 分群 / 案例）"
    rationale.append(f"用户或调用方显式指定路线为 `{route_override}`。")
    markdown = _render_route_decision(
        theme=route_decision.theme,
        route=route_override,
        route_label=overrides[route_override],
        confidence="人工指定",
        rationale=rationale,
        confirmation_questions=confirmation_questions,
        next_layer=next_layer,
    )
    return RouteDecision(
        theme=route_decision.theme,
        route=route_override,
        route_label=overrides[route_override],
        confidence="人工指定",
        rationale=rationale,
        confirmation_questions=confirmation_questions,
        next_layer=next_layer,
        markdown=markdown,
    )


def _build_route_layer_outputs(
    route_decision: RouteDecision,
    brief: IdeaBrief,
    prompt: ResearchPrompt,
    request: str,
) -> dict[str, str]:
    if route_decision.route == "needs-clarification":
        return {
            "clarification-brief.md": _render_clarification_brief(brief, prompt, route_decision),
        }
    if route_decision.route == "product-research":
        mode, label = _infer_product_mode(request)
        outputs = {
            "product-route.md": _render_product_route(mode, label, route_decision, brief),
            "product-research-brief.md": _render_product_research_brief(mode, label, brief, prompt),
        }
        outputs.update(_build_product_package(mode, brief))
        return outputs
    if route_decision.route == "social-research":
        mode, label = _infer_social_mode(request)
        outputs = {
            "social-route.md": _render_social_route(mode, label, route_decision, brief),
            "social-research-brief.md": _render_social_research_brief(mode, label, brief, prompt),
        }
        outputs.update(_build_social_package(mode, brief))
        return outputs
    return {
        "github-build-brief.md": _render_github_build_brief(route_decision, brief, prompt),
    }


def _infer_product_mode(request: str) -> tuple[str, str]:
    text = request.lower()
    competitive_hits = sum(token in text for token in ["竞品", "竞争", "市场", "替代", "pricing", "价格"])
    discovery_hits = sum(token in text for token in ["用户", "需求", "痛点", "mvp", "场景", "验证"])
    if competitive_hits > discovery_hits:
        return "competitive", "竞品 / 市场位势"
    if discovery_hits > competitive_hits:
        return "discovery", "需求 / 用户发现"
    return "hybrid", "需求发现 + 竞品扫描"


def _infer_social_mode(request: str) -> tuple[str, str]:
    text = request.lower()
    explainer_hits = sum(
        token in text
        for token in [
            "怎么写",
            "怎么做",
            "怎么用",
            "如何",
            "入门",
            "科普",
            "介绍",
            "教程",
            "教学",
            "基础",
            "原理",
            "是什么",
            "是什么?",
            "是什么？",
            "指南",
            "说明",
            "步骤",
            "写法",
        ]
    )
    trend_hits = sum(token in text for token in ["趋势", "变化", "发展", "行业"])
    population_hits = sum(token in text for token in ["人群", "青年", "用户群", "群体", "分层"])
    case_hits = sum(token in text for token in ["案例", "事件", "样本", "故事"])
    if explainer_hits >= max(trend_hits, population_hits, case_hits) and explainer_hits > 0:
        return "explainer", "介绍 / 教学拆解"
    if trend_hits >= population_hits and trend_hits >= case_hits:
        return "trend", "趋势 / 宏观变化"
    if population_hits >= trend_hits and population_hits >= case_hits:
        return "population", "分群 / 人群差异"
    return "case", "案例 / 样本观察"


def _render_product_route(
    mode: str,
    label: str,
    route_decision: RouteDecision,
    brief: IdeaBrief,
) -> str:
    project_title = _product_project_title(brief)
    display_title = _product_display_title(brief)
    next_step = {
        "discovery": "先把问题、目标用户和验证计划收紧，再决定要不要往更细的 PRD 走。",
        "competitive": "先看竞品格局、替代方案和价格带，再决定这个切口值不值得做。",
        "hybrid": "先把问题和用户收紧，再补一轮竞品扫描，看有没有值得进的位置。",
    }[mode]
    lines = [
        "# Product Route",
        "",
        f"**项目标题：** {project_title}",
        f"**这轮标题：** {display_title}",
        f"**推荐产品模式：** {label}",
        "",
        "## 这轮为什么先走产品调研",
        "- 这件事现在更像要先想清楚用户、场景和问题，而不是立刻找代码实现。",
        f"- 放到产品调研里看，这轮更适合先走：{label}。",
        "",
        "## 这轮建议怎么往下走",
        f"- {next_step}",
        "- 先把谁最痛、现在怎么凑合、为什么现有办法不够用讲清楚。",
        "- 再决定是继续收需求，还是补竞品和市场空位。",
    ]
    return "\n".join(lines) + "\n"


def _render_product_research_brief(
    mode: str,
    label: str,
    brief: IdeaBrief,
    prompt: ResearchPrompt,
) -> str:
    project_title = _product_project_title(brief)
    display_title = _product_display_title(brief)
    one_liner = _product_problem_one_liner(brief)
    focus = {
        "discovery": ["先确认谁最痛", "先确认痛点是不是高频", "先看用户现在怎么凑合", "先判断最小切口该落在哪里"],
        "competitive": ["先盘清市场上谁在做", "先看用户为什么选他们", "先找差异化机会", "先判断这个位子值不值得进"],
        "hybrid": ["先定义目标用户和痛点", "再补竞品扫描", "最后判断最小切口和差异化机会"],
    }[mode]
    lines = [
        "# Product Research Brief",
        "",
        f"**项目标题：** {project_title}",
        f"**这轮标题：** {display_title}",
        f"**一句话问题定义：** {one_liner}",
        f"**当前模式：** {label}",
        f"**研究框架：** {prompt.framework}",
        "",
        "## 这轮重点先看什么",
    ]
    lines.extend([f"- {item}" for item in focus])
    lines.extend(
        [
            "",
            "## 这轮先产出什么",
            "- `problem-statement.md`",
            "- `target-user.md`",
            "- `assumptions-log.md`",
            "- `validation-plan.md`",
            "- 如需要，再补 `competitor-scan.md`",
            "",
            "## 进入下一层前先答清楚",
            "- 这个东西到底先帮谁解决问题？",
            "- 他们今天到底怎么凑合？",
            "- 这轮到底先验证需求，还是先看竞品空位？",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_product_package(mode: str, brief: IdeaBrief) -> dict[str, str]:
    outputs: dict[str, str] = {}
    if mode in {"discovery", "hybrid"}:
        outputs.update(
            {
                "problem-statement.md": _render_problem_statement(brief),
                "target-user.md": _render_target_user(brief),
                "assumptions-log.md": _render_assumptions_log(brief),
                "validation-plan.md": _render_validation_plan(brief),
                "mvp-wedge.md": _render_mvp_wedge(brief),
                "prd-outline.md": _render_prd_outline(brief),
                "reader-brief.md": _render_product_reader_brief(brief),
                "discovery-report.md": _render_discovery_report(brief),
            }
        )
    if mode in {"competitive", "hybrid"}:
        outputs.update(
            {
                "market-question.md": _render_market_question(brief),
                "competitor-scope.md": _render_competitor_scope(brief),
                "competitor-list.csv": _render_competitor_list_csv(),
                "feature-matrix.csv": _render_feature_matrix_csv(),
                "pricing-landscape.csv": _render_pricing_landscape_csv(),
                "sentiment-summary.md": _render_sentiment_summary(brief),
                "gtm-signals.md": _render_gtm_signals(brief),
                "competitors-report.md": _render_competitors_report(brief),
                "battle-cards.md": _render_battle_cards(brief),
            }
        )
    outputs["final-report.md"] = _render_product_final_report(mode, brief)
    return outputs


def _build_social_package(mode: str, brief: IdeaBrief) -> dict[str, str]:
    return {
        "research-scope.md": _render_social_research_scope(mode, brief),
        "population-or-case-definition.md": _render_population_or_case_definition(mode, brief),
        "evidence-log.md": _render_social_evidence_log(mode, brief),
        "uncertainty-and-bias.md": _render_uncertainty_and_bias(mode, brief),
        "reader-brief.md": _render_social_reader_brief(mode, brief),
        "final-report.md": _render_social_final_report(mode, brief),
    }


def _render_social_route(
    mode: str,
    label: str,
    route_decision: RouteDecision,
    brief: IdeaBrief,
) -> str:
    next_step = {
        "explainer": "优先把核心概念、文件组成、作用和写法步骤拆开讲清楚，再补常见误区和判断标准。",
        "trend": "优先做趋势拆解，明确时间范围、地区边界和变化驱动因素。",
        "population": "优先做人群分层，明确比较对象、样本边界和关键差异维度。",
        "case": "优先做案例采样，明确样本选择标准和观察口径。",
    }[mode]
    wrap_up = (
        "- 再决定讲解顺序更适合按为什么存在、是什么、包含什么、怎么写，还是按常见错误来展开。"
        if mode == "explainer"
        else "- 再决定是看趋势、看分群差异，还是看案例证据。"
    )
    lines = [
        "# Social Route",
        "",
        f"**主题：** {brief.theme}",
        f"**推荐社会调研模式：** {label}",
        f"**内部标识：** `{mode}`",
        "",
        "## 为什么是这条社会调研路",
        "- 当前主题更像社会/行业研究，而不是产品定义或代码实现。",
        f"- 在社会调研内部，更推荐先走：{label}。",
        "",
        "## 建议后续动作",
        f"- {next_step}",
        "- 先明确研究对象、样本人群、时间范围和不研究的边界。",
        wrap_up,
    ]
    return "\n".join(lines) + "\n"


def _render_social_research_brief(
    mode: str,
    label: str,
    brief: IdeaBrief,
    prompt: ResearchPrompt,
) -> str:
    focus = {
        "explainer": ["这个主题为什么存在", "核心定义和边界是什么", "关键组成部分或文件分别是什么", "新手最容易混淆和写错的地方在哪里"],
        "trend": ["过去到现在发生了什么变化", "变化由什么驱动", "有哪些相反信号", "未来可能怎么演化"],
        "population": ["要比较哪几类人群", "差异维度是什么", "结论能不能泛化", "哪些差异只是样本偏差"],
        "case": ["样本怎么选", "案例之间共性是什么", "是否存在反例", "案例能支持多大结论范围"],
    }[mode]
    entry_questions = [
        "- 研究对象是谁？",
        "- 时间和地区边界是什么？",
        "- 这轮最关心趋势、分群差异，还是案例证据？",
    ]
    if mode == "explainer":
        entry_questions = [
            "- 先给新手讲清哪三个最基础的问题？",
            "- 哪些定义、文件或步骤最容易被混淆？",
            "- 这轮更适合按概念、作用、结构还是写法来组织内容？",
        ]
    lines = [
        "# Social Research Brief",
        "",
        f"**主题：** {brief.theme}",
        f"**当前模式：** {label}",
        f"**研究框架：** {prompt.framework}",
        "",
        "## 本轮研究重点",
    ]
    lines.extend([f"- {item}" for item in focus])
    lines.extend(
        [
            "",
            "## 建议输出",
            "- `research-scope.md`",
            "- `population-or-case-definition.md`",
            "- `evidence-log.md`",
            "- `uncertainty-and-bias.md`",
            "- `reader-brief.md`",
            "",
            "## 进入下一层前要先回答",
        ]
    )
    lines.extend(entry_questions)
    return "\n".join(lines) + "\n"


def _render_clarification_brief(
    brief: IdeaBrief,
    prompt: ResearchPrompt,
    route_decision: RouteDecision,
) -> str:
    lines = [
        "# Clarification Brief",
        "",
        f"**主题：** {brief.theme}",
        f"**当前状态：** {route_decision.route_label}",
        f"**研究框架：** {prompt.framework}",
        "",
        "## 为什么先停在这里",
    ]
    lines.extend([f"- {item}" for item in route_decision.rationale])
    lines.extend(
        [
            "",
            "## 这轮先补什么",
            "- 明确后面更想接实现、产品定义，还是社会/行业研究",
            "- 明确这轮最先要解决的是边界问题、参考材料，还是正式调研",
            "- 明确是否只看路线判断，还是准备正式落盘进入下一层",
            "",
            "## 先回答这几个问题",
        ]
    )
    lines.extend([f"- {item}" for item in route_decision.confirmation_questions])
    return "\n".join(lines) + "\n"


def _render_github_build_brief(
    route_decision: RouteDecision,
    brief: IdeaBrief,
    prompt: ResearchPrompt,
) -> str:
    lines = [
        "# GitHub Build Brief",
        "",
        f"**主题：** {brief.theme}",
        f"**研究框架：** {prompt.framework}",
        "",
        "## 本轮目标",
        "- 找成熟项目和实现路径",
        "- 判断哪些能直接抄，哪些只能改造用",
        "- 给后续开发提供结构化共识",
    ]
    return "\n".join(lines) + "\n"


def _render_problem_statement(brief: IdeaBrief) -> str:
    theme_display = _product_theme_display(brief)
    return "\n".join(
        [
            "# Problem Statement",
            "",
            f"- 这次要解决的核心问题: {brief.core_problem}",
            f"- 为什么现在值得看: 像“{theme_display}”这类需求，往往已经有高频反馈流，但整理动作还卡在人手上。",
            f"- 谁最受影响: {brief.primary_user_hint}",
            f"- 他们现在怎么凑合: {brief.workflow_hint}",
            f"- 这轮先验证什么: {brief.target_outcome}",
            "",
        ]
    )


def _render_target_user(brief: IdeaBrief) -> str:
    display_title = _product_display_title(brief)
    return "\n".join(
        [
            "# Target User",
            "",
            f"- 主要用户: {brief.primary_user_hint}",
            "- 次要相关方: 可能包括研发负责人、设计负责人或直接接收反馈的人",
            f"- 典型触发场景: 团队需要开始处理“{display_title}”这件事的时候",
            f"- 他们现在怎么做: {brief.workflow_hint}",
            f"- 当前最高成本: {brief.pain_hint}",
            "",
        ]
    )


def _render_assumptions_log(brief: IdeaBrief) -> str:
    rows = [
        "| Assumption | Why we believe it | Evidence today | How to validate |",
        "|---|---|---|---|",
        f"| 用户确实在为“{brief.theme}”相关问题付出成本 | 这是本轮想做产品调研的前提 | 暂无硬证据 | 访谈 5-8 个目标用户，确认问题频率和痛感 |",
        "| 用户愿意迁移到新的解决方案 | 有新功能想法说明用户现有方案可能不够好 | 仅为推测 | 验证用户当前凑合方案和切换阻力 |",
        "| 最小 wedge 可以独立产生价值 | 产品方向需要先从小切口试 | 暂无 | 先定义单一用户、单一任务、单一触发场景 |",
    ]
    return "# Assumptions Log\n\n" + "\n".join(rows) + "\n"


def _render_validation_plan(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# Validation Plan",
            "",
            "## 第一轮最低成本验证",
            "- 做 5-8 个目标用户访谈",
            "- 收集 3 个真实凑合方案",
            "- 验证痛点是否高频、是否高成本、是否高情绪摩擦",
            "",
            "## 成功信号",
            "- 用户能清楚描述痛点",
            "- 用户已经有明确的凑合方案，且明显不满意",
            "- 用户愿意尝试最小版本或继续访谈",
            "",
            "## 失败信号",
            "- 问题只是偶发抱怨，不影响行为",
            "- 用户没有明确的凑合方案",
            "- 用户虽然认可想法，但不愿付出切换成本",
            "",
        ]
    )


def _render_mvp_wedge(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# MVP Wedge",
            "",
            f"- 先做什么: {brief.wedge_hint}",
            "- 不做什么: 不同时覆盖多个用户群、多条工作流和完整后台能力。",
            "- 为什么这是最小切口: 先验证问题和使用意愿，再决定是否扩面。",
            "- 若假设错了,最先会错在哪里: 用户其实没那么痛，或者切换成本远高于想象。",
            "",
        ]
    )


def _render_prd_outline(brief: IdeaBrief) -> str:
    display_title = _product_display_title(brief)
    return "\n".join(
        [
            "# PRD Outline",
            "",
            "## 用户",
            f"- 主要用户: {brief.primary_user_hint}",
            "",
            "## 场景",
            f"- 核心场景: {display_title}",
            "",
            "## 核心任务",
            f"- 用户最想完成的一件事: 更快把零散反馈整理成可直接讨论的需求草稿",
            "",
            "## 成功指标",
            "- 首次完成率",
            "- 重复使用率",
            "- 用户主观价值判断",
            "",
            "## 非目标",
            "- 本轮不覆盖多场景扩面",
            "- 本轮不做完整平台化",
            "",
        ]
    )


def _render_product_reader_brief(brief: IdeaBrief) -> str:
    project_title = _product_project_title(brief)
    display_title = _product_display_title(brief)
    one_liner = _product_problem_one_liner(brief)
    return "\n".join(
        [
            "# 这份产品调研在讲什么",
            "",
            f"**项目标题：** {project_title}",
            f"**这轮标题：** {display_title}",
            f"**一句话问题定义：** {one_liner}",
            "",
            f"## 1. 这轮到底在解决什么\n- {brief.core_problem}",
            f"## 2. 现在最可能谁最痛\n- 初步判断是 {brief.primary_user_hint}",
            f"## 3. 他们今天怎么凑合\n- {brief.workflow_hint}",
            "## 4. 为什么这件事值得看\n- 因为反馈已经高频存在，但整理和改写动作还主要靠人工",
            "## 5. 现在哪些还是猜测\n- 用户痛点到底有多高频\n- 他们愿不愿意换掉现有办法\n- 他们会不会愿意为这件事付出切换成本",
            f"## 6. 这轮最小切口是什么\n- {brief.wedge_hint}",
            "## 7. 接下来最该先验证什么\n- 这个痛点是不是真的高频\n- 现在的凑合方案是不是真的够痛\n- 用户会不会信任自动整理出的需求草稿",
            "",
        ]
    )


def _render_discovery_report(brief: IdeaBrief) -> str:
    project_title = _product_project_title(brief)
    display_title = _product_display_title(brief)
    one_liner = _product_problem_one_liner(brief)
    theme_display = _product_theme_display(brief)
    return "\n".join(
        [
            "# Discovery Report",
            "",
            f"**项目标题：** {project_title}",
            f"**这轮标题：** {display_title}",
            f"**一句话问题定义：** {one_liner}",
            "",
            f"## 一句话判断\n- “{theme_display}”值得先做需求和用户发现，但现在还不适合直接开做。",
            "",
            "## 这轮先要看清什么问题",
            f"- {brief.core_problem}",
            "",
            "## 现在最可能谁最痛",
            f"- 初步判断是 {brief.primary_user_hint}",
            "",
            "## 用户今天怎么凑合",
            f"- {brief.workflow_hint}",
            "",
            "## 下一步先做什么",
            "- 做小样本访谈",
            "- 收集当前凑合方案和真实样本",
            f"- 验证“{brief.wedge_hint}”是不是一个够小、也真的有价值的切口",
            "",
        ]
    )


def _render_market_question(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# Market Question",
            "",
            f"- Core question: 围绕“{brief.theme}”，市场上是否已有成熟替代方案与明显空位？",
            "- Why this market matters: 如果市场已拥挤或用户已满意，产品定义就要收得更窄。",
            "- Decision context: 决定是继续产品定义，还是调整切口。",
            "- Geography: 待确认",
            "- Time window: 最近 12-24 个月",
            "- Audience: 产品与业务决策者",
            "",
        ]
    )


def _render_competitor_scope(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# Competitor Scope",
            "",
            "## 本次算进来的玩家",
            "- Direct: 待补",
            "- Adjacent: 待补",
            "- Status quo / workaround: 待补",
            "",
            "## 本次不算进来的玩家",
            "- Who: 待补",
            "- Why excluded: 与核心问题关系弱或目标用户不重合",
            "",
        ]
    )


def _render_competitor_list_csv() -> str:
    return "\n".join(
        [
            "name,type,target_user,core_promise,price_band,notes",
            "TBD,Direct,TBD,TBD,TBD,TBD",
        ]
    ) + "\n"


def _render_feature_matrix_csv() -> str:
    return "\n".join(
        [
            "competitor,core_feature,differentiator,missing_piece,notes",
            "TBD,TBD,TBD,TBD,TBD",
        ]
    ) + "\n"


def _render_pricing_landscape_csv() -> str:
    return "\n".join(
        [
            "competitor,entry_price,billing_model,seat_or_usage_limit,source,notes",
            "TBD,TBD,TBD,TBD,TBD,TBD",
        ]
    ) + "\n"


def _render_sentiment_summary(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# Sentiment Summary",
            "",
            f"- 针对“{brief.theme}”相关竞品，后续重点收集：用户最常夸什么、最常骂什么、哪些是高频而不是个例。",
            "",
        ]
    )


def _render_gtm_signals(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# GTM Signals",
            "",
            "- 重点看官网定位、价格页、招聘、融资、渠道动作和近期上新。",
            f"- 目的：判断“{brief.theme}”是不是一个已经很挤的位置，还是还有空位。",
            "",
        ]
    )


def _render_competitors_report(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# Competitors Report",
            "",
            f"## 一句话结论\n- 围绕“{brief.theme}”，这轮需要先建立 direct / adjacent / workaround 三层竞争集合。",
            "",
            "## 这次调研在看什么",
            "- 市场是否已有足够成熟方案",
            "- 用户为什么选它们",
            "- 还有没有值得切入的空位",
            "",
        ]
    )


def _render_battle_cards(brief: IdeaBrief) -> str:
    return "\n".join(
        [
            "# Battle Cards",
            "",
            "## 使用说明",
            "- 每个 direct competitor 后续补一张卡",
            "- 记录它卖给谁、主打什么、用户为什么选它、它的强弱项和价格提醒",
            "",
        ]
    )


def _render_product_final_report(mode: str, brief: IdeaBrief) -> str:
    project_title = _product_project_title(brief)
    display_title = _product_display_title(brief)
    one_liner = _product_problem_one_liner(brief)
    theme_display = _product_theme_display(brief)
    mode_summary = {
        "discovery": "先把需求和用户看清楚，再决定要不要进入更细的 PRD。",
        "competitive": "先看竞品格局和市场空位，再决定产品切口。",
        "hybrid": "先把问题和用户收紧，再补竞品格局，最后再定最小切口。",
    }[mode]
    validation_line = "先验证这个用户群是否真的在高频承受这个痛点"
    if brief.primary_user_hint != "待确认":
        validation_line = f"先验证{brief.primary_user_hint}是否真的在高频承受这个痛点"
    return "\n".join(
        [
            "# 产品调研总报告",
            "",
            f"**项目标题：** {project_title}",
            f"**这轮标题：** {display_title}",
            f"**一句话问题定义：** {one_liner}",
            "",
            "## 1. 先说判断",
            f"- 围绕“{theme_display}”，这轮更适合：{mode_summary}",
            "",
            "## 2. 这轮到底想解决什么问题",
            f"- {brief.core_problem}",
            "",
            "## 3. 现在最值得先做什么",
            f"- {validation_line}",
            f"- 补当前凑合方案和真实样本，判断“{brief.wedge_hint}”是否值得先做",
            "- 如需要，再补竞品与市场空位扫描",
            "",
            "## 4. 建议先看哪些文件",
            "- `problem-statement.md`",
            "- `target-user.md`",
            "- `validation-plan.md`",
            "- `product-research-brief.md`",
            "",
        ]
    )


def _render_social_research_scope(mode: str, brief: IdeaBrief) -> str:
    mode_focus = {
        "explainer": "把一个主题给新手讲清楚：为什么存在、核心定义、结构组成、关键步骤和常见误区。",
        "trend": "追踪同一现象在一段时间内怎么变、为什么变、哪些信号互相矛盾。",
        "population": "比较不同人群对同一现象的感受、行为和约束差异。",
        "case": "从一组可比样本里看共性、反例和边界条件。",
    }[mode]
    return "\n".join(
        [
            "# Research Scope",
            "",
            f"- 研究主题: {brief.theme}",
            f"- 本轮重点: {mode_focus}",
            "- 时间范围: 待确认",
            "- 地区边界: 待确认",
            "- 研究对象: 待确认",
            "- 明确不看什么: 先不把个别情绪表达直接放大成整体结论。",
            "",
        ]
    )


def _render_population_or_case_definition(mode: str, brief: IdeaBrief) -> str:
    if mode == "explainer":
        lines = [
            "# Explanation Structure",
            "",
            "- 核心概念: 待确认",
            "- 先讲什么: 为什么会有这个设定 / 这个主题解决什么问题",
            "- 再讲什么: 它到底是什么、包含哪些文件或组成部分",
            "- 后讲什么: 具体怎么做、每一部分分别怎么写",
            f"- 主题关联: 围绕“{brief.theme}”只保留能帮助新手建立正确心智模型的内容",
            "- 不纳入的内容: 只讲功利场景、不讲定义和边界；或把多个文件要求混成一团",
            "",
        ]
    elif mode == "population":
        lines = [
            "# Population Definition",
            "",
            "- 主比较人群: 待确认",
            "- 对照人群: 待确认",
            "- 比较维度: 年龄 / 职业阶段 / 地区 / 收入 / 教育背景 等待补齐",
            f"- 主题关联: 围绕“{brief.theme}”只比较与问题直接相关的人群差异",
            "- 不做的比较: 不把无法对齐口径的样本硬放在一起比",
            "",
        ]
    elif mode == "case":
        lines = [
            "# Case Definition",
            "",
            "- 样本类型: 待确认",
            "- 选样标准: 至少满足与主题直接相关、可复查、有基本背景信息",
            "- 反例标准: 需要主动保留和主叙事相反的样本",
            f"- 主题关联: 所有样本都必须能直接支持“{brief.theme}”这个问题",
            "- 不纳入的样本: 纯情绪宣泄、上下文残缺、无法验证出处的个例",
            "",
        ]
    else:
        lines = [
            "# Population Or Case Definition",
            "",
            "- 核心观察对象: 待确认",
            "- 需要分开的子人群: 待确认",
            "- 需要重点跟踪的事件或样本: 待确认",
            f"- 主题关联: 围绕“{brief.theme}”优先保留能体现时间变化的代表性样本",
            "- 不纳入的内容: 只提供情绪、不提供现象背景的零碎表达",
            "",
        ]
    return "\n".join(lines)


def _render_social_evidence_log(mode: str, brief: IdeaBrief) -> str:
    rows = [
        "| Evidence | Type | What it supports | Risk | Next step |",
        "|---|---|---|---|---|",
        f"| 围绕“{brief.theme}”的首批公开样本 | 待补 | 先验证现象是否真的存在 | 可能只反映高声量少数人 | 继续补时间、地区、人群分布 |",
        "| 行业报告 / 官方数据 / 平台公开统计 | 待补 | 验证规模、变化速度和长期趋势 | 指标口径可能不一致 | 统一定义后再比较 |",
        "| 访谈 / 案例 / 评论区叙事 | 待补 | 补行为动机和主观解释 | 容易被情绪和样本偏差带偏 | 与更硬证据交叉验证 |",
    ]
    if mode == "explainer":
        rows = [
            "| Evidence | Type | What it supports | Risk | Next step |",
            "|---|---|---|---|---|",
            f"| 围绕“{brief.theme}”的权威定义或官方说明 | 待补 | 说明这个概念到底是什么 | 二手转述容易改写走样 | 优先补一手定义来源 |",
            "| 规范文件 / 模板 / 示例材料 | 待补 | 说明它包含什么、每部分怎么写 | 样例可能只代表某一口径 | 对照适用边界和版本 |",
            "| 常见误区 / 问答 / 教学材料 | 待补 | 说明新手最容易混淆什么 | 经验贴可能夹带个人偏好 | 与正式要求交叉验证 |",
        ]
    header = {
        "explainer": "# Evidence Log",
        "trend": "# Evidence Log",
        "population": "# Evidence Log",
        "case": "# Evidence Log",
    }[mode]
    return header + "\n\n" + "\n".join(rows) + "\n"


def _render_uncertainty_and_bias(mode: str, brief: IdeaBrief) -> str:
    mode_risk = {
        "explainer": "- 讲解时最容易把定义、作用、文件要求和写作技巧混成一团。",
        "trend": "- 看到阶段性波动时，不能直接当长期趋势。",
        "population": "- 看到群体差异时，不能跳过样本量和口径差异直接下结论。",
        "case": "- 看到几个强案例时，不能默认它们代表整体。",
    }[mode]
    return "\n".join(
        [
            "# Uncertainty And Bias",
            "",
            "## 当前最大不确定性",
            "- 研究对象、时间范围和地区边界都还没完全锁定。",
            "- 现有公开表达可能更偏高情绪、高声量样本。",
            "",
            "## 本轮最容易犯的错",
            mode_risk,
            "- 把平台舆论、媒体叙事和真实行为变化混为一谈。",
            "- 先有观点，再回头挑证据支持它。",
            "",
            "## 保守处理原则",
            "- 先分清事实、解释和猜测。",
            "- 每个结论尽量都保留反例和替代解释。",
            "- 结论只说到证据能撑住的地方。",
            "",
        ]
    )


def _render_social_reader_brief(mode: str, brief: IdeaBrief) -> str:
    angle = {
        "explainer": "先把为什么会有这个设定、它到底是什么、包含什么、以及具体怎么做讲清楚。",
        "trend": "这个现象到底是在变大、变小，还是只是最近更容易被看到。",
        "population": "同一个现象，是不是其实只集中在少数人群，而不是普遍共识。",
        "case": "这些高讨论度案例，到底是普遍规律，还是几个容易被转发的特殊样本。",
    }[mode]
    next_steps = ["- 时间边界", "- 对象定义", "- 更硬的证据来源"]
    if mode == "explainer":
        next_steps = ["- 一手定义来源", "- 关键文件或结构示例", "- 常见混淆点和正确区分方式"]
    return "\n".join(
        [
            "# 这份社会调研在讲什么",
            "",
            f"## 1. 这次在研究什么\n- {brief.theme}",
            f"## 2. 这轮最想看清什么\n- {angle}",
            "## 3. 现在已经知道什么\n- 路线和研究重点已明确，但硬证据还待补",
            "## 4. 现在还不能下什么结论\n- 还不能把少量样本直接放大成总体判断",
            "## 5. 下一步最该补什么",
            *next_steps,
            "",
        ]
    )


def _render_social_final_report(mode: str, brief: IdeaBrief) -> str:
    mode_summary = {
        "explainer": "先把定义、作用、结构和写法步骤讲清楚，再补常见误区与判断标准。",
        "trend": "先做趋势拆解，再决定要不要进一步做分群或案例深挖。",
        "population": "先把关键人群差异拆开，再判断哪些差异是真差异、哪些只是样本错觉。",
        "case": "先用一组可复查案例看共性和反例，再决定能不能上升到更大结论。",
    }[mode]
    return "\n".join(
        [
            "# 社会调研总报告",
            "",
            "## 1. 先说结论",
            f"- 围绕“{brief.theme}”，当前建议路线是：{mode_summary}",
            "",
            "## 2. 这次到底在看什么",
            f"- {brief.theme}",
            "",
            "## 3. 当前最值得做的下一步",
            "- 锁定研究对象、时间范围和地区边界",
            "- 补一批更硬的证据来源和反例",
            "- 再决定是否继续扩大结论范围",
            "",
            "## 4. 先看哪些文件",
            "- `research-scope.md`",
            "- `population-or-case-definition.md`",
            "- `evidence-log.md`",
            "- `uncertainty-and-bias.md`",
            "- `social-research-brief.md`",
            "",
        ]
    )
