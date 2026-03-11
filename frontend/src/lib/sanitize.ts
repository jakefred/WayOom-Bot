import DOMPurify from "dompurify";

// Allow <audio controls> for [sound:] → <audio> rewrites in CardSerializer.
const CARD_PURIFY_CONFIG = {
  ADD_TAGS: ["audio"],
  ADD_ATTR: ["controls"],
};

/** Sanitize card HTML from the API. Allows <audio controls> for [sound:] rewrites. */
export function sanitizeCardHtml(html: string): string {
  return DOMPurify.sanitize(html, CARD_PURIFY_CONFIG) as string;
}
