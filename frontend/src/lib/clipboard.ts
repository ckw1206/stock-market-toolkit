// Clipboard API is only available in secure contexts (HTTPS / localhost).
// In non-secure contexts navigator.clipboard is undefined, so we fall back to
// the deprecated document.execCommand("copy") path — it is the only option that
// works over plain HTTP on a LAN.

export async function copyText(value: string): Promise<boolean> {
  if (navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      // permission denied or other failure — fall through to legacy path
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "-9999px";
  document.body.appendChild(textarea);
  try {
    textarea.select();
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    document.body.removeChild(textarea);
  }
}
