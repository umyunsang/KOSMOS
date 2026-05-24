import { afterEach, describe, expect, it } from 'bun:test'
import { render } from 'ink-testing-library'
import React from 'react'
import type { AdapterManifestSyncFrame } from '../../src/ipc/frames.generated.js'
import { Text } from '../../src/ink.js'
import {
  clearManifestCache,
  ingestManifestFrame,
} from '../../src/services/api/adapterManifest.js'
import { waitForFrame } from '../../src/test-utils/waitForFrame.js'
import { getEmptyToolPermissionContext, type Tools } from '../../src/Tool.js'
import { useMergedTools } from '../../src/hooks/useMergedTools.js'

function adapterManifestFrame(): AdapterManifestSyncFrame {
  return {
    kind: 'adapter_manifest_sync',
    role: 'backend',
    session_id: 'session-test',
    correlation_id: 'correlation-test',
    ts: '2026-05-25T00:00:00.000Z',
    entries: [
      {
        tool_id: 'nmc_aed_site_locate',
        name: 'NMC AED site lookup',
        primitive: 'find',
        source_mode: 'live',
        policy_authority_url: 'https://www.e-gen.or.kr/',
        search_hint: 'AED automated external defibrillator location',
        llm_description: 'Find AED installation sites by Korean region.',
        input_schema_json: {
          type: 'object',
          properties: {
            q0: { type: 'string', description: 'Province or metropolitan city.' },
            q1: { type: 'string', description: 'District, city, or county.' },
          },
          required: ['q0', 'q1'],
          additionalProperties: false,
        },
      },
      {
        tool_id: 'kma_current_observation',
        name: 'KMA current observation',
        primitive: 'find',
        source_mode: 'live',
        policy_authority_url: 'https://apihub.kma.go.kr/',
        search_hint: 'KMA current weather observation',
        llm_description: 'Fetch current weather observations by KMA grid.',
        input_schema_json: {
          type: 'object',
          properties: {
            nx: { type: 'integer', description: 'KMA grid x coordinate.' },
            ny: { type: 'integer', description: 'KMA grid y coordinate.' },
          },
          required: ['nx', 'ny'],
          additionalProperties: false,
        },
      },
    ],
    manifest_hash: '0'.repeat(64),
    emitter_pid: 12345,
  }
}

function ToolNamesProbe({
  initialTools = [],
  mcpTools = [],
}: {
  initialTools?: Tools
  mcpTools?: Tools
}) {
  const tools = useMergedTools(
    initialTools,
    mcpTools,
    getEmptyToolPermissionContext(),
  )
  return <Text>{tools.map((tool) => tool.name).join('|')}</Text>
}

afterEach(() => {
  clearManifestCache()
})

describe('useMergedTools adapter manifest updates', () => {
  it('recomputes the render-visible tool pool after backend manifest sync', async () => {
    clearManifestCache()
    const result = render(<ToolNamesProbe />)

    expect(result.lastFrame() ?? '').not.toContain('nmc_aed_site_locate')
    expect(result.lastFrame() ?? '').not.toContain('kma_current_observation')

    ingestManifestFrame(adapterManifestFrame())

    const observed = await waitForFrame(
      result,
      (frame) =>
        frame.includes('nmc_aed_site_locate') &&
        frame.includes('kma_current_observation'),
      {
        deadlineMs: 1_000,
        describe: 'adapter manifest tools are visible to message renderers',
      },
    )

    expect(observed.lastFrame).toContain('nmc_aed_site_locate')
    expect(observed.lastFrame).toContain('kma_current_observation')
  })
})
