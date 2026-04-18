import en from './en';
import ko from './ko';
import type { I18nBundle } from './keys';

export type { I18nBundle };

// TODO: Register KOSMOS_TUI_LOCALE in src/kosmos/config/env_registry.py in a follow-up task.
// It is intentionally omitted here to avoid scope creep (T024 only covers bilingual bundle authoring).
const LOCALE = process.env['KOSMOS_TUI_LOCALE'] ?? 'ko';

export const i18n: I18nBundle = LOCALE === 'en' ? en : ko;
