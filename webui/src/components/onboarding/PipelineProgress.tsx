import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  Circle,
  FileSearch,
  GitBranch,
  Loader2,
  ScanSearch,
  TestTube2,
} from "lucide-react";

export type PipelineStep = "input" | "structure" | "architecture" | "issues" | "generate";
export type StepStatus = "pending" | "running" | "done";

interface StepDef {
  key: PipelineStep;
  label: string;
  icon: typeof FileSearch;
}

const STEPS: StepDef[] = [
  { key: "input", label: "Input", icon: ScanSearch },
  { key: "structure", label: "Structure Scan", icon: FileSearch },
  { key: "architecture", label: "Architecture", icon: GitBranch },
  { key: "issues", label: "Tests & Issues", icon: TestTube2 },
  { key: "generate", label: "Generate Docs", icon: CheckCircle2 },
];

interface Props {
  current: PipelineStep | null;
  completed: Set<PipelineStep>;
  className?: string;
}

export function PipelineProgress({ current, completed, className }: Props) {
  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      {STEPS.map((step, i) => {
        const isRunning = current === step.key;
        const isDone = completed.has(step.key);
        const isPending = !isRunning && !isDone;

        return (
          <div key={step.key} className="flex items-center gap-1.5">
            {i > 0 && (
              <span
                className={cn(
                  "h-px w-4 rounded",
                  isDone ? "bg-teal-400" : "bg-border",
                )}
              />
            )}
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                isRunning &&
                  "border-teal-400/50 bg-teal-500/10 text-teal-600 dark:text-teal-400",
                isDone &&
                  "border-teal-300 bg-teal-50 text-teal-700 dark:border-teal-700 dark:bg-teal-950 dark:text-teal-300",
                isPending && "border-dashed border-border text-muted-foreground",
              )}
            >
              {isRunning ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : isDone ? (
                <CheckCircle2 className="h-3 w-3" />
              ) : (
                <Circle className="h-3 w-3" />
              )}
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
