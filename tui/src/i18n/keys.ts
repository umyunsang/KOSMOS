export interface I18nBundle {
  // Coordinator / lifecycle
  sessionStarting: string;
  sessionReady: string;
  sessionEnded: string;

  // Commands
  commandNotFound: (name: string) => string;
  commandHelp: string;

  // Permission gauntlet
  permissionPromptTitle: string;
  permissionPromptBody: (toolName: string) => string;
  permissionApproved: string;
  permissionDenied: string;

  // Errors
  toolCallFailed: (toolId: string, reason: string) => string;
  workerCrashed: (reason: string) => string;
  ipcDecodeError: string;

  // Renderer status lines
  toolRunning: (toolId: string) => string;
  toolSucceeded: (toolId: string) => string;
  toolFailed: (toolId: string) => string;
  subscriptionOpened: (toolId: string) => string;
  subscriptionClosed: (toolId: string) => string;

  // Verify primitive
  verifyInProgress: string;
  verifySucceeded: string;
  verifyFailed: string;

  // Location resolver
  resolveLocationPending: string;
  resolveLocationAmbiguous: string;

  // Shutdown / footer
  pressCtrlCToExit: string;
  shuttingDown: string;
}
