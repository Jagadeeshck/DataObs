const replacements: Array<[RegExp, string | ((substring: string) => string)]> =
  [
    [/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, "[email]"],
    [/\b\d{12}\b/g, "[account]"],
    [/arn:aws[^\s"']+/gi, "[aws-arn]"],
    [
      /(authorization|cookie|token|password|secret|external[_-]?id)\s*[:=]\s*[^\s,;]+/gi,
      "$1=[redacted]",
    ],
    [/(postgres|mysql|mongodb(?:\+srv)?):\/\/[^\s]+/gi, "[connection-string]"],
    [/https?:\/\/[^\s?#]+\?[^\s#]*/gi, (value) => value.split("?")[0]],
    [/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "[ip]"],
  ];

export function redact(value: unknown, maximumLength = 240): string {
  let safe =
    value instanceof Error
      ? `${value.name}: ${value.message}`
      : String(value ?? "unknown");
  for (const [pattern, replacement] of replacements)
    safe =
      typeof replacement === "string"
        ? safe.replace(pattern, replacement)
        : safe.replace(pattern, replacement);
  return safe.replace(/[\r\n\t]+/g, " ").slice(0, maximumLength);
}

export function fingerprint(parts: readonly string[]) {
  let hash = 2166136261;
  const input = parts.map((part) => redact(part, 80).toLowerCase()).join("|");
  for (let index = 0; index < input.length; index++) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}
