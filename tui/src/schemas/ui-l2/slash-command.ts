// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — SlashCommandCatalogEntry (data-model.md §4,
// FR-014/029). Single source of truth for autocomplete dropdown and
// /help 4-group output. Schema mirrors contracts/slash-commands.schema.json.
import { z } from 'zod';

export const SlashCommandGroup = z.enum([
  'session',
  'permission',
  'tool',
  'storage',
]);
export type SlashCommandGroupT = z.infer<typeof SlashCommandGroup>;

export const SlashCommandCatalogEntry = z.object({
  name: z.string().regex(/^\/[a-z][a-z0-9-]*( [a-z0-9-]+)?$/),
  group: SlashCommandGroup,
  description_ko: z.string().min(1),
  description_en: z.string().min(1),
  arg_signature: z.string().nullable(),
  hidden: z.boolean().default(false),
});
export type SlashCommandCatalogEntryT = z.infer<typeof SlashCommandCatalogEntry>;

export const SlashCommandCatalog = z.array(SlashCommandCatalogEntry);
export type SlashCommandCatalogT = z.infer<typeof SlashCommandCatalog>;

export const GROUP_ORDER: readonly SlashCommandGroupT[] = [
  'session',
  'permission',
  'tool',
  'storage',
] as const;

export function groupCatalog(
  entries: readonly SlashCommandCatalogEntryT[],
): Record<SlashCommandGroupT, SlashCommandCatalogEntryT[]> {
  const out: Record<SlashCommandGroupT, SlashCommandCatalogEntryT[]> = {
    session: [],
    permission: [],
    tool: [],
    storage: [],
  };
  for (const e of entries) {
    if (e.hidden) continue;
    out[e.group].push(e);
  }
  for (const g of GROUP_ORDER) {
    out[g].sort((a, b) => a.name.localeCompare(b.name));
  }
  return out;
}
