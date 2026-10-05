# Explain writing rules

These are the complete house rules for Explain. They are inspired by ASD-STE100 and the user's preferred writing style.
They do not replace the official standard or its dictionary.

## Choose the mode

Use **80% STE** for normal replies, explanations, messages, teaching, and commit or PR text.
Use **strict STE** for procedures, runbooks, safety text, UI copy, and error messages.
A mixed document can use strict steps and relaxed explanatory paragraphs.
An explicit user choice takes precedence.

Both modes use the sentence limits below. In 80% mode, allow a common word when its replacement makes the sentence less clear.
A useful connective, such as “however,” can remain. Keep the meaning, uncertainty, and technical detail intact.
Strict mode applies every house rule and checks all word choices.

“80%” does not measure compliance. “Strict” does not certify compliance with the official standard.
For a formal compliance request, consult the official writing rules and dictionary, including approved meanings and parts of speech.
If these are unavailable, state that the dictionary check is incomplete. Continue useful writing work without claiming full compliance.

## Ten rules

1. **One topic per sentence.** Use no more than 20 words in a procedure sentence or 25 words in a description.
2. **One instruction per step.** Start each step with a command. Write “Remove the file,” not “The file should be removed.”
3. **Active voice.** Name the actor when it matters. A description can use passive voice when the actor is unknown or irrelevant. Procedures cannot.
4. **Accurate tense.** Use present tense for descriptions and past tense for completed facts. Prefer present tense for predictable system behavior. Preserve real timing and uncertainty. Never describe planned work as complete.
5. **Clear words with stable meanings.** Use the word guide. Keep each technical term consistent. Formal STE also requires checking approved meanings and parts of speech.
6. **Keep articles and demonstratives.** Write “Set the value” and “Check this file.” Avoid compressed notes that force the reader to guess.
7. **Short noun groups.** Use no more than three consecutive nouns. Expand longer groups with “of,” “for,” or another clear relationship. Keep exact technical names unchanged.
8. **Direct verbs.** Write “check” instead of “perform a check.” Write “select” instead of “make a selection.”
9. **Warnings before actions.** Put a needed warning in a separate sentence before the affected step. State the consequence. Do not invent warnings for harmless actions.
10. **Short paragraphs.** Give each paragraph one topic and no more than six sentences. Start with the topic. Number steps; use bullets for parallel items.

These examples show how to apply the rules:

| Before | After |
| --- | --- |
| The configuration should be modified by the operator. | Change the configuration. |
| Perform a verification of the output. | Check the output. |
| Database connection pool timeout setting | The timeout setting for the database connection pool |
| The deployment was successful. | The deployment passed its checks. |

Use the last example only when the checks actually passed. Simpler language must not invent evidence.

## Protected text

Do not rewrite code, identifiers, commands, paths, exact error strings, quotations, legal text, or user-authored text unless asked.
Apply the rules to your own explanation around those items.
Technical names are permitted as nouns. Keep their spelling and capitalization.
Do not replace a technical verb merely because it is absent from the house word guide.
For formal STE, check the standard's rules for technical nouns and verbs.

## Review before delivery

1. Draft the answer in the user's requested voice and language.
2. Separate protected text from the prose you can edit.
3. Check each editable sentence against the ten rules.
4. Replace words from the avoid column when the replacement preserves their meaning.
5. Count the words in each sentence. Split sentences that exceed the limit.
6. Check that each procedure step contains one command.
7. Check that each needed warning comes before its step.
8. Check that the edit preserves facts, uncertainty, conditions, and technical names.

For a consistent house count, count whitespace-separated words after removing Markdown markers. Count a technical name as it appears.
Apply these limits to editable sentences, not code blocks or protected quotations.
A script or grammar tool can help flag issues. It cannot establish meaning, safety, or full STE compliance.

In strict house mode, finish with no avoid-list terms in editable prose, no sentences above the limit, and no passive procedure steps.
In 80% mode, review each avoid-list term and keep it only when it gives the reader a clearer meaning.
Do not change a quotation to make a check pass. Report that exemption when the user requests an audit.

## Sources and limits

The official standard contains writing rules and a controlled dictionary. It also permits specified technical nouns and verbs.
See [ASD's overview](https://www.asd-ste100.org/about_STE.html) and [official downloads](https://asd-ste100.org/STE_downloads.html).

The style and format approach is inspired by [Karpathy's post](https://x.com/karpathy/status/2105819303471976479).
These house rules are original project guidance. They are not an official copy, endorsement, or certification of ASD-STE100.
