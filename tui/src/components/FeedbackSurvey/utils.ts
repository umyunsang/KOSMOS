// [P0 reconstructed · Pass 3 · FeedbackSurvey utils]
// Reference: FeedbackSurveyView.tsx `inputToResponse` map +
//            SkillImprovementSurvey.tsx consumer (`handleSelect: (r:
//            FeedbackSurveyResponse) => void`).
//
// Survey responses map 4 digit keys (0-3) to a simple 4-value enum. The
// source of truth for the digit→label mapping lives in FeedbackSurveyView,
// which imports the type from this file.

/**
 * Possible user responses to a post-session feedback survey.
 * `dismissed` = the user hit ESC / declined to answer.
 */
export type FeedbackSurveyResponse = 'dismissed' | 'bad' | 'fine' | 'good'

/** All valid responses, in display order (bad → good). */
export const FEEDBACK_SURVEY_RESPONSES: readonly FeedbackSurveyResponse[] = [
  'dismissed',
  'bad',
  'fine',
  'good',
] as const

/** Type guard. */
export function isFeedbackSurveyResponse(
  value: unknown,
): value is FeedbackSurveyResponse {
  return (
    typeof value === 'string' &&
    (FEEDBACK_SURVEY_RESPONSES as readonly string[]).includes(value)
  )
}
