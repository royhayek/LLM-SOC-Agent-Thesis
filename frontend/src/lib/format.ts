// Pretty-print a reasoning-trace completion when it is JSON (the node outputs are), else leave it.
export function beautifyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}
