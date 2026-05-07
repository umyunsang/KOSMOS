// SPDX-License-Identifier: Apache-2.0
// Spec 1979 T030 — /plugins command tests (FR-015 / FR-016 / FR-019).
// Replaces the Spec 1635 T071 env-var stub tests after T023 refactored
// executePlugins to round-trip plugin_op_request:list via the IPC bridge.

import { describe, it, expect, mock, beforeEach, afterEach } from 'bun:test';

// ---------------------------------------------------------------------------
// Bridge mock — replaces tui/src/ipc/bridgeSingleton at module level so
// executePlugins.ts sees a controllable bridge.
// ---------------------------------------------------------------------------

type StubFrame = Record<string, unknown>;

let _frames: StubFrame[] = [];
const _sentFrames: StubFrame[] = [];

function _makeFramesIterable(): AsyncIterable<StubFrame> {
  // Snapshot at call time so each test starts from a fresh queue.
  const queue = [..._frames];
  return {
    [Symbol.asyncIterator]() {
      return {
        async next() {
          if (queue.length === 0) {
            return { value: undefined, done: true };
          }
          return { value: queue.shift()!, done: false };
        },
      };
    },
  };
}

const _stubBridge = {
  send: (f: StubFrame) => {
    _sentFrames.push(f);
    return true;
  },
  frames: () => _makeFramesIterable(),
};

await mock.module('../../src/ipc/bridgeSingleton.js', () => ({
  getOrCreateKosmosBridge: () => _stubBridge,
  getKosmosBridgeSessionId: () => 'test-session',
}));

await mock.module('../../src/observability/surface.js', () => ({
  emitSurfaceActivation: () => undefined,
}));

// Late import after mock.module so executePlugins resolves to the stubs.
const { executePlugins } = await import('../../src/commands/plugins.js');

beforeEach(() => {
  _frames = [];
  _sentFrames.length = 0;
});

afterEach(() => {
  _frames = [];
  _sentFrames.length = 0;
});

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function _enqueueListResponse(
  correlationId: string,
  entries: object[],
): void {
  const payload = JSON.stringify({ entries });
  _frames = [
    {
      kind: 'payload_start',
      correlation_id: correlationId,
      content_type: 'application/json',
      estimated_bytes: payload.length,
    },
    {
      kind: 'payload_delta',
      correlation_id: correlationId,
      delta_seq: 0,
      payload,
    },
    {
      kind: 'payload_end',
      correlation_id: correlationId,
      delta_count: 1,
      status: 'ok',
    },
    {
      kind: 'plugin_op',
      correlation_id: correlationId,
      op: 'complete',
      result: 'success',
      exit_code: 0,
    },
  ];
}

// ---------------------------------------------------------------------------
// T030 — executePlugins IPC round-trip tests
// ---------------------------------------------------------------------------

describe('executePlugins (Spec 1979 T023 — IPC round-trip)', () => {
  it('emits a plugin_op_request:list frame and returns parsed entries', async () => {
    // Pre-stage backend response BEFORE the call (the test stub iterator
    // captures the queue at frames() call time).
    const correlationId = 'pre-staged';
    _enqueueListResponse(correlationId, [
      {
        plugin_id: 'seoul_subway',
        name: 'seoul-subway',
        version: '1.0.0',
        tier: 'live',
        permission_layer: 1,
        processes_pii: false,
        trustee_org_name: null,
        is_active: true,
        install_timestamp_iso: '2026-04-28T12:00:00Z',
        description_ko: '서울 지하철 도착 정보',
        description_en: 'Seoul subway arrival info',
        search_hint_ko: '지하철 강남역',
        search_hint_en: 'subway gangnam',
      },
    ]);

    // Patch correlation_id on every frame to match whatever executePlugins
    // sends. We do this by intercepting bridge.send.
    const original = _stubBridge.send;
    _stubBridge.send = (f: StubFrame) => {
      const cid = f.correlation_id as string;
      _frames = _frames.map((frame) => ({ ...frame, correlation_id: cid }));
      return original(f);
    };

    const result = await executePlugins();

    _stubBridge.send = original;

    expect(result.error).toBeUndefined();
    expect(result.plugins).toHaveLength(1);
    expect(result.plugins[0]?.id).toBe('seoul_subway');
    expect(result.plugins[0]?.tier).toBe('live');
    expect(result.plugins[0]?.layer).toBe(1);
    expect(result.plugins[0]?.isActive).toBe(true);
    expect(_sentFrames).toHaveLength(1);
    expect(_sentFrames[0]?.kind).toBe('plugin_op');
    expect(_sentFrames[0]?.request_op).toBe('list');
  });

  it('returns error when bridge send returns false (backend exited)', async () => {
    const original = _stubBridge.send;
    _stubBridge.send = () => false;
    const result = await executePlugins();
    _stubBridge.send = original;

    expect(result.error).toContain('IPC bridge unavailable');
    expect(result.plugins).toHaveLength(0);
  });

  it('returns error when payload JSON is malformed', async () => {
    const original = _stubBridge.send;
    _stubBridge.send = (f: StubFrame) => {
      const cid = f.correlation_id as string;
      _frames = [
        { kind: 'payload_start', correlation_id: cid, content_type: 'application/json' },
        { kind: 'payload_delta', correlation_id: cid, delta_seq: 0, payload: '{not-json' },
        { kind: 'payload_end', correlation_id: cid, delta_count: 1, status: 'ok' },
        { kind: 'plugin_op', correlation_id: cid, op: 'complete', result: 'success', exit_code: 0 },
      ];
      _sentFrames.push(f);
      return true;
    };
    const result = await executePlugins();
    _stubBridge.send = original;

    expect(result.error).toContain('JSON parse failed');
    expect(result.plugins).toHaveLength(0);
  });

  it('returns error when backend reports failure', async () => {
    const original = _stubBridge.send;
    _stubBridge.send = (f: StubFrame) => {
      const cid = f.correlation_id as string;
      _frames = [
        { kind: 'plugin_op', correlation_id: cid, op: 'complete', result: 'failure', exit_code: 6 },
      ];
      _sentFrames.push(f);
      return true;
    };
    const result = await executePlugins();
    _stubBridge.send = original;

    expect(result.error).toContain('result=failure');
    expect(result.plugins).toHaveLength(0);
  });

  it('returns empty list when registry has no plugins', async () => {
    const original = _stubBridge.send;
    _stubBridge.send = (f: StubFrame) => {
      const cid = f.correlation_id as string;
      _enqueueListResponse(cid, []);
      _sentFrames.push(f);
      return true;
    };
    const result = await executePlugins();
    _stubBridge.send = original;

    expect(result.error).toBeUndefined();
    expect(result.plugins).toHaveLength(0);
  });

  it('ignores frames with non-matching correlation_id', async () => {
    const original = _stubBridge.send;
    _stubBridge.send = (f: StubFrame) => {
      const cid = f.correlation_id as string;
      // Inject some unrelated frames first, then the matching response.
      _frames = [
        { kind: 'assistant_chunk', correlation_id: 'other-turn', payload: 'noise' },
        { kind: 'tool_use', correlation_id: 'yet-another-turn' },
        ...[
          { kind: 'payload_start', correlation_id: cid, content_type: 'application/json' },
          { kind: 'payload_delta', correlation_id: cid, delta_seq: 0, payload: '{"entries":[]}' },
          { kind: 'payload_end', correlation_id: cid, delta_count: 1, status: 'ok' },
          { kind: 'plugin_op', correlation_id: cid, op: 'complete', result: 'success', exit_code: 0 },
        ],
      ];
      _sentFrames.push(f);
      return true;
    };
    const result = await executePlugins();
    _stubBridge.send = original;

    expect(result.error).toBeUndefined();
    expect(result.plugins).toHaveLength(0);
  });
});
