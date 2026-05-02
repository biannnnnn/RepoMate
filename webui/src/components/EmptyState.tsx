import { MessageSquarePlus, Rocket } from "lucide-react";

import { Button } from "@/components/ui/button";

export function EmptyState({
  onNewChat,
  onGoOnboarding,
}: {
  onNewChat: () => void;
  onGoOnboarding?: () => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <MessageSquarePlus
        className="h-10 w-10 text-muted-foreground"
        aria-hidden
      />
      <div className="space-y-1">
        <p className="text-lg font-medium">No chats yet</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          Start a conversation — your sessions are stored locally and stay
          available across reloads.
        </p>
      </div>
      <div className="flex gap-2">
        {onGoOnboarding && (
          <Button
            onClick={onGoOnboarding}
            variant="outline"
            className="gap-1.5 border-teal-200 text-teal-700 hover:bg-teal-50 dark:border-teal-800 dark:text-teal-300 dark:hover:bg-teal-950"
          >
            <Rocket className="h-4 w-4" />
            Onboard a Repo
          </Button>
        )}
        <Button onClick={onNewChat}>New chat</Button>
      </div>
    </div>
  );
}
