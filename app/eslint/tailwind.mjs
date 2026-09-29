/**
 * Local ESLint rules for Tailwind classes (no dependencies).
 *
 * `hestia-tailwind/no-arbitrary-value` forbids arbitrary values (`text-[13px]`, `w-[232px]`,
 * `bg-[#fff]`, `[mask-type:luminance]`): use the spacing scale (`w-58` = 232 px) or a theme
 * token from `src/styles.css` (`text-ui`). Arbitrary variants (`[&>svg]:size-4`,
 * `data-[state=open]:`) are allowed: they select, they do not invent values.
 *
 * Every string literal and template chunk is checked, so class lists kept in constants
 * (`const itemClass = "…"`) are covered too.
 */

/** `text-[13px]`, `-mt-[3px]`, `bg-[#fff]/50` or `[mask-type:luminance]` (utility part only). */
const ARBITRARY_VALUE = /^-?[a-z][\w-]*-\[[^\]]+\](\/[\w.[\]]+)?$|^\[[a-z-]+:[^\]]+\]$/;

/** The utility of a class, without variants (`md:hover:`) or the important modifier (`!`). */
function utilityOf(token) {
  let depth = 0;
  let start = 0;
  for (let i = 0; i < token.length; i++) {
    const char = token[i];
    if (char === "[" || char === "(") depth++;
    else if (char === "]" || char === ")") depth--;
    else if (char === ":" && depth === 0) start = i + 1;
  }
  return token.slice(start).replace(/^!|!$/g, "");
}

function arbitraryClasses(text) {
  return text.split(/\s+/).filter((token) => token && ARBITRARY_VALUE.test(utilityOf(token)));
}

const noArbitraryValue = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Forbid Tailwind arbitrary values: use the scale or a theme token.",
    },
    schema: [],
    messages: {
      arbitrary:
        "Arbitrary Tailwind value `{{name}}`: use the scale (px / 4, e.g. `w-58`) or a theme " +
        "token from src/styles.css (e.g. `text-ui`). See app/AGENTS.md, «Estilo».",
    },
  },
  create(context) {
    const check = (node, text) => {
      for (const name of arbitraryClasses(text)) {
        context.report({ node, messageId: "arbitrary", data: { name } });
      }
    };
    return {
      Literal(node) {
        if (typeof node.value === "string") check(node, node.value);
      },
      TemplateElement(node) {
        check(node, node.value.cooked ?? node.value.raw);
      },
    };
  },
};

export default {
  meta: { name: "hestia-tailwind" },
  rules: { "no-arbitrary-value": noArbitraryValue },
};
