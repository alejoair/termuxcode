/**
 * CodeMirror 6 extensions for inline diff display.
 * Shows added lines (green bg) and removed lines (red strikethrough widgets).
 */

import { EditorView, Decoration, WidgetType } from "@codemirror/view";
import { StateEffect, StateField } from "@codemirror/state";

// ── Effects ──────────────────────────────────────────────

const setDiff = StateEffect.define();   // { addRanges: [{from, to}], removeRanges: [{line, content}] }
const clearDiff = StateEffect.define();

// ── Widget for removed lines ─────────────────────────────

class RemovedLineWidget extends WidgetType {
    constructor(content) {
        super();
        this.content = content;
    }
    toDOM() {
        const div = document.createElement('div');
        div.className = 'cm-diff-remove-widget';
        div.textContent = this.content;
        return div;
    }
    ignoreEvent() { return false; }
}

// ── StateField ───────────────────────────────────────────

const diffField = StateField.define({
    create() {
        return Decoration.none;
    },
    update(decorations, tr) {
        for (const effect of tr.effects) {
            if (effect.is(setDiff)) {
                const { addRanges, removeRanges } = effect.value;
                const decos = [];

                // Added lines: line decoration (green bg)
                for (const range of addRanges) {
                    try {
                        const line = tr.state.doc.line(range.line);
                        decos.push(
                            Decoration.line({ class: 'cm-diff-add' }).range(line.from)
                        );
                    } catch (e) { /* line out of range */ }
                }

                // Removed lines: block widget inserted before the specified line
                for (const range of removeRanges) {
                    let insertPos;
                    try {
                        if (range.line <= tr.state.doc.lines) {
                            insertPos = tr.state.doc.line(range.line).from;
                        } else {
                            // After last line
                            insertPos = tr.state.doc.line(tr.state.doc.lines).to;
                        }
                    } catch (e) {
                        continue;
                    }
                    decos.push(
                        Decoration.widget({
                            widget: new RemovedLineWidget(range.content),
                            block: true,
                            side: -1, // insert before the line
                        }).range(insertPos)
                    );
                }

                return Decoration.set(decos, true);
            }
            if (effect.is(clearDiff)) {
                return Decoration.none;
            }
        }
        return decorations.map(tr.changes);
    },
    provide: f => EditorView.decorations.from(f),
});

// ── Public API ───────────────────────────────────────────

export function diffExtension() {
    return [diffField];
}

/**
 * Apply diff decorations to the editor view.
 * @param {EditorView} view
 * @param {{ addRanges: Array<{line: number}>, removeRanges: Array<{line: number, content: string}> }} ranges
 */
export function setDiffRanges(view, ranges) {
    if (!view) return;
    view.dispatch({
        effects: setDiff.of(ranges),
    });
}

/**
 * Clear all diff decorations from the editor view.
 * @param {EditorView} view
 */
export function clearDiffDecorations(view) {
    if (!view) return;
    view.dispatch({
        effects: clearDiff.of(null),
    });
}
