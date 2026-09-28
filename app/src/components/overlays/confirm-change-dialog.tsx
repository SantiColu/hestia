import { useState, type ReactNode } from "react";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { JustificationField } from "@/components/forms/justification-field";
import { KeyValue } from "@/components/data/readouts";
import type { FieldChange } from "@/components/workflow/history-item";

type ConfirmChangeDialogProps = {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Element that opens the dialog (rendered via Base UI's trigger). */
  trigger?: ReactNode;
  title?: string;
  /** Impact reported by the API, e.g. which stages become outdated. */
  summary?: string;
  changes: FieldChange[];
  confirmLabel?: string;
  onConfirm: (justification: string) => void;
};

/** Every write goes through here: shows the diff and asks for a justification. */
export function ConfirmChangeDialog({
  open,
  onOpenChange,
  trigger,
  title = "Confirmar cambio",
  summary,
  changes,
  confirmLabel = "Aplicar cambio",
  onConfirm,
}: ConfirmChangeDialogProps) {
  const [justification, setJustification] = useState("");
  const canConfirm = justification.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {trigger}
      <DialogContent className="gap-0 rounded-lg bg-surface p-0 ring-border-strong sm:max-w-[480px]">
        <DialogHeader className="px-5 pt-4 pb-3">
          <DialogTitle className="text-[15px] font-semibold">{title}</DialogTitle>
          {summary && (
            <DialogDescription className="text-[13px] text-muted-foreground">
              {summary}
            </DialogDescription>
          )}
        </DialogHeader>
        <div className="flex flex-col gap-4 px-5 pb-5">
          <div className="rounded-lg border border-border bg-background px-3 py-1">
            {changes.map((change) => (
              <KeyValue
                key={change.field}
                className="last:border-b-0"
                label={<span className="font-mono">{change.field}</span>}
                value={`${change.from} → ${change.to}`}
              />
            ))}
          </div>
          <JustificationField
            value={justification}
            onChange={(event) => setJustification(event.target.value)}
          />
        </div>
        <DialogFooter className="mx-0 mb-0 rounded-b-lg border-border bg-transparent px-5 py-3">
          <DialogClose render={<Button variant="ghost" />}>Cancelar</DialogClose>
          <Button disabled={!canConfirm} onClick={() => onConfirm(justification.trim())}>
            <Check data-icon="inline-start" />
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
