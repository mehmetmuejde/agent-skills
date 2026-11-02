---
name: book-key-insights
description: Use when the user wants to learn the content of a book without reading it: a complete learning document with core messages, all topics and concepts, conclusion, practical examples, verification and self-test questions.
---

# Book Key Insights

Goal: The user wants to learn the content of a book without reading it. The result is a learning document that explains the book's complete concept: core message, every topic and concept, the conclusion, and practical examples. After reading it, the user should understand the book's ideas well enough to apply and explain them. It is not a plot recap and not a review.

## Output language

Write the deliverable in German unless the user asks for another language. These instructions are in English; the output is not.

## Procedure

0. **Triage**: Identify the book type. For fiction, philosophy, textbooks, evidence-heavy or narrative non-fiction, tell the user briefly what a summary cannot carry (evidence, methodology, counterarguments, the narrative or the language itself) and recommend reading the key chapters in full. For fiction, ask whether a plot summary is wanted. Then continue; do not refuse.
1. **Inventory**: Check file type, page count and table of contents. If the file is scanned (no extractable text), use OCR. If it is unreadable, say so openly and do not invent content. Exclude front and back matter (author bio, acknowledgements, marketing text) from the working material, since it can lead to invented content.
2. **Structure first**: Read the table of contents, introduction, concluding chapter, and the openings and endings of chapters to grasp the thesis and the structure.
3. **Then every chapter**: For non-fiction and topic books (e.g. UX guides), process every chapter so that no topic is missing. For long books, work chapter by chapter, collect intermediate results in a file, and write the document in stages (outline first, then section by section). Never summarize the whole book in one pass. Merge the chapter notes into the overall synthesis afterwards, and give the middle chapters the same care as the first and last ones. Never fill a chapter in from guesswork.
   - Note page or section references for every key claim.
4. **Own words**: Do not copy long passages. Direct quotes only if the exact wording matters, and then under 15 words.
5. **Verify**: Check every quote against the text. Spot-check numbers, names and dates, especially from the middle of the book. Compare the outline with the table of contents: what is missing? List open doubts and affected chapters in the document.
6. **Deliver** in the structure below.

## Length

The document is detailed, but it has an upper limit: about 15 % of the book's word count, and at most 12,000 words (roughly 25 pages), whichever is lower. These are rules of thumb, not measured values. Within the limit, choose completeness over brevity: explain every concept, the reasoning, steps and examples properly. To stay within the limit, drop repetition, filler examples and anecdotes, never concepts. If the book is so dense that the limit would force cutting concepts, do not cut silently: tell the user and offer a second part. A short version (1-2 pages) is only produced if the user explicitly asks for it.

## Output structure

1. **The book in three sentences**: what it is about, which problem it solves, who it is for.
2. **Core messages**: the most important theses of the book.
3. **Key topics and concepts**: for each concept, a full explanation (what it is, how it works, the author's reasoning, steps or rules where the book gives them), why it matters, and concrete examples from everyday life or work.
4. **Chapter overview**: per chapter, the key lesson and how it connects to the others.
5. **The conclusion**: what the author concludes or recommends at the end.
6. **In practice**: how to apply the knowledge, with examples from daily life, plus a checklist or rules of the form "if X, then Y".
7. **Rules of thumb**: the most important rules for quick lookup.
8. **Assessment**: how strong the evidence is, where the book is weak or outdated, what is missing. Only what can be justified from the book itself. State the author's position fairly before criticizing it.
9. **Self-test questions**: at least one question per key concept (minimum 5), answers in a separate block at the end of the document so they can be covered up.

## Delivery

Provide it as a document, not only in chat. PDF or Word only if the user names the format. A summary alone is not retained well: recommend asking the self-test questions from memory after 1, 7 and 30 days. At the end, briefly offer to deepen topics as a quiz, flashcards or in conversation, so the user actually learns the material.

## Rules

- Do not invent: what is not in the book must not be presented as the book's claim. Mark own examples as such. Mark anything the text does not support as "not in the text".
- If parts are missing or unreadable, say which chapters are affected.
- If only the book's name is known and no file is available, say so openly and work from research (reviews, publisher information), not from recall. State clearly that the result is not a faithful summary of the text.
