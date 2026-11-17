# Battleship / Atlantis: War for the Lost Kingdom – Bug Log

Test suite: `tests/test_game.py` (Playwright, 142 checks). It covers ship placement, random fleets (500 generated), hit/miss detection, sinking, AI turns, AI behaviour over 300 simulated games, win and loss, restarting, small screens, and the cinematic effects, audio and end screens, and (for the Atlantis version) the kingdom buildings, underwater scene and frame rate. Most tests run with `?fast` (same code, shorter animations), and one full game runs at normal speed.
Run it with: `python3 serve.py` in this folder (a local server with browser caching turned off), then `python3 tests/test_game.py`. To make the single-file version, run `python3 build_standalone.py`.

Result: 14 issues found and fixed (5 in the original game, 3 in the naval redesign, 6 in the Atlantis redesigns). All 142 checks now pass. Screenshots are in `screenshots/`.

## 1. Old AI turn fires into a new game
- **Symptom:** If you fire a shot and then click **New game** → **Random placement** → **Start battle** within 0.6 s, the old game's waiting AI move fires on the new board. The AI gets a free first shot.
- **Cause:** The AI move was scheduled with `setTimeout`. Its only safeguard was `phase === "battle"`, and that is true again once the new game starts.
- **Fix:** `reset()` now cancels the pending timer (`clearTimeout(aiTimer)`) and increments `gameId`. The timer callback only runs if `gameId` hasn't changed.
- **Verified:** The test "stale AI turn does not fire into new game" failed before the fix (player shots = 1) and passes after it (0 shots, still the player's turn).

## 2. Your own shot result disappears
- **Symptom:** The message line under the boards only showed the AI's shot ("Enemy fires at E6: miss."). Your result ("You fire at …: HIT!") was replaced 0.6 s later, before you could read it.
- **Fix:** `log()` now has an append mode. The AI's message is added after yours, so both show until your next shot. This includes the final message when you lose.
- **Verified:** The test "log shows player's own shot result after AI moves" failed before the fix and passes after it.

## 3. Board cut off on small phones
- **Symptom:** Each board was a fixed 382 px wide. At 320 px screen width, 40 cells sat partly off-screen and you couldn't tap them.
- **Fix:** The cell size now scales with the screen: `--cell: min(34px, calc((100vw - 74px) / 10))`.
- **Verified:** The new test "all cells fully visible" checks widths of 320, 375 and 414 px. The old layout had 40 off-screen cells at 320 px; the fixed layout has 0 at every width. The 375 px screenshot was also checked by eye.

## 4. Horizontal placement seemed impossible ("I can only place ships vertically")
- **Reported:** ships could only be placed vertically.
- **Investigation:** the placement code itself handles horizontal ships correctly. Placing a ship horizontally by mouse click, by touch tap on a 375 px phone, and with the R key all worked. Random fleets come out about 51% horizontal. I could not reproduce a case where the code refuses a valid horizontal spot.
- **Root cause:** four problems in the controls made horizontal placement look broken:
  1. **Confusing button label.** The button said "Rotate (R): Horizontal", which shows the *current* orientation but reads like an action ("rotate to horizontal"). Players who wanted horizontal clicked it and got vertical. After that it read "Vertical", so they never clicked it again.
  2. **Edge clicks did nothing.** Ships extend right (horizontal) or down (vertical) from the cell you click. Clicking a horizontal ship within 4 columns of the right edge did nothing and gave no message.
  3. **Holding R flipped repeatedly.** Holding the key down fired repeated key events, so the orientation flipped several times and landed randomly. Ctrl+R / Cmd+R (reload) also flipped it.
  4. **No feedback on phones.** Touch screens have no hover preview, and a rejected placement gave no message, so there was no way to see which orientation was active.
- **Fix** (in `index.html`):
  - The button now reads "Rotate ship (R) · now: Horizontal/Vertical", and the status line names the orientation ("Place your Cruiser (3 cells, vertical). Press R or Rotate to switch.").
  - New `shipCells()`: a ship clicked near the right or bottom edge is shifted back onto the board instead of being silently rejected. The hover preview uses the same logic.
  - The R key handler ignores auto-repeat (`e.repeat`) and Ctrl/Cmd/Alt combinations.
  - Overlapping placements now show "That overlaps another ship…".
- **Verified:** new tests "all 5 ships placeable horizontally" and "all 5 ships placeable vertically" place a full fleet in each orientation. Other new tests cover the right-edge shift (a carrier clicked in column 10 lands in columns 6–10), the bottom-edge shift for vertical ships, holding R toggling only once, and touch taps in both orientations. `screenshots/placement_both_orientations.png` shows both orientations on one board.

## 5. Winning showed no victory screen
- **Reported:** after sinking every AI ship, there was no victory message or end screen.
- **Investigation:** win detection itself worked. `allSunk()` ran after every shot, the phase changed to "over", and further shots were blocked. The only feedback was the one-line status text at the top of the page changing to "Victory! …".
- **Root cause:** that feedback was too easy to miss. On a phone, the enemy board sits below the player board, so you're scrolled down when you take the winning shot. The status line was 292 px above the top of the screen (measured at 375×700), so you saw nothing at all. On desktop it was a small, unhighlighted text change. The AI winning had the same problem.
- **Fix** (in `index.html`):
  - `endGame()` now calls `showEndScreen()`, which shows a fixed full-screen overlay.
  - **Win:** a gold "VICTORY!" card with falling confetti, both sides' stats (shots, hits, accuracy), and **Play again** and **View board** buttons.
  - **AI win:** a red "DEFEAT" card ("The AI sank your entire fleet. The AI wins this battle.") with the same buttons.
  - The overlay covers the boards, so the game can't receive more moves. Even after **View board** closes it, the existing `phase === "over"` check still rejects shots, and `endGame()` also cancels any pending AI timer.
  - **Play again** and **New game** both reset the game and hide the overlay.
- **Verified:**
  - Before the fix, a 375 px browser that won the game had the only victory text off-screen (y = -292 px).
  - After the fix, tests confirm:
    - the victory screen and confetti appear, with 17 hits in the stats;
    - the screen covers the board;
    - shots are blocked both with the overlay up and after **View board**;
    - the AI takes no further turn;
    - **Play again** and **New game** reset the game;
    - the DEFEAT screen appears without confetti and shots are blocked;
    - on a 375×700 phone scrolled to the enemy board, the victory card is fully on-screen.
  - Screenshots: `victory_desktop.png`, `victory_phone.png`, `defeat_desktop.png`.

## Cinematic redesign: bugs found during re-testing

The redesign added a command-center look, radar and sonar sweeps, target lock, missile, explosion, splash and sinking animations, synthesized music and sound effects, a mute button, and MISSION ACCOMPLISHED / MISSION FAILED screens. The rules, placement, AI and win/loss code were copied over unchanged. The automated test suite was rewritten for the new attack timing and extended from 71 to 104 checks. Three real bugs in the new interface were found and fixed. No bugs were found in the rules, placement, AI or win/loss logic.

### 6. Placement instruction repeated itself
- **Issue:** during placement, the status line read "Deploy your Carrier (5 cells, horizontal). Place your Carrier on your grid; press R or Rotate to switch." The same instruction appeared twice.
- **Root cause:** when the new status text was written, a new opening sentence was added without removing the old one.
- **Fix:** the status text is now one sentence: "Place your Carrier (5 cells, horizontal) on your grid. Press R or Rotate to switch."
- **Verified:** the new check "placement instruction shown once, not duplicated" confirms the ship name appears once. The existing placement and orientation checks still pass.

### 7. "SHIP DESTROYED" banner showed through the end screen
- **Issue:** the winning shot sinks a ship, so the "ENEMY … DESTROYED" banner (or "… LOST" when you lose) was still visible behind the MISSION ACCOMPLISHED / MISSION FAILED card. This was found in the end-screen screenshots.
- **Root cause:** the banner fades out over about 1.8 seconds, but the end screen opens 1.7 seconds after the last shot. Both were on screen at the same moment.
- **Fix:** `showEndScreen()` now cancels the banner animation and hides it before showing the end card.
- **Verified:** the new check "ship-destroyed banner cleared from end screen" confirms the banner is fully transparent when the victory card appears. The new screenshots `cine_victory_desktop.png` and `cine_defeat_desktop.png` show a clean card.

### 8. Mute control was icon-only on phones
- **Issue:** on screens 520 px wide or narrower, the mute button hid its "SOUND ON / MUTED" label and showed only a small speaker icon. That falls short of the requirement for a clearly visible mute/unmute control.
- **Root cause:** the mobile layout hid the label so that the button wouldn't overlap the title.
- **Fix:** the label now stays visible on phones. To avoid the overlap, the header moves below the button on narrow screens instead.
- **Verified:** at 375×700, new checks confirm the button and its label are fully on-screen and don't overlap the header. Screenshot: `cine_phone_battle.png`.

### Redesign checks that passed (no bug)
- **Rules unchanged:** placement in both orientations (mouse, touch, R key, edge shifting), random fleets, hits, misses, sinking, Easy and Hard AI (Hard still averages about 45 shots), win, loss and restart all pass as before.
- **Attack flow:** after you fire, a target lock appears and a missile flies to the target. A hit shows an explosion and a screen shake, a miss shows a water splash, and a sinking ship plays a sinking animation with a "DESTROYED" banner. While the missile is in flight, clicking another cell does nothing.
- **Timing:** pressing **New game** while your missile is in flight, or while the AI is aiming, doesn't let the old shot land in the new game.
- **Boards stay usable:** the radar, sonar and effect layers don't block clicks on either grid. The row/column targeting crosshair works.
- **Audio:** no sound plays before your first click or key press, and music starts after it. The mute button and M key both work, muting silences everything, and the setting is remembered after a reload. Every sound effect plays without errors. All music and sounds are generated in the browser; no recordings, film footage, artwork or logos are used.
- **End screens:** MISSION ACCOMPLISHED has fireworks and MISSION FAILED does not. Both show stats, **Play again** and **View board**. No shots are accepted from the moment the game ends, before the card appears, or after **View board**.
- **Full speed:** one complete game at normal animation speed reached MISSION ACCOMPLISHED, with the AI taking exactly one turn per player shot.
- **Responsive:** every cell is fully on-screen at 320, 375, 414, 768 and 1280 px widths. On a phone, the end card fits on the screen.
- **Errors:** no JavaScript errors in any run.

## Atlantis: War for the Lost Kingdom redesign

### 9. Mute button covers the status message on phones
- **Symptom:** on a 375 px wide phone, once you scroll down to the enemy board, the sticky status bar slides to the top of the screen, under the fixed SOUND ON button. The end of every message ("…The Abyssal Empire takes aim") was hidden.
- **Root cause:** both elements sit at the top of the screen. The status bar is `position: sticky; top: 0` and the mute button is `position: fixed; top: 10px`, and nothing kept them apart.
- **Fix:** on narrow screens the status bar now sticks 54 px from the top, just below the mute button.
- **Verified:** a new check at 375×700 scrolls to the enemy board and compares the two boxes. It failed before the fix (they overlapped) and passes after. Screenshot: `kingdoms_phone_battle.png`.

### 10. Long target names stretched the board panels (creature version)
- **Symptom:** after the ships became creatures, both board panels were about 35 px wider than their grids, leaving an empty strip on the right of each board.
- **Root cause:** the fleet list under each board shows names like "Armored Sea Serpent". The panel sized itself to fit that whole line of names instead of fitting the grid.
- **Fix:** the fleet list no longer affects the panel width (`contain: inline-size`). It wraps inside the width set by the grid.
- **Verified:** panel width minus grid width is now just the panel padding on both boards (424 px vs 398 px at 1280 px wide). Every-cell-visible checks still pass at 320–1280 px.

### 11. Background effect cut the frame rate in half
- **Symptom:** the new frame-rate check measured 15–18 frames per second during play. Animations looked choppy and clicks felt slow.
- **Root cause:** a full-screen animated light layer used `mix-blend-mode: screen`, so the browser had to redraw and blend the whole screen on every frame. Turning it off brought the rate back to about 47 fps. The creature sprites and other effects made no measurable difference.
- **Fix:** the light layer was removed. The light shafts give the same look at much lower cost.
- **Verified:** "animations keep a smooth frame rate (>= 30 fps)" failed before the fix (18 fps) and passes after (about 45 fps on this machine).

### 12. Background buildings showed through disabled buttons
- **Symptom:** in the kingdoms version, once the battle started, a golden dome from the background city showed through the "Rotate building" label and made it hard to read.
- **Root cause:** buttons that can't be used during battle (Rotate, Random placement, Start battle, AI difficulty) were dimmed with `opacity: .38`. That made the whole button see-through, including its background. Earlier backgrounds were too low to reach the buttons, but the new city's tall towers do.
- **Fix:** disabled buttons now keep a solid background and are dimmed by greying their text and border instead.
- **Verified:** a new check starts a battle and confirms all four disabled controls have opacity 1. It measured 0.38 before the fix and passes after. Screenshot: `kingdoms_bolt.png`.

### Kingdoms version: the creatures become castles, temples and fortresses
- **Targets:** Atlantis has a Poseidon's Palace (5), Temple of Triton (4), Royal Citadel (3), Golden Temple (3) and Atlantis Watchtower (2). The Abyssal Empire has a Hades' Palace (5), Temple of Nyx (4), Dark Citadel (3), Shadow Temple (3) and Abyss Watchtower (2). Lengths and rules are unchanged.
- **Art:** each building has a wide version for horizontal placement and a tall tower version for vertical placement. All 20 drawings are different (checked), and the art never blocks clicks.
- **Hidden enemies:** enemy buildings stay hidden until destroyed. Then they're revealed and crumble, with falling rubble and a whirlpool. Damaged buildings of yours flash and lose colour.
- **Background:** a golden Atlantis on the left faces a dark Abyssal kingdom on the right, across a glowing chasm. Victory lights Atlantis gold and dims the Abyssal windows. Defeat darkens Atlantis and makes the Abyssal lights blaze.

### 13. Subtitle unreadable over the painted backdrop
- **Symptom:** after the painted background was added, "WAR FOR THE LOST KINGDOM" and the story line under the title sat on top of the brightest light rays and were barely readable.
- **Root cause:** the old backgrounds were dark at the top of the screen. The new painting is brightest there, where sunlight enters the water, and the header text had no backing or shadow.
- **Fix:** the header now has a soft dark glow behind it, and the subtitle and story text have a strong text shadow.
- **Verified:** checked in desktop and phone screenshots (`kingdoms_placement.png`, `kingdoms_phone_top.png`). The layout checks for the header and mute button still pass.

### 14. Painted-art update didn't show up for the user
- **Symptom:** the user saw the new art in the screenshots, but their copy of the game still looked like the old version.
- **Root cause (likely; their browser couldn't be inspected):** there were two ways this could happen. (1) The preview server (`python3 -m http.server`) sends no cache headers, so a browser can keep showing an old cached `index.html`. (2) The game was no longer one file: `index.html` loads its images from `assets/`. The attached `index.html` opened on its own can't find them, so no images appear.
- **Fix:** (1) the preview now runs on `serve.py`, which tells the browser never to cache, so a reload always gets the latest version. (2) `build_standalone.py` creates `atlantis_standalone.html`, a single file with every image built in, so it works anywhere with no folder.
- **Verified:** the server's response now includes `Cache-Control: no-store`. The single-file version opened directly from disk (`file://`) shows the painted backdrop and buildings with no errors. All 133 checks pass against the new server.

### Painted-art version: checks that passed (no bug)
- **Assets:** the backdrop and all 20 building sprites (a wide and a tall version of each of the 10 buildings) are original images made for this game and stored in `assets/`. A check confirms every one loads.
- **Grid stays clear:** sprites never block clicks. Hit and miss markers always draw on top of buildings, and each building's grid cells keep their outline.
- **Collapse:** a destroyed building splits into pieces that crumble into a pile of ruins inside its own cells, with rubble, dust, a whirlpool and a flash of light. A check confirms the pieces are created and animate.
- **Frame rate:** about 55–60 fps in isolation with the painted backdrop. It replaces the large vector scene, which had cut the rate to about 22 fps.
- (Test-script fix: the "hit damages your building" check assumed the AI had not already hit that building. It now compares against the hit count before the shot. This was in the test, not the game.)

### Destroyed-fortress markers and new names (no bug)
- **Destroyed fortresses stay marked:** on the final hit, the whole fortress flashes with light. Its squares then stay as dark cracked stone with ember markers, the collapsed ruins stay in place, and a red outline surrounds the whole fortress. New checks confirm the flash, the outline, the cracked squares, and that the marking is still there on later turns.
- **New names:** Atlantis has the Poseidon's Palace (5), Temple of Triton (4), Royal Citadel (3), Golden Temple (3) and Atlantis Watchtower (2). The Abyssal Empire has the Hades' Palace (5), Temple of Nyx (4), Dark Citadel (3), Shadow Temple (3) and Abyss Watchtower (2). They appear in the fleet lists, status messages, battle log and banners. Lengths and rules are unchanged.
- The "destroyed" banner now wraps onto two lines on narrow phones instead of running off the screen, because some names are longer.

### Ruins and attack sounds (no bug in the shipped game)
- **Ruins:** when a fortress is destroyed, it lights up, breaks apart, and is replaced by a painted ruin of the same building (20 ruin images, wide and tall versions). The ruin stays on its cracked, darkened squares with the red outline for the rest of the game. The old red hit dots are no longer drawn on destroyed squares.
- **Sounds:** a hit now plays a sharp lightning crack followed by deep rolling thunder. A miss plays a soft underwater splash with bubbles and no lightning or thunder. New checks confirm this for both your shots and the AI's, and that the sounds stay silent when muted.
- While making this change, one edit to the sound code broke the whole script (a missing comma). The first test run caught it (Start battle stayed disabled), and it was fixed before anything was shared.

### Atlantis checks that passed (no bug)
- **Rules unchanged:** both fleets keep lengths 5, 4, 3, 3, 2. Placement works in both orientations (mouse, touch, R key, edge shifting), and random fleets, hits, misses, sinking, Easy and Hard AI, win, loss and restart all pass as before.
- **Creatures:** each of the 10 creatures has its own illustration. Each sprite covers exactly its cells, and vertical creatures are turned to run down the column. A ghost creature previews the placement. Sprites never block clicks.
- **Hidden enemies:** enemy creatures don't show during battle, and a hit doesn't reveal them. A creature appears only when it is defeated, then sinks into the abyss with a whirlpool. The whole enemy fleet is shown after a loss.
- **Combat effects:** your attacks fire trident lightning with an energy orb, and the enemy fires dark energy blasts. Hits show a glowing burst and a swirl, and the hit creature flashes and fades. Misses show ripples, a spinning rune and bubbles. Effects clear themselves away within about 1.5 s.
- **End screens:** ATLANTIS IS YOURS lights the city gold. THE KINGDOM HAS FALLEN turns the city dark. Play Again resets everything, including the lighting.
- **Audio:** no sound before your first click or key press. The mute button and M key work, and the setting is remembered. All music and sound effects are generated in the browser.
- **Errors:** no JavaScript errors in any run.

## Final QA pass (no new bugs)
- **Automated suite:** 142/142 checks passed.
- **Extra edge-case checks** (run against both the server version and the standalone file): pressing R during battle does nothing, and rapid clicking during the AI's turn fires only one shot. New game during a collapse animation clears every ruin, effect and pending AI shot. After a win, all 5 enemy ruins show and no further shots are accepted. Sprites stay on their cells when the window is resized to phone width. Neither version had any JavaScript errors.
- **AI over 150 games each:** Easy and Hard never fire at the same cell twice and always finish the game. Hard needs far fewer shots than Easy.
- Two first-run failures turned out to be problems in the checks themselves, not the game. One check expected the wrong AI shot count. The other flagged the browser's automatic request for a site icon (`favicon.ico`), which the game doesn't use.

## Original version: checked and found working (no bug)
- **Placement:** out-of-bounds and overlapping placements are rejected, rotating works (button and R key), the hover preview shows good and bad spots, and **Start battle** stays disabled until all 5 ships are placed.
- **Shots:** hits and misses are detected correctly. Firing at a cell twice is ignored, and so is firing during the AI's turn or during placement.
- **Sinking:** a ship only sinks once every cell is hit, and it's crossed off the fleet list.
- **AI:** it never fires at the same cell twice and always finishes. Hard averages about 45 shots to sink your fleet.
- **Game end:** victory and defeat are detected. After the game ends no more shots are accepted, and the enemy fleet is revealed when you lose.
- **Restart:** works mid-game and after a game ends. It clears both boards and the message line, and places a new enemy fleet.
- **Errors:** no JavaScript errors in any run.

(A test-script problem in the loss test was fixed along the way. That was in the test, not the game.)
