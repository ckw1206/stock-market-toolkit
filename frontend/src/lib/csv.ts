/** Minimal CSV serialization + browser download for client-side exports.
 *
 * Pure-frontend by design: the rows exported here (Screener results, alert
 * history) are already fully fetched into the page before export, so there's
 * no server-side pagination to worry about truncating the output.
 */

function csvEscape(value: unknown): string {
  if (value === null || value === undefined) return "";
  const s = String(value);
  if (/[",\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

export function toCsv<T extends object>(
  rows: T[],
  columns: { key: keyof T; label: string }[]
): string {
  const header = columns.map((c) => csvEscape(c.label)).join(",");
  const body = rows
    .map((row) => columns.map((c) => csvEscape(row[c.key])).join(","))
    .join("\r\n");
  return rows.length > 0 ? `${header}\r\n${body}` : header;
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportCsv<T extends object>(
  filename: string,
  rows: T[],
  columns: { key: keyof T; label: string }[]
): void {
  downloadCsv(filename, toCsv(rows, columns));
}
