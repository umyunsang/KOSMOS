/* eslint-disable custom-rules/no-process-exit -- CLI subcommand handler intentionally exits */
// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — FriendliAI session-auth CLI stubs.
//
// FriendliAI API keys are kept in the user memdir in UMMAYA. The interactive TUI
// /login command stores a token so it is restored on next app launch and can be
// cleared later via /logout.

import {
  clearFriendliCredential,
  getFriendliCredentialSource,
} from '../../utils/friendliAuth.js'
import { jsonStringify } from '../../utils/slowOperations.js'

export async function installOAuthTokens(_tokens: unknown): Promise<void> {
  throw new Error('UMMAYA does not install Anthropic OAuth tokens. Use /login inside the TUI.')
}

export async function authLogin(_opts: {
  email?: string
  sso?: boolean
  console?: boolean
  claudeai?: boolean
} = {}): Promise<void> {
  process.stdout.write(
    'UMMAYA FriendliAI login stores the token in your local user store. Start the TUI and run /login; the token is stored locally and restored on the next launch.\n',
  )
  process.exit(0)
}

export async function authStatus(opts: {
  json?: boolean
  text?: boolean
}): Promise<void> {
  const source = getFriendliCredentialSource()
  const loggedIn = source !== 'none'

  if (opts.text) {
    if (loggedIn) {
      process.stdout.write(`FriendliAI API key: ${source}\n`)
    } else {
      process.stdout.write(
        'Not logged in. Start the UMMAYA TUI and run /login to save your token locally.\n',
      )
    }
  } else {
    process.stdout.write(
      jsonStringify(
        {
          loggedIn,
          authMethod: loggedIn ? 'friendli_api_key' : 'none',
          apiProvider: 'friendliai',
          apiKeySource: loggedIn ? source : null,
          persistence: 'user_memdir',
        },
        null,
        2,
      ) + '\n',
    )
  }

  process.exit(loggedIn ? 0 : 1)
}

export async function authLogout(): Promise<void> {
  clearFriendliCredential()
  process.stdout.write(
    'FriendliAI credential cleared from process state and local disk store. In the TUI, run /logout to clear the stored token and close the backend bridge.\n',
  )
  process.exit(0)
}
