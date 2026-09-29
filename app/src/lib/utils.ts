import { createCn } from "cn/config";

/**
 * Join classes and resolve Tailwind conflicts (clsx + tailwind-merge semantics).
 *
 * The theme tokens added in `styles.css` must be registered here: otherwise `text-ui` looks
 * like a text color, and `cn("text-ui", "text-muted-foreground")` would drop the size.
 */
export const cn = createCn({
  extend: {
    classGroups: {
      "font-size": [{ text: ["3xs", "2xs", "ui", "title"] }],
      tracking: [{ tracking: ["label"] }],
    },
  },
});
