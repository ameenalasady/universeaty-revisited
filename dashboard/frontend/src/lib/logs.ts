export type LogLevel = "INFO" | "WARNING" | "ERROR" | "CRITICAL" | "DEBUG" | "OTHER";

export interface ParsedLogLine {
  id: number;
  raw: string;
  ts: string | null;
  level: LogLevel;
  logger: string | null;
  thread: string | null;
  message: string;
}

const LINE_RE =
  /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (CRITICAL|ERROR|WARNING|INFO|DEBUG) - (\S+) - (\S+) - (.*)$/;

let nextId = 0;

export function parseLogLine(raw: string): ParsedLogLine {
  const match = LINE_RE.exec(raw);
  if (match) {
    return {
      id: nextId++,
      raw,
      ts: match[1],
      level: match[2] as LogLevel,
      logger: match[3],
      thread: match[4],
      message: match[5],
    };
  }
  return {
    id: nextId++,
    raw,
    ts: null,
    level: "OTHER",
    logger: null,
    thread: null,
    message: raw,
  };
}

export function parseLogLines(lines: string[]): ParsedLogLine[] {
  return lines.map(parseLogLine);
}
