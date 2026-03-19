"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Bot, FolderKanban, LoaderCircle, Plus, X } from "lucide-react";
import type { FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { formatDuration, markdownComponents } from "./content";
import type { RoleCard, StreamMeta } from "./types";

type CreateProjectDialogProps = {
  open: boolean;
  titleInput: string;
  summaryInput: string;
  loading: boolean;
  error: string | null;
  onOpenChange: (open: boolean) => void;
  onTitleChange: (value: string) => void;
  onSummaryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function CreateProjectDialog({
  open,
  titleInput,
  summaryInput,
  loading,
  error,
  onOpenChange,
  onTitleChange,
  onSummaryChange,
  onSubmit,
}: CreateProjectDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-backdrop" />
        <Dialog.Content className="modal-panel modal-panel-compact">
          <div className="modal-head">
            <div>
              <span className="mini-label">
                <FolderKanban size={14} />
                新建研究项目
              </span>
              <Dialog.Title asChild>
                <h2>给新的课题留一个独立入口</h2>
              </Dialog.Title>
              <Dialog.Description className="visually-hidden">
                输入研究题目和说明，系统会为这个议题创建独立的项目空间与首轮调查入口。
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button className="icon-button" type="button">
                <X size={16} />
                关闭
              </button>
            </Dialog.Close>
          </div>

          <form className="project-form" onSubmit={onSubmit}>
            <label className="project-field">
              <span>课题标题</span>
              <input
                placeholder="例如：多模态大模型辅助药物靶点发现"
                value={titleInput}
                onChange={(event) => onTitleChange(event.target.value)}
              />
            </label>

            <label className="project-field">
              <span>相关说明</span>
              <textarea
                placeholder="写下研究背景、你已知的方向、想优先了解的问题，后续就能围绕这个说明建立文献与方案上下文。"
                rows={6}
                value={summaryInput}
                onChange={(event) => onSummaryChange(event.target.value)}
              />
            </label>

            {error ? <div className="error-box">{error}</div> : null}

            <div className="project-form-actions">
              <button className="secondary-button" onClick={() => onOpenChange(false)} type="button">
                取消
              </button>
              <button className="primary-button" disabled={loading} type="submit">
                {loading ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}
                {loading ? "创建并调查中..." : "创建并启动首轮调查"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

type RoleRunDialogProps = {
  open: boolean;
  activeRole: RoleCard | null;
  loading: boolean;
  status: string;
  error: string | null;
  content: string;
  meta: StreamMeta | null;
  onOpenChange: (open: boolean) => void;
};

export function RoleRunDialog({
  open,
  activeRole,
  loading,
  status,
  error,
  content,
  meta,
  onOpenChange,
}: RoleRunDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-backdrop" />
        <Dialog.Content className="modal-panel">
          <div className="modal-head">
            <div>
              <span className="mini-label">
                <Bot size={14} />
                OpenClaw 执行面板
              </span>
              <Dialog.Title asChild>
                <h2>{activeRole?.name ?? "角色执行"}</h2>
              </Dialog.Title>
              <Dialog.Description className="visually-hidden">
                展示当前角色调用 OpenClaw 后的状态、会话信息与流式 Markdown 输出。
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button className="icon-button" type="button">
                <X size={16} />
                关闭
              </button>
            </Dialog.Close>
          </div>

          <div className="result-meta-grid">
            <div>
              <span>状态</span>
              <strong>{status}</strong>
            </div>
            <div>
              <span>Skill</span>
              <strong>{meta?.skill ?? activeRole?.skill ?? "等待返回"}</strong>
            </div>
            <div>
              <span>内部推理层</span>
              <strong>{meta?.model ? "已启用" : "等待连接"}</strong>
            </div>
            <div>
              <span>耗时</span>
              <strong>{formatDuration(meta?.duration_ms)}</strong>
            </div>
            <div>
              <span>执行会话</span>
              <strong>{meta?.session_id ?? "等待建立"}</strong>
            </div>
          </div>

          {loading ? (
            <div className="modal-loading">
              <LoaderCircle className="spin" size={18} />
              <div>
                <strong>正在流式接收输出</strong>
                <p>这条结果来自 OpenClaw 调用 workspace skill 后的真实执行链路。</p>
              </div>
            </div>
          ) : null}

          {error ? <div className="error-box">{error}</div> : null}

          <div className="markdown-box">
            {content ? (
              <ReactMarkdown components={markdownComponents()} remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            ) : (
              <div className="empty-state">执行结果会在这里以 Markdown 形式流式出现。</div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
