# Bug Report: Atlantis: War for the Lost Kingdom

This report covers genuine software defects found and fixed during development. Each fix is covered by an automated Playwright check in `tests/test_game.py`. Requested features, design changes and user misunderstandings are not listed. The full list of 12 fixed bugs is in [docs/BUG_LOG_DETAILED.md](docs/BUG_LOG_DETAILED.md).

## 1. Previous game's AI turn fired into a new game
- **Issue:** if a new game started within 0.6 s of a shot, the old game's pending AI move landed on the new board, giving the AI a free first shot.
- **Identified by:** an automated restart test that fires, then immediately starts a new game, found 1 enemy shot already on the fresh board.
- **Fix:** all game timers go through one scheduler. `reset()` cancels every pending timer and increments a game ID, and callbacks from an older game are ignored.

## 2. Player's shot result was overwritten
- **Issue:** the AI's result replaced the player's message ("You fire at D5: hit!") 0.6 s after each shot, before it could be read.
- **Identified by:** a test reading the message line after the AI's reply.
- **Fix:** the AI's result is now added after the player's, and both stay visible until the next shot.

## 3. Board cut off on small phones
- **Issue:** at 320 px screen width, 40 cells of the fixed-width 382 px board were off-screen and couldn't be tapped.
- **Identified by:** an automated check that every cell is fully visible at 320, 375 and 414 px widths.
- **Fix:** the cell size now scales with the screen width (`min(34px, (100vw - 74px) / 10)`).

## 4. Holding R flipped the orientation repeatedly
- **Issue:** holding the R key sent repeated key events, so the orientation flipped several times and ended up random. Ctrl+R / Cmd+R (browser reload) also flipped it.
- **Identified by:** keyboard tests during placement testing.
- **Fix:** the key handler ignores auto-repeat events and Ctrl/Cmd/Alt combinations, so each press rotates exactly once.

## 5. "Destroyed" banner showed through the end screen
- **Issue:** the winning or losing shot always destroys a target, and its banner was still visible behind the victory/defeat card.
- **Identified by:** reviewing end-screen screenshots. The banner's 1.8 s fade outlasted the 1.7 s delay before the end screen.
- **Fix:** the end screen now cancels and hides the banner before it appears.

## 6. Animated background halved the frame rate
- **Issue:** the game ran at 15–18 fps, making animations choppy and clicks feel slow.
- **Identified by:** an automated frame-rate check (minimum 30 fps), then switching layers off one at a time. A full-screen animated light layer was blended over the whole page on every frame.
- **Fix:** removed that layer. The same look now comes from cheaper light shafts and a painted backdrop image, and the game runs at about 45–60 fps.

## Final QA summary
- **Automated suite:** `tests/test_game.py` (Playwright) passes **142/142 checks**. It covers placement and rotation, random fleets, alternating turns, Easy and Hard AI, hit/miss detection, fortress destruction, victory and defeat screens, sound effects and mute, restarting, phone layouts, and frame rate.
- **Additional edge-case checks:** **19/19 passed**, on both the served game and the standalone file:
  - rapid clicks during the AI's turn and R presses mid-battle are ignored;
  - restarting during an animation leaves nothing behind;
  - no shots are accepted after the game ends;
  - pieces stay aligned when the window is resized;
  - no JavaScript errors;
  - over 150 games per level, both AIs never repeat a cell, and Hard clearly beats Easy.
- **Deployed game:** 23/23 checks on GitHub Pages at desktop and phone sizes. All 41 images load, audio and mute work, and both victory and defeat screens appear.
- **Result:** no known open bugs.
