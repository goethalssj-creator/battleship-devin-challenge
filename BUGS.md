# Bug Report: Atlantis: War for the Lost Kingdom

These are the six most significant bugs found and fixed during development. Each fix was confirmed by an automated Playwright check that failed before the fix and passes after it. The full development log is in [docs/BUG_LOG_DETAILED.md](docs/BUG_LOG_DETAILED.md).

## 1. Old AI turn fired into a new game
- **Issue:** if a new game was started within 0.6 s of a shot, the previous game's pending AI move landed on the new board, giving the AI a free first shot.
- **How found:** an automated restart test that fires and then immediately starts a new game recorded 1 enemy shot on the fresh board.
- **Fix:** all game timers go through one scheduler. `reset()` cancels every pending timer and increments a `gameId`, and timer callbacks from an older game are ignored.

## 2. Horizontal placement appeared impossible
- **Issue:** a playtester reported they could only place pieces vertically.
- **How found:** investigation showed the placement logic supported both orientations, so the problem was in the controls. The rotate button showed the *current* orientation but read like an action. Clicks near the right edge silently failed, holding R flipped the orientation repeatedly, and phones had no orientation preview.
- **Fix:** a clear "Rotate (R) · now: Horizontal/Vertical" label and status text. Pieces clicked near an edge shift onto the board, R ignores key repeat, overlaps show a message, and touch screens get a preview. Tests place a full fleet in each orientation by mouse, touch and keyboard.

## 3. Winning showed no victory screen
- **Issue:** after sinking every enemy target, nothing obvious happened.
- **How found:** win detection worked, but the only feedback was a status line. On a phone scrolled to the enemy board, that line was 292 px off-screen.
- **Fix:** full-screen victory (ATLANTIS IS YOURS) and defeat (THE KINGDOM HAS FALLEN) screens with stats, Play Again and View Board. Moves are blocked after the game ends, including after closing the screen.

## 4. Board cut off on small phones
- **Issue:** at 320 px width, 40 cells of a fixed 382 px board were off-screen and couldn't be tapped.
- **How found:** an automated visibility check at 320, 375 and 414 px widths.
- **Fix:** the cell size scales with the viewport, so every cell is fully visible and tappable at all tested widths.

## 5. Animated background halved the frame rate
- **Issue:** the game dropped to 15–18 fps, making animations choppy and clicks feel slow.
- **How found:** an automated frame-rate check (minimum 30 fps), plus testing with layers switched off one at a time.
- **Fix:** removed a full-screen animated blend layer and later replaced the vector scene with one painted backdrop image. The game now runs at about 45–60 fps.

## 6. Updated artwork didn't appear for the user
- **Issue:** after the painted-art update, the user's copy still showed the old visuals.
- **How found:** the preview server sent no cache headers, so browsers kept an old page. The game also now loaded images from `assets/`, which a lone `index.html` couldn't find.
- **Fix:** a no-cache local server (`serve.py`) and a single-file build (`atlantis_standalone.html`) with all images embedded. Both were checked in a browser, including opening the file straight from disk.

## Final QA summary
- **Automated suite:** `tests/test_game.py` (Playwright) passes **142/142 checks**. It covers placement and rotation, random fleets, alternating turns, Easy and Hard AI, hit/miss detection, fortress destruction and ruins, victory and defeat screens, sound effects and mute, restarting, phone layouts, and frame rate.
- **Additional edge-case checks:** **19/19 passed**, on both the served version and the standalone file:
  - rapid clicks during the AI's turn and R presses mid-battle are ignored;
  - restarting during a collapse animation leaves nothing behind;
  - no shots are accepted after the game ends;
  - pieces stay aligned when the window is resized;
  - no JavaScript errors;
  - over 150 games per level, both AIs never repeat a cell and Hard clearly outperforms Easy.
- **Result:** no open bugs.
