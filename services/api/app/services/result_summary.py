from __future__ import annotations

from io import BytesIO
import re
from textwrap import dedent

from fastapi import HTTPException, status

from app.domain.schemas import (
    ArtifactBundle,
    GeneratedDocument,
    KnowledgeSource,
    Project,
    ProjectState,
    ResultSummaryAction,
    ResultSummaryReference,
    ResultSummaryResponse,
    ResultSummarySection,
)
from app.settings import Settings


STAGE_LABELS = {
    "literature_review": "文献梳理",
    "gap_analysis": "缺口判断",
    "proposal": "方案成形",
    "meeting_notes": "纪要沉淀",
}


def _stage_label(stage: str) -> str:
    return STAGE_LABELS.get(stage, stage)


def _first_sentence(text: str | None, fallback: str) -> str:
    if not text:
        return fallback
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return fallback
    for sep in ["。", ".", ";", "；"]:
        if sep in cleaned:
            candidate = cleaned.split(sep)[0].strip()
            if candidate:
                return candidate
    return cleaned[:140]


def _pick_intro(project: Project, state: ProjectState, artifacts: ArtifactBundle) -> str:
    if state.research_focus and state.why_now:
        return f"{state.research_focus}。当前值得推进的原因是：{state.why_now}"
    if artifacts.plan_cards:
        plan = artifacts.plan_cards[0]
        return f"当前推荐围绕“{plan.research_question}”展开，并优先把它收成一版可验证的研究方案。"
    if artifacts.gap_cards:
        gap = artifacts.gap_cards[0]
        return f"当前最值得优先关注的缺口是“{gap.title}”，因为它直接关系到：{gap.why_it_matters}"
    return project.summary or f"这个项目当前处于{_stage_label(project.stage)}阶段，适合先建立领域地图和基础认知。"


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^\w\u4e00-\u9fff]+", text.lower()) if token]


def _score_source_relevance(source: KnowledgeSource, project: Project, state: ProjectState) -> float:
    source_text = " ".join(
        [
            source.title,
            source.abstract or "",
            source.citation or "",
            source.venue or "",
            source.doi or "",
        ]
    ).lower()
    query_terms = _tokenize(" ".join([project.title, state.research_focus or "", *state.search_queries]))
    if not query_terms:
        return 0.0
    score = 0.0
    for token in query_terms:
        if token in source_text:
            score += 1.0
    title_lower = source.title.lower()
    if "oled" in title_lower:
        score += 6.0
    if "machine learning" in title_lower or "ml" in title_lower:
        score += 2.0
    if source.source_type == "pdf_upload":
        score += 1.5
    return score


def _build_recommended_reading(
    project: Project,
    state: ProjectState,
    knowledge_sources: list[KnowledgeSource],
    artifacts: ArtifactBundle,
) -> list[ResultSummaryReference]:
    reading: list[ResultSummaryReference] = []
    keyed_results = {card.title: card.key_result for card in artifacts.literature_cards}
    ranked_sources = [
        (
            source,
            _score_source_relevance(source, project, state),
        )
        for source in knowledge_sources
    ]
    ranked_sources.sort(key=lambda item: (item[1], item[0].updated_at.timestamp()), reverse=True)
    top_score = ranked_sources[0][1] if ranked_sources else 0.0
    threshold = max(2.5, top_score * 0.45) if top_score > 0 else 0.0

    for source, score in ranked_sources:
        if reading and score < threshold:
            continue
        reason = keyed_results.get(source.title) or _first_sentence(
            source.abstract,
            "推荐作为入门阅读，用来先建立领域背景和术语地图。",
        )
        reading.append(
            ResultSummaryReference(
                title=source.title,
                reason=reason,
                citation=source.citation,
                doi=source.doi,
                url=source.url,
                source_type=source.source_type,
            )
        )
        if len(reading) >= 5:
            break

    if not reading:
        fallback_sources = sorted(knowledge_sources, key=lambda source: source.updated_at.timestamp(), reverse=True)
        for source in fallback_sources[:3]:
            reading.append(
                ResultSummaryReference(
                    title=source.title,
                    reason=_first_sentence(
                        source.abstract,
                        "当前缺少更贴题的来源，先用这篇建立基础背景，再继续补充证据。",
                    ),
                    citation=source.citation,
                    doi=source.doi,
                    url=source.url,
                    source_type=source.source_type,
                )
            )
    return reading


def _build_sections(
    project: Project,
    state: ProjectState,
    artifacts: ArtifactBundle,
    knowledge_sources: list[KnowledgeSource],
) -> list[ResultSummarySection]:
    literature_points = [
        f"{card.title}：{card.research_question}；当前结论是 {card.key_result}"
        for card in artifacts.literature_cards[:3]
    ] or ["当前还缺少足够的文献卡，建议先补充 PDF 或继续执行文献助理。"]
    gap_points = [
        f"{card.title}：重要性 {card.importance_score}/10，可行性 {card.feasibility_score}/10。{card.why_it_matters}"
        for card in artifacts.gap_cards[:3]
    ] or ["当前还没有明确缺口，建议继续围绕已有知识源补证据。"]

    if artifacts.plan_cards:
        plan = artifacts.plan_cards[0]
        entry_content = dedent(
            f"""
            当前最推荐的切入点是：{plan.research_question}
            建议先把研究边界收在：{plan.boundary}
            数据优先来自：{plan.data_source}
            验证方式优先采用：{plan.validation}
            """
        ).strip()
        entry_bullets = [
            f"方法路线：{'、'.join(plan.methods) if plan.methods else '待补充'}",
            f"评价指标：{'、'.join(plan.metrics) if plan.metrics else '待补充'}",
        ]
    elif artifacts.gap_cards:
        gap = artifacts.gap_cards[0]
        entry_content = f"当前更适合先从“{gap.title}”切入，因为它直接影响后续能否形成可执行方案。"
        entry_bullets = [gap.why_it_matters]
    else:
        entry_content = "当前还不适合直接确定切入点，先补足文献和证据会更稳。"
        entry_bullets = ["建议先执行文献助理并上传最关键的 3 到 5 篇 PDF。"]

    if artifacts.meeting_notes:
        meeting = artifacts.meeting_notes[0]
        next_bullets = [*meeting.todos[:4]]
        if meeting.next_step:
            next_bullets.append(f"本轮系统建议的下一步：{meeting.next_step}")
    else:
        next_bullets = state.key_questions[:4] or ["先明确 1 个最想回答的问题，再继续追问。"]

    evidence_bullets = []
    if knowledge_sources:
        evidence_bullets.append(f"当前项目知识库中已有 {len(knowledge_sources)} 条来源，可直接点开原始链接。")
    else:
        evidence_bullets.append("当前项目知识库仍为空，结论可信度会受影响。")
    if any(item.source_type == "pdf_upload" for item in knowledge_sources):
        evidence_bullets.append("项目里已经有用户上传的 PDF，适合继续补正文证据。")
    else:
        evidence_bullets.append("目前主要还是外部候选来源，建议补充用户上传 PDF 来强化证据层。")

    return [
        ResultSummarySection(
            title="这个方向现在在做什么",
            content=state.research_focus or project.title,
            bullets=literature_points,
        ),
        ResultSummarySection(
            title="当前最值得优先关注的问题",
            content="这部分不是泛泛而谈，而是当前系统基于已有证据收出来的优先缺口。",
            bullets=gap_points,
        ),
        ResultSummarySection(
            title="最推荐的切入点",
            content=entry_content,
            bullets=entry_bullets,
        ),
        ResultSummarySection(
            title="下一步怎么推进",
            content="这部分是给科研新人直接执行的行动清单。",
            bullets=next_bullets,
        ),
        ResultSummarySection(
            title="当前证据与边界",
            content="所有结论都应该回到知识源和成果卡去理解；如果证据不足，就继续补资料，而不是强行下结论。",
            bullets=evidence_bullets,
        ),
    ]


def _build_next_actions(
    state: ProjectState,
    artifacts: ArtifactBundle,
    knowledge_sources: list[KnowledgeSource],
) -> list[ResultSummaryAction]:
    actions: list[ResultSummaryAction] = []
    if not knowledge_sources:
        actions.append(
            ResultSummaryAction(
                title="补齐第一批资料",
                description="先上传 3 到 5 篇最关键的 PDF，或者继续让文献助理扩充知识源。",
            )
        )
    if not artifacts.literature_cards:
        actions.append(
            ResultSummaryAction(
                title="先建立领域地图",
                description="优先让系统生成文献卡，确保你知道这个方向目前做到哪一步。",
            )
        )
    if artifacts.gap_cards:
        actions.append(
            ResultSummaryAction(
                title="围绕优先缺口继续追问",
                description=f"建议针对“{artifacts.gap_cards[0].title}”继续追问，收紧研究边界。",
            )
        )
    if state.next_step:
        actions.append(
            ResultSummaryAction(
                title="执行当前下一步",
                description=state.next_step,
            )
        )
    return actions[:4]


def build_result_summary(
    settings: Settings,
    *,
    project: Project,
    state: ProjectState,
    artifacts: ArtifactBundle,
    knowledge_sources: list[KnowledgeSource],
    generated_documents: list[GeneratedDocument],
) -> ResultSummaryResponse:
    reading = _build_recommended_reading(project, state, knowledge_sources, artifacts)
    sections = _build_sections(project, state, artifacts, knowledge_sources)
    next_actions = _build_next_actions(state, artifacts, knowledge_sources)
    knowledge_highlights = reading[:3]
    latest_follow_up = next(
        (item for item in generated_documents if item.doc_type == "follow_up"),
        None,
    )

    intro = _pick_intro(project, state, artifacts)
    if latest_follow_up:
        intro = f"{intro}\n\n最近一轮继续追问已经完成，结果已被纳入当前项目档案，可继续沿这条主线推进。"

    pdf_url = f"{settings.guideclaw_api_base_url.rstrip('/')}/projects/{project.id}/result-summary.pdf"

    return ResultSummaryResponse(
        project_id=project.id,
        project_title=project.title,
        stage_label=_stage_label(project.stage),
        intro=intro,
        sections=sections,
        recommended_reading=reading,
        next_actions=next_actions,
        knowledge_highlights=knowledge_highlights,
        pdf_url=pdf_url,
    )


def build_result_summary_markdown(summary: ResultSummaryResponse) -> str:
    section_blocks = []
    for section in summary.sections:
        bullets = "\n".join([f"- {item}" for item in section.bullets]) or "- 暂无补充。"
        section_blocks.append(
            dedent(
                f"""
                ## {section.title}

                {section.content}

                {bullets}
                """
            ).strip()
        )

    reading_blocks = "\n".join(
        [
            dedent(
                f"""
                - **{item.title}**
                  - 为什么先看：{item.reason}
                  - 引用：{item.citation or '暂无引用串'}
                  - DOI：{item.doi or '暂无 DOI'}
                  - 链接：{item.url or '暂无外部链接'}
                """
            ).strip()
            for item in summary.recommended_reading
        ]
    ) or "- 当前还没有优先阅读列表。"

    action_blocks = "\n".join(
        [f"- **{item.title}**：{item.description}" for item in summary.next_actions]
    ) or "- 当前还没有下一步行动建议。"

    return "\n\n".join(
        [
            f"# {summary.project_title} - 结果汇总",
            f"- 当前阶段：{summary.stage_label}",
            f"- 生成时间：{summary.generated_at.astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}",
            "",
            "## 一句话概览",
            summary.intro,
            "",
            *section_blocks,
            "",
            "## 优先阅读",
            reading_blocks,
            "",
            "## 下一步行动",
            action_blocks,
            "",
            f"## PDF 版本\n- {summary.pdf_url}",
        ]
    ).strip()


def build_result_summary_pdf(summary: ResultSummaryResponse) -> bytes:
    try:
        from reportlab.lib.colors import HexColor
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"PDF generation dependency missing: {exc}",
        ) from exc

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "GuideTitle",
        parent=styles["Title"],
        fontName="STSong-Light",
        fontSize=22,
        leading=28,
        textColor=HexColor("#0f172a"),
        alignment=TA_LEFT,
    )
    h2_style = ParagraphStyle(
        "GuideH2",
        parent=styles["Heading2"],
        fontName="STSong-Light",
        fontSize=15,
        leading=20,
        textColor=HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "GuideBody",
        parent=styles["BodyText"],
        fontName="STSong-Light",
        fontSize=10.5,
        leading=17,
        textColor=HexColor("#1e293b"),
    )
    subtle_style = ParagraphStyle(
        "GuideSubtle",
        parent=body_style,
        textColor=HexColor("#475569"),
        fontSize=9.5,
        leading=15,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"{summary.project_title} - 结果汇总",
    )

    story = [
        Paragraph("引路虾结果汇总", title_style),
        Spacer(1, 6),
        Paragraph(summary.project_title, h2_style),
        Paragraph(f"当前阶段：{summary.stage_label}", subtle_style),
        Spacer(1, 8),
        Paragraph(summary.intro.replace("\n", "<br/>"), body_style),
        Spacer(1, 10),
    ]

    for section in summary.sections:
        story.append(Paragraph(section.title, h2_style))
        story.append(Paragraph(section.content.replace("\n", "<br/>"), body_style))
        for bullet in section.bullets:
            story.append(Paragraph(f"• {bullet}", body_style))
        story.append(Spacer(1, 8))

    if summary.recommended_reading:
        story.append(Paragraph("优先阅读", h2_style))
        for item in summary.recommended_reading:
            story.append(Paragraph(f"• {item.title}", body_style))
            story.append(Paragraph(item.reason, subtle_style))
            if item.url:
                story.append(Paragraph(f"<link href='{item.url}' color='blue'>{item.url}</link>", subtle_style))
        story.append(Spacer(1, 8))

    if summary.next_actions:
        story.append(Paragraph("接下来建议你立刻做的事", h2_style))
        data = [["动作", "说明"]]
        for item in summary.next_actions:
            data.append([item.title, item.description])
        table = Table(data, colWidths=[42 * mm, 120 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("LEADING", (0, 0), (-1, -1), 13),
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e2f4f1")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#0f172a")),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return buffer.getvalue()
