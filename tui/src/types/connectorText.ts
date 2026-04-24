// [P0 baseline stub] CC-native `connectorText` types were not captured in the
// restored source. The minimal shape below keeps consumers type-safe; the
// `isConnectorTextBlock` guard always returns `false` so no connector-text
// branch is taken at runtime. Full fidelity is tracked in Epic #1633.

export interface ConnectorTextBlock {
  type: 'connector_text';
  text: string;
  connector_id?: string;
}

export function isConnectorTextBlock(block: unknown): block is ConnectorTextBlock {
  return false;
}
