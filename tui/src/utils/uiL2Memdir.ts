// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — atomic-rename memdir helpers for the two new
// USER-tier paths owned by this epic (memdir-paths.md):
//
// - ~/.kosmos/memdir/user/onboarding/state.json   (FR-002)
// - ~/.kosmos/memdir/user/preferences/a11y.json   (FR-005)
//
// Reuses the existing Spec 027 memdir base path resolver; never edits paths
// owned by Spec 027/035.
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { homedir } from 'node:os';

import {
  AccessibilityPreference,
  type AccessibilityPreferenceT,
  freshAccessibilityPreference,
} from '../schemas/ui-l2/a11y.js';
import {
  OnboardingState,
  type OnboardingStateT,
  freshOnboardingState,
} from '../schemas/ui-l2/onboarding.js';

const USER_TIER_ROOT = process.env['KOSMOS_MEMDIR_USER'] ??
  join(homedir(), '.kosmos', 'memdir', 'user');

export const ONBOARDING_STATE_PATH = join(USER_TIER_ROOT, 'onboarding', 'state.json');
export const A11Y_PREF_PATH = join(USER_TIER_ROOT, 'preferences', 'a11y.json');

async function atomicWriteJson(path: string, data: unknown): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  const tmp = `${path}.tmp.${process.pid}.${Date.now()}`;
  await writeFile(tmp, JSON.stringify(data, null, 2), 'utf8');
  await rename(tmp, path);
}

async function readJsonOr<T>(path: string, fallback: T): Promise<T> {
  try {
    const raw = await readFile(path, 'utf8');
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export async function loadOnboardingState(): Promise<OnboardingStateT> {
  const raw = await readJsonOr<unknown>(ONBOARDING_STATE_PATH, null);
  if (raw == null) return freshOnboardingState();
  const parsed = OnboardingState.safeParse(raw);
  return parsed.success ? parsed.data : freshOnboardingState();
}

export async function saveOnboardingState(state: OnboardingStateT): Promise<void> {
  const validated = OnboardingState.parse(state);
  await atomicWriteJson(ONBOARDING_STATE_PATH, validated);
}

export async function loadAccessibilityPreference(): Promise<AccessibilityPreferenceT> {
  const raw = await readJsonOr<unknown>(A11Y_PREF_PATH, null);
  if (raw == null) return freshAccessibilityPreference();
  const parsed = AccessibilityPreference.safeParse(raw);
  return parsed.success ? parsed.data : freshAccessibilityPreference();
}

export async function saveAccessibilityPreference(pref: AccessibilityPreferenceT): Promise<void> {
  const validated = AccessibilityPreference.parse({
    ...pref,
    updated_at: new Date().toISOString(),
  });
  await atomicWriteJson(A11Y_PREF_PATH, validated);
}
