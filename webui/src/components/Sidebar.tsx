import { Moon, PanelLeftClose, PanelLeftOpen, RefreshCcw, Rocket, Settings, SquarePen, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ChatList } from "@/components/ChatList";
import { ConnectionBadge } from "@/components/ConnectionBadge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { ChatSummary } from "@/lib/types";

interface SidebarProps {
  sessions: ChatSummary[];
  activeKey: string | null;
  loading: boolean;
  theme: "light" | "dark";
  collapsed?: boolean;
  onToggleTheme: () => void;
  onToggleCollapse?: () => void;
  onNewChat: () => void;
  onSelect: (key: string) => void;
  onRefresh: () => void;
  onRequestDelete: (key: string, label: string) => void;
  activeView?: "chat" | "settings" | "onboarding";
  onOpenSettings: () => void;
  onOpenOnboarding: () => void;
}

import { cn } from "@/lib/utils";

function IconButton({ label, icon, onClick, active }: { label: string; icon: React.ReactNode; onClick: () => void; active?: boolean }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={label}
          onClick={onClick}
          className={cn(
            "h-8 w-8 rounded-lg text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground",
            active && "bg-teal-500/10 text-teal-600 dark:bg-teal-500/15 dark:text-teal-300",
          )}
        >
          {icon}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="right" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  );
}

export function Sidebar(props: SidebarProps) {
  const { t } = useTranslation();

  // Collapsed: thin icon rail
  if (props.collapsed) {
    return (
      <aside className="flex h-full w-full flex-col items-center gap-1 border-r border-sidebar-border/70 bg-sidebar py-3">
        <IconButton label={t("sidebar.collapse")} icon={<PanelLeftOpen className="h-4 w-4" />} onClick={props.onToggleCollapse ?? (() => {})} />
        <Separator className="my-1 w-8 bg-sidebar-border/50" />
        <IconButton label={t("sidebar.onboarding")} icon={<Rocket className="h-4 w-4" />} onClick={props.onOpenOnboarding} active={props.activeView === "onboarding"} />
        <IconButton label={t("sidebar.newChat")} icon={<SquarePen className="h-4 w-4" />} onClick={props.onNewChat} />
        <div className="flex-1" />
        <IconButton
          label={t("sidebar.toggleTheme")}
          icon={props.theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          onClick={props.onToggleTheme}
        />
        <IconButton label={t("sidebar.settings")} icon={<Settings className="h-4 w-4" />} onClick={props.onOpenSettings} />
        <ConnectionBadge collapsed />
      </aside>
    );
  }

  // Expanded: full sidebar
  return (
    <aside className="flex h-full w-full flex-col border-r border-sidebar-border/70 bg-sidebar text-sidebar-foreground">
      <div className="flex items-center justify-between px-3 pb-2 pt-3">
        <span className="text-sm font-bold tracking-tight">
          Repo<span className="text-teal-500">Mate</span>
        </span>
        <div className="flex items-center gap-0.5">
          <IconButton
            label={t("sidebar.toggleTheme")}
            icon={props.theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            onClick={props.onToggleTheme}
          />
          <IconButton
            label={t("sidebar.collapse")}
            icon={<PanelLeftClose className="h-3.5 w-3.5" />}
            onClick={props.onToggleCollapse ?? (() => {})}
          />
        </div>
      </div>

      {/* Onboarding button */}
      <div className="px-2 pb-1">
        <Button
          onClick={props.onOpenOnboarding}
          className={cn(
            "h-9 w-full justify-start gap-2 rounded-full px-3 text-[13px] font-medium",
            props.activeView === "onboarding"
              ? "bg-teal-500/10 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300"
              : "text-sidebar-foreground/90 hover:bg-sidebar-accent hover:text-sidebar-foreground",
          )}
          variant="ghost"
        >
          <Rocket className="h-3.5 w-3.5" />
          {t("sidebar.onboarding")}
        </Button>
      </div>

      {/* New chat button */}
      <div className="px-2 pb-2">
        <Button
          onClick={props.onNewChat}
          className="h-9 w-full justify-start gap-2 rounded-full px-3 text-[13px] font-medium text-sidebar-foreground/90 hover:bg-sidebar-accent hover:text-sidebar-foreground"
          variant="ghost"
        >
          <SquarePen className="h-3.5 w-3.5" />
          {t("sidebar.newChat")}
        </Button>
      </div>

      <div className="flex items-center justify-between px-3 pb-1.5 pt-2.5 text-[11px] font-medium text-muted-foreground">
        <span>{t("sidebar.recent")}</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 rounded-md text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
          onClick={props.onRefresh}
          aria-label={t("sidebar.refreshSessions")}
        >
          <RefreshCcw className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div className="flex-1 overflow-hidden">
        <ChatList
          sessions={props.sessions}
          activeKey={props.activeKey}
          loading={props.loading}
          onSelect={props.onSelect}
          onRequestDelete={props.onRequestDelete}
        />
      </div>
      <Separator className="bg-sidebar-border/50" />
      <div className="flex items-center justify-between gap-2 px-2.5 py-2 text-xs">
        <ConnectionBadge />
        <Button
          onClick={props.onOpenSettings}
          className="h-7 gap-1.5 rounded-md px-2 text-[11px] text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
          variant={props.activeView === "settings" ? "secondary" : "ghost"}
        >
          <Settings className="h-3.5 w-3.5" />
          Settings
        </Button>
      </div>
    </aside>
  );
}
