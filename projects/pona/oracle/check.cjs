/* check.cjs -- batch interface to the vendored telo misikeke grammar checker.
 *
 * stdin:  JSON array of strings (sentences / short texts)
 * stdout: JSON array (same order) of {errors: [{rule, category, text}]}
 *
 * Error definition matches upstream tests.js: a token counts as an error when
 * its matched rule declares a category. An empty errors list = the oracle
 * accepts the sentence.
 *
 *   node projects/pona/oracle/check.cjs < sentences.json
 */
const fs = require("fs");
const path = require("path");

// Parser.js console.logs unmatched input before throwing; stdout is our JSON
// channel, so route library logging to stderr.
console.log = console.error;

const VENDOR = path.join(__dirname, "vendor");
const rulesFunctions = require(path.join(VENDOR, "telo-misikeke", "public", "rules.js"));
const ParserWithCallbacks = require(path.join(VENDOR, "telo-misikeke", "public", "Parser.js")).ParserWithCallbacks;

const linku = JSON.parse(fs.readFileSync(path.join(VENDOR, "linku.json"), "utf8"));
const words = rulesFunctions.parseLipuLinku(linku);
const rules = rulesFunctions.build_rules(words);
const parser = new ParserWithCallbacks(rules);

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const out = input.map((sentence) => {
    let tokens;
    try {
        tokens = parser.tokenize(sentence);
    } catch (e) {
        return { errors: [{ rule: "PARSER_CRASH", category: "crash", text: String(e).slice(0, 120) }] };
    }
    const errors = tokens
        .filter((t) => t.ruleName && rules[t.ruleName] && rules[t.ruleName].category)
        .map((t) => ({
            rule: t.ruleName,
            category: rules[t.ruleName].category,
            text: (t.text || "").slice(0, 60),
        }));
    return { errors };
});
process.stdout.write(JSON.stringify(out));
