// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T071 /plugins command tests (FR-031, US5).

import { describe, it, expect, afterEach } from 'bun:test';
import { executePlugins } from '../../src/commands/plugins.js';
import type { PluginEntry } from '../../src/components/plugins/PluginBrowser.js';

afterEach(() => {
  delete process.env['KOSMOS_PLUGIN_REGISTRY'];
});

describe('executePlugins (FR-031)', () => {
  it('returns empty array when no registry env var', () => {
    const result = executePlugins();
    expect(Array.isArray(result.plugins)).toBe(true);
    expect(result.plugins).toHaveLength(0);
  });

  it('parses single plugin from env', () => {
    const plugin: PluginEntry = {
      id: 'my-plugin',
      name: 'My Plugin',
      version: '2.1.0',
      description_ko: '내 플러그인',
      description_en: 'My plugin',
      isActive: false,
    };
    process.env['KOSMOS_PLUGIN_REGISTRY'] = JSON.stringify([plugin]);
    const result = executePlugins();
    expect(result.plugins).toHaveLength(1);
    expect(result.plugins[0]?.id).toBe('my-plugin');
    expect(result.plugins[0]?.isActive).toBe(false);
  });

  it('parses multiple plugins', () => {
    const plugins: PluginEntry[] = [
      { id: 'p1', name: 'P1', version: '1.0', description_ko: '1', description_en: '1', isActive: true },
      { id: 'p2', name: 'P2', version: '2.0', description_ko: '2', description_en: '2', isActive: false },
    ];
    process.env['KOSMOS_PLUGIN_REGISTRY'] = JSON.stringify(plugins);
    const result = executePlugins();
    expect(result.plugins).toHaveLength(2);
  });

  it('returns empty array on invalid JSON', () => {
    process.env['KOSMOS_PLUGIN_REGISTRY'] = 'not-json';
    const result = executePlugins();
    expect(result.plugins).toHaveLength(0);
  });

  it('returns empty array when env var is an object (not array)', () => {
    process.env['KOSMOS_PLUGIN_REGISTRY'] = JSON.stringify({ id: 'not-an-array' });
    const result = executePlugins();
    expect(result.plugins).toHaveLength(0);
  });
});
