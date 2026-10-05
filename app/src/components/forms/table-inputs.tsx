import type { ComponentProps } from "react";
import { NumberField as NumberFieldPrimitive } from "@base-ui/react/number-field";
import { cn } from "@/lib/utils";
import type { SelectOption } from "./select-field";

/** A cell of an editable table (`Table/*`): fixed height, row rule. */
export const tableCellClass = "h-8 border-b border-border px-2.5";
/** A header cell of an editable table. */
export const tableHeadClass =
  "h-7 border-b border-border px-2.5 text-left text-2xs font-medium text-subtle-foreground";

const inputClass = cn(
  "h-full w-full bg-transparent px-2.5 text-xs outline-none placeholder:text-subtle-foreground",
  "focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-inset",
  "aria-invalid:ring-1 aria-invalid:ring-error aria-invalid:ring-inset",
);

type TableInputProps = {
  /** Accessible name: a table cell has no visible label. */
  label: string;
  /** Validation message: marks the cell invalid and shows on hover. */
  error?: string;
  /** The value differs from the applied one; `hint` (e.g. "Aplicado: 20 °C") shows on hover. */
  modified?: boolean;
  hint?: string;
  className?: string;
};

function stateProps({ label, error, modified, hint }: TableInputProps) {
  return {
    "aria-label": label,
    "aria-invalid": error ? true : undefined,
    title: error ?? hint,
    className: modified ? "ring-1 ring-primary ring-inset" : undefined,
  };
}

/** Free text inside a table cell. Empty is `null`. */
export function TableTextInput({
  value,
  onChange,
  placeholder = "—",
  autoFocus,
  onBlur,
  onKeyDown,
  ...props
}: TableInputProps &
  Pick<ComponentProps<"input">, "autoFocus" | "onBlur" | "onKeyDown"> & {
    value: string | null;
    onChange: (value: string | null) => void;
    placeholder?: string;
  }) {
  const state = stateProps(props);
  return (
    <input
      {...state}
      autoFocus={autoFocus}
      onBlur={onBlur}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      className={cn(inputClass, state.className, props.className)}
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value === "" ? null : event.target.value)}
    />
  );
}

/** A number inside a table cell (mono, "en-US" decimals). Empty is `null`. */
export function TableNumberInput({
  value,
  onValueChange,
  ...props
}: TableInputProps & {
  value: number | null;
  onValueChange: (value: number | null) => void;
}) {
  const state = stateProps(props);
  return (
    <NumberFieldPrimitive.Root
      locale="en-US"
      format={{ maximumFractionDigits: 6, useGrouping: false }}
      value={value}
      onValueChange={(next) => onValueChange(next ?? null)}
      className="h-full"
    >
      <NumberFieldPrimitive.Input
        {...state}
        placeholder="—"
        className={cn(
          inputClass,
          "font-mono tabular-nums placeholder:font-sans",
          state.className,
          props.className,
        )}
      />
    </NumberFieldPrimitive.Root>
  );
}

/** One option of a list inside a table cell; «—» is no value (`null`). */
export function TableSelect({
  value,
  options,
  onChange,
  ...props
}: TableInputProps & {
  value: string | null;
  options: SelectOption[];
  onChange: (value: string | null) => void;
}) {
  const state = stateProps(props);
  return (
    <select
      {...state}
      className={cn(
        inputClass,
        "cursor-pointer appearance-none [&>option]:bg-surface",
        value === null && "text-subtle-foreground",
        state.className,
        props.className,
      )}
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value === "" ? null : event.target.value)}
    >
      <option value="">—</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
