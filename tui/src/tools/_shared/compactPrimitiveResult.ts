import React from 'react'
import { CtrlOToExpand } from '../../components/CtrlOToExpand.js'
import { MessageResponse } from '../../components/MessageResponse.js'
import { Box, Text } from '../../ink.js'

export const PRIMITIVE_RESULT_PREVIEW_MAX_ROWS = 3

export function isPrimitiveResultPreviewTruncated(
  rows: readonly React.ReactNode[],
): boolean {
  return rows.length > PRIMITIVE_RESULT_PREVIEW_MAX_ROWS
}

export function renderCompactPrimitiveResult(
  rows: readonly React.ReactNode[],
): React.ReactNode {
  const truncated = isPrimitiveResultPreviewTruncated(rows)
  const visibleRows = truncated
    ? rows.slice(0, PRIMITIVE_RESULT_PREVIEW_MAX_ROWS - 1)
    : rows

  return React.createElement(
    MessageResponse,
    null,
    React.createElement(
      Box,
      { flexDirection: 'column' },
      ...visibleRows,
      truncated
        ? React.createElement(
            Text,
            { key: 'primitive-result-more', dimColor: true },
            '... ',
            React.createElement(CtrlOToExpand),
          )
        : null,
    ),
  )
}
