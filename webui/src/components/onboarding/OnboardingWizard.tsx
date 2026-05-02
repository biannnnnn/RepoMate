import { useState } from "react";
import { ArrowRight, FolderGit2, Github, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface OnboardingWizardProps {
  onStart: (repoInput: string) => void;
  loading: boolean;
}

const EXAMPLES = [
  { label: "本地项目", icon: FolderGit2, value: "/path/to/your/project" },
  { label: "GitHub 仓库", icon: Github, value: "github.com/owner/repo" },
];

export function OnboardingWizard({ onStart, loading }: OnboardingWizardProps) {
  const [repoInput, setRepoInput] = useState("");

  const isValid = repoInput.trim().length > 0;

  const handleSubmit = () => {
    if (!isValid || loading) return;
    onStart(repoInput.trim());
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
      <div className="flex w-full max-w-2xl flex-col items-center gap-8 animate-in fade-in-0 slide-in-from-bottom-4 duration-500">
        {/* Hero */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-700 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-300">
            <Sparkles className="h-3 w-3" />
            AI 驱动的代码库入职分析
          </div>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Repo<span className="text-teal-500">Mate</span>
          </h1>
          <p className="max-w-md text-sm text-muted-foreground">
            输入本地项目路径或 GitHub 仓库地址，RepoMate
            将自动扫描代码结构、分析架构、定位测试缺口，并生成专属入职文档。
          </p>
        </div>

        {/* Input */}
        <div className="flex w-full max-w-md gap-2">
          <div className="relative flex-1">
            <Input
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit();
              }}
              placeholder="github.com/owner/repo  或  /path/to/project"
              disabled={loading}
              className="h-10 pr-8 text-sm"
              autoFocus
            />
          </div>
          <Button
            onClick={handleSubmit}
            disabled={!isValid || loading}
            className="h-10 gap-1.5 bg-teal-600 hover:bg-teal-700 text-white dark:bg-teal-500 dark:hover:bg-teal-600"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            开始分析
          </Button>
        </div>

        {/* Quick examples */}
        <div className="flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs text-muted-foreground">快速填入：</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              onClick={() => {
                setRepoInput(ex.value);
                const input = document.querySelector("input") as HTMLInputElement;
                if (input) {
                  input.focus();
                  input.select();
                }
              }}
              disabled={loading}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs",
                "text-muted-foreground hover:border-teal-300 hover:text-teal-700",
                "dark:hover:border-teal-700 dark:hover:text-teal-300",
                "transition-colors",
              )}
            >
              <ex.icon className="h-3 w-3" />
              {ex.label}
            </button>
          ))}
        </div>

        {/* Feature cards */}
        <div className="grid w-full max-w-lg grid-cols-3 gap-3">
          {[
            { icon: "🔍", title: "结构扫描", desc: "带注释的目录树" },
            { icon: "🏗", title: "架构分析", desc: "依赖图 + 设计模式" },
            { icon: "🧪", title: "测试与问题", desc: "覆盖率缺口 + 热点" },
            { icon: "📝", title: "入职计划", desc: "逐日学习路线" },
            { icon: "📄", title: "架构文档", desc: "含 file:line 引用" },
            { icon: "🐛", title: "新手任务", desc: "Good First Issue 列表" },
          ].map((f) => (
            <div
              key={f.title}
              className="flex flex-col gap-1 rounded-lg border bg-card/50 p-3 text-center"
            >
              <span className="text-lg">{f.icon}</span>
              <span className="text-xs font-medium">{f.title}</span>
              <span className="text-[10px] text-muted-foreground">{f.desc}</span>
            </div>
          ))}
        </div>

        <p className="text-[11px] text-muted-foreground">
          全程本地运行，RepoMate MCP 工具为只读模式——代码不会离开你的设备。
        </p>
      </div>
    </div>
  );
}
