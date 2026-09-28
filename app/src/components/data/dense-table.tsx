import type { ReactNode } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type DenseColumn<Row> = {
  key: string;
  header: string;
  cell: (row: Row) => ReactNode;
  /** Numeric columns: mono, tabular figures, right-aligned. */
  numeric?: boolean;
  className?: string;
};

type DenseTableProps<Row> = {
  columns: DenseColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  className?: string;
};

/**
 * Compact read-only table for engineering data (nodes, cases, margins).
 * TODO: move to TanStack Table when sorting/filtering/virtualization is needed.
 */
export function DenseTable<Row>({ columns, rows, rowKey, className }: DenseTableProps<Row>) {
  return (
    <div className={cn("overflow-hidden rounded-lg border border-border", className)}>
      <Table className="text-xs">
        <TableHeader className="bg-surface-2">
          <TableRow className="hover:bg-transparent">
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={cn(
                  "h-7 px-2.5 text-[11px] font-medium text-subtle-foreground",
                  column.numeric && "text-right",
                  column.className,
                )}
              >
                {column.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={rowKey(row)} className="hover:bg-surface-2/60">
              {columns.map((column) => (
                <TableCell
                  key={column.key}
                  className={cn(
                    "h-8 px-2.5 py-0",
                    column.numeric && "text-right font-mono tabular-nums",
                    column.className,
                  )}
                >
                  {column.cell(row)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
