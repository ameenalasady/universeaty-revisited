import type { TimeblockInfo } from "@/services/api";

/**
 * Format timeblocks into a human-readable schedule string.
 * Deduplicates identical (day, start, end) entries and groups by day.
 * Example output: "Mon 08:30–09:20 | Wed 08:30–09:20"
 */
export function formatTimeblocks(timeblocks?: TimeblockInfo[]): string {
  if (!timeblocks || timeblocks.length === 0) return "";
  const seen = new Set<string>();
  const grouped: Record<string, string[]> = {};
  for (const tb of timeblocks) {
    const key = `${tb.day_name}|${tb.start}|${tb.end}`;
    if (seen.has(key)) continue;
    seen.add(key);
    if (!grouped[tb.day_name]) grouped[tb.day_name] = [];
    grouped[tb.day_name].push(`${tb.start}\u2013${tb.end}`);
  }
  return Object.entries(grouped)
    .map(([day, times]) => `${day} ${times.join(", ")}`)
    .join(" | ");
}

export function isOnline(attrs?: Record<string, string[]>): boolean {
  return !!attrs?.ONLN && attrs.ONLN.length > 0;
}

export function isEvening(attrs?: Record<string, string[]>): boolean {
  return !!attrs?.EVE && attrs.EVE.length > 0;
}
