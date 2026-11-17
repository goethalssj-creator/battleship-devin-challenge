# Detailed Bug Log: Atlantis: War for the Lost Kingdom

This log lists every genuine software defect found and fixed during development. It covers the original Battleship game and its naval and Atlantis redesigns. Each entry gives the symptom, root cause, fix and verification. Unless noted otherwise, each verification is an automated Playwright check in `tests/test_game.py` that failed before the fix and passes after it.

Not included: features and design changes the user requested (for example the victory and defeat screens, new artwork, sounds and names), and reports that turned out not to be defects (for example horizontal placement, which always worked through the Rotate button and R key).

Run the tests with `python3 serve.py`, then `python3 tests/test_game.py`. Final result: 142/142 checks pass.

## Gameplay and logic

### 1. Previous game's AI turn fired into a new game
- **Symptom:** firing a shot, then clicking New game → Random placement → Start battle within 0.6 s let the old game's pending AI move land on the new board.
- **Root cause:** the AI move was scheduled with `setTimeout`. Its only guard was `phase === "battle"`, which is true again once the new game starts.
- **Fix:** all delayed actions go through `later()`, which records each timer. `reset()` cancels them all and increments `gameId`, and a callback runs only if `gameId` is unchanged.
- **Verified:** "stale AI turn does not fire into new game" recorded 1 player-board shot before the fix and 0 after.

### 2. Player's shot result was overwritten
- **Symptom:** the message line showed only the AI's result. The player's own result was replaced 0.6 s after each shot.
- **Root cause:** each message replaced the whole message line.
- **Fix:** `log()` has an append mode for the AI's reply, so both results stay visible until the next shot, including the final message on a loss.
- **Verified:** "log shows player's own shot result after AI moves".

### 3. Holding R flipped the orientation repeatedly
- **Symptom:** holding R flipped the orientation several times and left it random. Ctrl+R / Cmd+R (reload) also flipped it.
- **Root cause:** the keydown handler responded to auto-repeat events and ignored modifier keys.
- **Fix:** the handler ignores `e.repeat` and Ctrl/Cmd/Alt combinations.
- **Verified:** "holding R toggles only once".

## Layout and display

### 4. Board cut off on small phones
- **Symptom:** at 320 px screen width, 40 cells of the fixed-width 382 px board were off-screen and couldn't be tapped.
- **Root cause:** the cell size was fixed at 34 px.
- **Fix:** `--cell: min(34px, calc((100vw - 74px) / 10))`.
- **Verified:** "all cells fully visible" at 320, 375 and 414 px. At 320 px, 40 cells were cut off before the fix and none after.

### 5. "Destroyed" banner showed through the end screen
- **Symptom:** the banner from the final shot was visible behind the victory/defeat card.
- **Root cause:** the banner fades out over 1.8 s, but the end screen opens 1.7 s after the last shot.
- **Fix:** `showEndScreen()` cancels the banner animation and hides it first.
- **Verified:** "ship-destroyed banner cleared from end screen" checks that the banner is fully transparent when the card appears.

### 6. Placement instruction repeated itself
- **Symptom:** the status line gave the same placement instruction twice in one message.
- **Root cause:** a new sentence was added to the status text without removing the old one.
- **Fix:** the status is a single sentence naming the piece, its length and its orientation.
- **Verified:** "placement instruction shown once, not duplicated".

### 7. Mute control was icon-only on phones
- **Symptom:** on screens 520 px wide or less, the mute button hid its SOUND ON / MUTED label. That fell short of the requirement for a clearly visible mute control.
- **Root cause:** the label was hidden on mobile to avoid overlapping the title.
- **Fix:** the label stays visible. On narrow screens the header moves below the button instead.
- **Verified:** "mute control fully visible on phone, with text label" and "mute control does not overlap title on phone" at 375×700.

### 8. Mute button covered the status message on phones
- **Symptom:** after scrolling to the enemy board on a 375 px phone, the end of every status message was hidden under the mute button.
- **Root cause:** the sticky status bar (`top: 0`) and the fixed mute button (`top: 10px`) shared the top of the screen.
- **Fix:** on narrow screens the status bar sticks 54 px from the top, below the button.
- **Verified:** "mute control does not cover the sticky status text while scrolled (phone)" at 375×700.

### 9. Long names stretched the board panels
- **Symptom:** each board panel was about 35 px wider than its grid, leaving an empty strip.
- **Root cause:** the panel sized itself to fit the one-line list of long piece names under the grid.
- **Fix:** the list has `contain: inline-size` and wraps within the grid's width.
- **Verified:** panel width now equals grid width plus padding on both boards. The all-cells-visible checks still pass at 320–1280 px.

### 10. Background art showed through disabled buttons
- **Symptom:** during battle, a tall building from the background showed through the dimmed Rotate button and made its label hard to read.
- **Root cause:** disabled controls used `opacity: .38`, which also made their backgrounds see-through.
- **Fix:** disabled controls keep a solid background and are dimmed by greying their text and border instead.
- **Verified:** "disabled buttons stay opaque so the scene can't show through their labels" confirms all four disabled controls have opacity 1 during battle (0.38 before the fix).

### 11. Subtitle unreadable over the painted backdrop
- **Symptom:** the subtitle and story line sat on the brightest light rays of the new backdrop and were barely legible.
- **Root cause:** the header text had no backing or shadow, and the new painting is brightest at the top.
- **Fix:** a soft dark glow behind the header and a strong text shadow on the subtitle.
- **Verified:** desktop and phone screenshots. This was a visual check; the header layout checks still pass.

## Performance

### 12. Animated background halved the frame rate
- **Symptom:** 15–18 fps during play, with choppy animations and slow clicks.
- **Root cause:** a full-screen animated light layer with `mix-blend-mode: screen` forced the whole page to be redrawn and blended every frame. Switching it off restored about 47 fps.
- **Fix:** removed the layer. Light shafts, and later a single painted backdrop image, give the same look at a fraction of the cost.
- **Verified:** "animations keep a smooth frame rate (>= 30 fps)" measured 18 fps before the fix. It passes after, at about 45–60 fps.
