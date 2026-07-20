export function absoluteInviteLink(link: string): string {
  if (!link) return link;
  if (/^[a-zA-Z][a-zA-Z0-9+\-.]*:/.test(link)) return link;
  if (link.startsWith("//")) return link;
  if (link.startsWith("/")) return window.location.origin + link;
  return link;
}
