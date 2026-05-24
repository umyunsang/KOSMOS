import { describe, expect, test } from 'bun:test'
import { buildTool, getEmptyToolPermissionContext } from '../../src/Tool.js'
import { assembleToolPool, getTools } from '../../src/tools.js'
import { z } from 'zod/v4'
import {
  clearManifestCache,
  ingestManifestFrame,
} from '../../src/services/api/adapterManifest.js'
import type { AdapterManifestSyncFrame } from '../../src/ipc/frames.generated.js'
import { isDeferredTool } from '../../src/tools/ToolSearchTool/prompt.js'

const context7Tool = buildTool({
  name: 'mcp__context7__resolve-library-id',
  inputSchema: z.object({ libraryName: z.string() }),
  isEnabled: () => true,
  isReadOnly: () => true,
  isConcurrencySafe: () => true,
  description: async () => 'Context7 resolver',
  prompt: async () => 'Resolve documentation libraries',
  validateInput: async () => ({ result: true }),
  call: async () => ({ data: {} }),
  userFacingName: () => 'context7',
  mapToolResultToToolResultBlockParam: (data, toolUseID) => ({
    type: 'tool_result',
    tool_use_id: toolUseID,
    content: JSON.stringify(data),
  }),
  renderToolUseMessage: () => null,
  mcpInfo: { serverName: 'context7', toolName: 'resolve-library-id' },
})

describe('UMMAYA model-facing tool surface', () => {
  test('exposes public-service primitives, not Claude Code developer tools', () => {
    const names = getTools(getEmptyToolPermissionContext()).map(tool => tool.name)

    expect(names).toEqual(
      expect.arrayContaining(['ToolSearch', 'find', 'locate', 'send', 'check']),
    )
    expect(names).not.toContain('Bash')
    expect(names).not.toContain('Read')
    expect(names).not.toContain('Write')
    expect(names).not.toContain('Edit')
    expect(names).not.toContain('Glob')
    expect(names).not.toContain('Grep')
    expect(names).not.toContain('NotebookEdit')
  })

  test('keeps CC assembly shape while external MCP tools stay out of citizen turns', () => {
    clearManifestCache()
    const names = assembleToolPool(getEmptyToolPermissionContext(), [
      context7Tool,
    ]).map(tool => tool.name)

    expect(names).toEqual(['check', 'find', 'locate', 'send', 'ToolSearch'])
    expect(names).not.toContain('mcp__context7__resolve-library-id')
  })

  test('loads synced backend adapters as first-turn CC Tool objects', () => {
    clearManifestCache()
    ingestManifestFrame({
      kind: 'adapter_manifest_sync',
      version: '1.0',
      session_id: 'test-session',
      correlation_id: '01HXKQ7Z3M1V8K2YQ8A6P4F9C1',
      ts: new Date().toISOString(),
      role: 'backend',
      frame_seq: 0,
      entries: [
        {
          tool_id: 'kma_current_observation',
          name: 'KMA Current Observation',
          primitive: 'find',
          policy_authority_url: 'https://apihub.kma.go.kr/',
          source_mode: 'live',
          search_hint: 'KMA current weather observation getUltraSrtNcst',
          llm_description:
            'KMA APIHub current weather observation adapter. Use latitude-derived KMA grid values from locate before calling this tool.',
          input_schema_json: {
            type: 'object',
            properties: {
              nx: { type: 'integer', description: 'KMA grid X coordinate.' },
              ny: { type: 'integer', description: 'KMA grid Y coordinate.' },
            },
            required: ['nx', 'ny'],
            additionalProperties: false,
          },
        },
      ],
      manifest_hash: 'a'.repeat(64),
      emitter_pid: 12345,
    } satisfies AdapterManifestSyncFrame)

    const tools = assembleToolPool(getEmptyToolPermissionContext(), [])
    const adapter = tools.find(tool => tool.name === 'kma_current_observation')

    expect(adapter).toBeDefined()
    expect(adapter?.alwaysLoad).toBe(true)
    expect(adapter ? isDeferredTool(adapter) : true).toBe(false)
    expect(adapter?.inputJSONSchema?.properties).toHaveProperty('nx')
    expect(adapter?.userFacingName({ nx: 97, ny: 74 })).toBe('find')
    expect(
      adapter?.renderToolUseMessage({ nx: 97, ny: 74 }, { verbose: false }),
    ).toBe('kma_current_observation')
  })
})
