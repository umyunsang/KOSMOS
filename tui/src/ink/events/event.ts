// Source: .references/claude-code-sourcemap/restored-src/src/ink/events/event.ts (Claude Code 2.1.88, research-use)
export class Event {
  private _didStopImmediatePropagation = false

  didStopImmediatePropagation(): boolean {
    return this._didStopImmediatePropagation
  }

  stopImmediatePropagation(): void {
    this._didStopImmediatePropagation = true
  }
}
