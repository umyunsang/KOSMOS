Output specs/2773-rollback-debug-infra/vhs/loc-er-hadan-urlheader.gif
Output specs/2773-rollback-debug-infra/vhs/loc-er-hadan-urlheader.txt
Output specs/2773-rollback-debug-infra/vhs/loc-er-hadan-urlheader.ascii

Require sed

Set Shell "bash"
Set FontSize 16
Set Width 1400
Set Height 900
Set LetterSpacing 0
Set Framerate 4
Set PlaybackSpeed 2

Type "sed -n '1,52p' specs/2773-rollback-debug-infra/captures/p0-full-final-16-2026-05-07/LOC-ER-HADAN-001/snap-000-boot.txt" Enter
Sleep 1s
Screenshot specs/2773-rollback-debug-infra/vhs/loc-er-hadan-urlheader-01-boot.png

Type "clear" Enter
Sleep 500ms
Type "sed -n '1,70p' specs/2773-rollback-debug-infra/captures/p0-full-final-16-2026-05-07/LOC-ER-HADAN-001/snap-001-input-submitted.txt" Enter
Sleep 1s
Screenshot specs/2773-rollback-debug-infra/vhs/loc-er-hadan-urlheader-02-input.png

Type "clear" Enter
Sleep 500ms
Type "sed -n '1,90p' specs/2773-rollback-debug-infra/captures/p0-full-final-16-2026-05-07/LOC-ER-HADAN-001/snap-002-post-tool-flow.txt" Enter
Sleep 1s
Screenshot specs/2773-rollback-debug-infra/vhs/loc-er-hadan-urlheader-03-post-tool-flow.png

Type "clear" Enter
Sleep 500ms
Type "sed -n '1,100p' specs/2773-rollback-debug-infra/captures/p0-full-final-16-2026-05-07/LOC-ER-HADAN-001/snap-003-expanded-tool-detail.txt" Enter
Sleep 1s
Screenshot specs/2773-rollback-debug-infra/vhs/loc-er-hadan-urlheader-04-expanded-tool-detail.png
