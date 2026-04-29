// KOSMOS-2293: extra-usage-core.ts deleted (claude.ai SaaS billing dead).
export async function call(): Promise<{ type: 'text'; value: string }> {
  return {
    type: 'text',
    value: 'Extra usage is not available in KOSMOS. Usage is managed via FriendliAI.',
  }
}
