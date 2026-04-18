import type { I18nBundle } from './keys';

const ko: I18nBundle = {
  sessionStarting: 'KOSMOS \uc138\uc158\uc744 \uc2dc\uc791\ud569\ub2c8\ub2e4\u2026',
  sessionReady: '\uc900\ube44 \uc644\ub8cc',
  sessionEnded: '\uc138\uc158\uc774 \uc885\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4',
  commandNotFound: (name) => `\uc54c \uc218 \uc5c6\ub294 \uba85\ub839: /${name}`,
  commandHelp: '\uc0ac\uc6a9 \uac00\ub2a5\ud55c \uba85\ub839:',
  permissionPromptTitle: '\uad8c\ud55c\uc774 \ud544\uc694\ud569\ub2c8\ub2e4',
  permissionPromptBody: (toolName) =>
    `\ub3c4\uad6c "${toolName}"\uc758 \uc2e4\ud589\uc744 \ud5c8\uc6a9\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?`,
  permissionApproved: '\ud5c8\uc6a9',
  permissionDenied: '\uac70\ubd80',
  toolCallFailed: (toolId, reason) => `\ub3c4\uad6c ${toolId} \uc2e4\ud328: ${reason}`,
  workerCrashed: (reason) => `\uc6cc\ucee4\uac00 \ucda9\ub3cc\ud588\uc2b5\ub2c8\ub2e4: ${reason}`,
  ipcDecodeError: 'IPC \ud504\ub808\uc784 \ub514\ucf54\ub529\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4',
  toolRunning: (toolId) => `${toolId} \uc2e4\ud589 \uc911\u2026`,
  toolSucceeded: (toolId) => `${toolId} \uc131\uacf5`,
  toolFailed: (toolId) => `${toolId} \uc2e4\ud328`,
  subscriptionOpened: (toolId) => `${toolId} \uad6c\ub3c5 \uc2dc\uc791`,
  subscriptionClosed: (toolId) => `${toolId} \uad6c\ub3c5 \ud574\uc81c`,
  verifyInProgress: '\uac80\uc99d \uc911\u2026',
  verifySucceeded: '\uac80\uc99d \uc131\uacf5',
  verifyFailed: '\uac80\uc99d \uc2e4\ud328',
  resolveLocationPending: '\uc704\uce58\ub97c \ud655\uc778\ud558\uace0 \uc788\uc2b5\ub2c8\ub2e4\u2026',
  resolveLocationAmbiguous:
    '\uc5ec\ub7ec \uc77c\uce58 \ud56d\ubaa9 \u2014 \uad6c\ubd84\uc774 \ud544\uc694\ud569\ub2c8\ub2e4',
  pressCtrlCToExit: 'Ctrl-C\ub97c \ub208\ub7ec \uc885\ub8cc',
  shuttingDown: '\uc885\ub8cc \uc911\u2026',
};

export default ko;
