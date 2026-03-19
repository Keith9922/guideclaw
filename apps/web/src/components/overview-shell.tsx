"use client";

import Link from "next/link";
import { ArrowRight, Bot, FileText, FolderKanban, LibraryBig, Plus, Sparkles } from "lucide-react";
import type { ApiProject } from "@/lib/api";

type OverviewShellProps = {
  projects: ApiProject[];
  pageErrors?: string[];
};

const overviewSections = [
  {
    href: "/projects",
    title: "项目管理",
    description: "创建新课题、切换当前研究项目、维护每个议题的独立空间。",
    icon: FolderKanban,
  },
  {
    href: "/workspace",
    title: "工作区",
    description: "只保留当前课题最关键的研究推进信息和下一步动作。",
    icon: Sparkles,
  },
  {
    href: "/artifacts",
    title: "成果页",
    description: "把文献卡、缺口卡、方案卡、纪要卡拆出来单独查看。",
    icon: FileText,
  },
  {
    href: "/results",
    title: "结果汇总",
    description: "把当前课题最有价值的结果收成一页，适合直接给科研新人阅读或导出 PDF。",
    icon: Sparkles,
  },
  {
    href: "/knowledge",
    title: "知识库",
    description: "查看候选论文、原始链接与项目级知识检索结果。",
    icon: LibraryBig,
  },
  {
    href: "/roles",
    title: "角色页",
    description: "单独触发 OpenClaw 角色执行，避免把操作入口塞满首页。",
    icon: Bot,
  },
];

export function OverviewShell({ projects, pageErrors = [] }: OverviewShellProps) {
  return (
    <main className="page-shell">
      <div className="page-bg-orb orb-one" />
      <div className="page-bg-orb orb-two" />

      <header className="topbar">
        <div className="topbar-copy">
          <div className="brand-lockup">
            <div className="brand-logo-frame">
              <img className="brand-logo" src="/guideclaw-logo.png" alt="引路虾 Logo" />
            </div>
            <div className="brand-copy">
              <div className="topbar-kicker">GuideClaw · 学术龙虾平台</div>
              <h1>引路虾总览</h1>
              <p>首页只保留总览和入口，不展示占位成果。真实研究数据从项目管理页开始建立。</p>
            </div>
          </div>
        </div>
        <div className="topbar-badges">
          <span className="badge ghost">{projects.length} 个真实课题</span>
          <span className="badge ghost">首页总览</span>
        </div>
      </header>

      <section className="hero hero-embedded home-hero">
        <div className="hero-copy">
          {pageErrors.length ? (
            <div className="page-banner-stack">
              {pageErrors.map((item) => (
                <div className="error-box page-error-box" key={item}>
                  {item}
                </div>
              ))}
            </div>
          ) : null}
          <span className="mini-label">
            <Sparkles size={14} />
            首页说明
          </span>
          <p className="hero-summary">
            这不是工作台，也不是成果页。它只是一个干净的总入口，用来选择你接下来要进入哪一类页面。
          </p>
          <div className="hero-actions">
            <Link className="primary-button" href="/projects">
              <Plus size={16} />
              创建第一个研究项目
            </Link>
            <Link className="secondary-button" href="/workspace">
              <ArrowRight size={16} />
              进入工作区
            </Link>
          </div>
        </div>

        <div className="metric-grid">
          <article className="metric-card">
            <span>项目总数</span>
            <strong>{projects.length}</strong>
            <p>这里只统计真实项目，不再预置任何示例课题。</p>
          </article>
          <article className="metric-card">
            <span>首页原则</span>
            <strong>保持干净</strong>
            <p>首页不承载复杂操作，复杂内容全部拆到其他页面。</p>
          </article>
        </div>
      </section>

      <section className="section-panel home-grid-panel">
        <div className="section-head">
          <div>
            <span className="mini-label">
              <FolderKanban size={14} />
              页面入口
            </span>
            <h2>进入不同功能页面</h2>
          </div>
          <p>差别大的内容全部拆页，不再在首页堆叠。</p>
        </div>

        <div className="home-grid">
          {overviewSections.map((section) => {
            const Icon = section.icon;
            return (
              <Link key={section.href} className="home-link-card" href={section.href}>
                <div className="home-link-head">
                  <span className="mini-label">
                    <Icon size={14} />
                    {section.title}
                  </span>
                  <ArrowRight size={18} />
                </div>
                <h3>{section.title}</h3>
                <p>{section.description}</p>
              </Link>
            );
          })}
        </div>

        <div className="home-empty">
          {projects.length ? (
            <>
              <strong>最近已有项目</strong>
              <p>你可以直接进入项目管理页继续补充真实研究数据。</p>
            </>
          ) : pageErrors.length ? (
            <>
              <strong>当前项目列表暂时不可用</strong>
              <p>这不是“没有项目”的正常空态。请先检查本地 API、OpenClaw 和数据库运行状态。</p>
            </>
          ) : (
            <>
              <strong>当前还没有任何项目</strong>
              <p>这是预期行为。首页保持空白，等你自己输入真实课题后再进入工作区。</p>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
