import { useState, type ReactNode } from "react";
import { Check, X } from "lucide-react";
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
      <DialogContent
        showCloseButton={false}
        className="gap-0 rounded-lg bg-surface p-0 ring-border-strong sm:max-w-120"
      >
        <DialogHeader className="flex-row items-center gap-3 px-5 py-4">
          <DialogTitle className="flex-1 text-title font-semibold">{title}</DialogTitle>
          <DialogClose render={<Button variant="outline" size="icon-sm" aria-label="Cerrar" />}>
            <X />
          </DialogClose>
        </DialogHeader>
        <div className="flex flex-col gap-4 px-5 pt-1 pb-5">
          {summary && (
            <DialogDescription className="text-ui leading-normal text-muted-foreground">
              {summary}
            </DialogDescription>
          )}
          {changes.length > 0 && (
            <div className="rounded-lg border border-border bg-background px-3 py-1">
              {changes.map((change) => (
                <KeyValue
                  key={change.field}
                  className="last:border-b-0"
                  label={<span className="font-mono">{change.field}</span>}
                  value={change.value ?? `${change.from} → ${change.to}`}
                />
              ))}
            </div>
          )}
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
