"""End-to-end tests for Atlantis: War for the Lost Kingdom (Battleship rules).
Requires the game served at BASE (default http://localhost:8080/) and Chrome CDP at localhost:29229.
Most tests load the page with ?fast (animations run at 15% duration, same code paths); t_full_speed_game plays at normal speed."""
import os, sys, traceback
from playwright.sync_api import sync_playwright

ROOT = os.environ.get("BASE", "http://localhost:8080/")
BASE = ROOT + "?fast"
results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))

def cell(pg, board, r, c):
    return pg.locator(f"#{board} .cell[data-r='{r}'][data-c='{c}']")

def classes(pg, board, r, c):
    return cell(pg, board, r, c).get_attribute("class")

def fresh(pg, url=None):
    pg.goto(url or BASE); pg.wait_for_function("typeof state !== 'undefined'")

def enemy_ships(pg):
    return pg.evaluate("state.enemy.ships.map(s=>({name:s.name,cells:s.cells}))")

def enemy_water(pg):
    return pg.evaluate("""(()=>{const o=[];for(let r=0;r<10;r++)for(let c=0;c<10;c++)if(!state.enemy.grid[r][c]&&!state.enemy.shots[r][c])o.push([r,c]);return o})()""")

def count_shots(pg, who):
    return pg.evaluate(f"state.{who}.shots.flat().filter(v=>v).length")

def wait_player_turn(pg, timeout=8000):
    pg.wait_for_function("state.phase!=='battle' || state.turn==='player'", timeout=timeout)

def shoot(pg, r, c, timeout=8000):
    """Click an enemy cell and wait until the missile lands (shot recorded)."""
    cell(pg, "enemy", r, c).click()
    pg.wait_for_function(f"state.enemy.shots[{r}][{c}] !== 0", timeout=timeout)

def start_random(pg):
    pg.click("#random"); pg.click("#start")

def sink_all(pg, timeout=8000):
    cells = [c for s in enemy_ships(pg) for c in s["cells"]]
    for i, c in enumerate(cells):
        wait_player_turn(pg, timeout); shoot(pg, *c, timeout=timeout)
    return cells

def wait_overlay(pg, timeout=8000):
    pg.wait_for_selector("#overlay.show", state="visible", timeout=timeout)

def t_placement(pg):
    fresh(pg)
    check("start disabled before placement", pg.is_disabled("#start"))
    check("default orientation is horizontal", pg.evaluate("state.horiz") is True and "now: Horizontal" in pg.inner_text("#rotate"))
    cell(pg, "player", 0, 0).click()                       # Poseidon's Palace A1-A5
    check("carrier placed horizontally", pg.evaluate("state.player.ships[0].cells") == [[0,i] for i in range(5)])
    cell(pg, "player", 0, 3).click()                       # overlap
    check("overlapping placement rejected", pg.evaluate("state.placeIdx") == 1)
    check("overlap shows feedback", "overlaps" in pg.inner_text("#status"))
    pg.click("#rotate")
    check("rotate button toggles vertical", pg.evaluate("state.horiz") is False and "now: Vertical" in pg.inner_text("#rotate"))
    check("status names orientation", "vertical" in pg.inner_text("#status"))
    cell(pg, "player", 2, 0).click()                       # Battleship C1-F1
    check("battleship placed vertically", pg.evaluate("state.player.ships[1].cells") == [[2+i,0] for i in range(4)])
    pg.keyboard.press("r")
    check("R key toggles horizontal", pg.evaluate("state.horiz") is True)
    cell(pg, "player", 9, 0).click(); cell(pg, "player", 9, 5).click(); cell(pg, "player", 5, 5).click()
    check("all 5 ships placed", pg.evaluate("state.placeIdx") == 5)
    check("17 ship cells rendered", pg.locator("#player .cell.ship").count() == 17)
    check("start enabled after placement", pg.is_enabled("#start"))
    cell(pg, "player", 7, 7).click()
    check("no 6th ship placed", pg.evaluate("state.player.ships.length") == 5)
    fresh(pg); cell(pg, "player", 4, 4).hover()
    check("hover preview shows 5 cells", pg.locator("#player .cell.preview").count() == 5)
    cell(pg, "player", 4, 4).click(); cell(pg, "player", 4, 2).hover()
    check("overlapping hover preview marked bad", pg.locator("#player .cell.preview.bad").count() == 4)

def t_orientation(pg):
    fresh(pg)                                              # all five ships horizontal, one per row
    for r in range(5): cell(pg, "player", r * 2, 0).click()
    ships = pg.evaluate("state.player.ships.map(s=>s.cells)")
    check("all 5 ships placeable horizontally", len(ships) == 5 and all(len({x[0] for x in sh}) == 1 for sh in ships))
    fresh(pg); pg.click("#rotate")                         # all five ships vertical, one per column
    for c in range(5): cell(pg, "player", 0, c * 2).click()
    ships = pg.evaluate("state.player.ships.map(s=>s.cells)")
    check("all 5 ships placeable vertically", len(ships) == 5 and all(len({x[1] for x in sh}) == 1 for sh in ships))
    fresh(pg); cell(pg, "player", 3, 9).click()            # horizontal carrier clicked at the right edge
    check("horizontal ship near right edge shifts onto board", pg.evaluate("state.player.ships[0]?.cells") == [[3, 5 + i] for i in range(5)])
    pg.click("#rotate"); cell(pg, "player", 9, 0).click()  # vertical battleship clicked at the bottom edge
    check("vertical ship near bottom edge shifts onto board", pg.evaluate("state.player.ships[1]?.cells") == [[6 + i, 0] for i in range(4)])
    fresh(pg); h0 = pg.evaluate("state.horiz")
    pg.keyboard.down("r"); pg.keyboard.down("r"); pg.keyboard.down("r"); pg.keyboard.up("r")   # held key = auto-repeat
    check("holding R toggles only once", pg.evaluate("state.horiz") == (not h0))

def t_touch_orientation(br):
    ctx = br.new_context(viewport={"width": 375, "height": 800}, has_touch=True, is_mobile=True); pg = ctx.new_page(); fresh(pg)
    pg.locator("#player .cell[data-r='0'][data-c='0']").tap()
    pg.locator("#rotate").tap()
    pg.locator("#player .cell[data-r='2'][data-c='0']").tap()
    sh = pg.evaluate("state.player.ships.map(s=>s.cells)")
    check("touch: horizontal and vertical placement both work", sh == [[[0,i] for i in range(5)], [[2+i,0] for i in range(4)]], str(sh))
    ctx.close()

def t_random_fleets(pg):
    fresh(pg)
    bad = pg.evaluate("""(()=>{let bad=0;for(let i=0;i<500;i++){const b=newBoard();randomFleet(b);
      const cells=b.ships.flatMap(s=>s.cells);const keys=new Set(cells.map(x=>x.join()));
      const lens=b.ships.map(s=>s.cells.length).join();
      const contiguous=b.ships.every(s=>s.cells.every(([r,c],k)=>k===0||(r===s.cells[0][0]&&c===s.cells[0][1]+k)||(c===s.cells[0][1]&&r===s.cells[0][0]+k)));
      if(cells.length!==17||keys.size!==17||lens!=='5,4,3,3,2'||!contiguous||cells.some(([r,c])=>r<0||r>9||c<0||c>9))bad++;}return bad})()""")
    check("500 random fleets valid (no overlap, in bounds, straight)", bad == 0, f"bad={bad}")
    fresh(pg); pg.click("#random")
    check("random placement fills fleet", pg.evaluate("state.placeIdx") == 5 and pg.locator("#player .cell.ship").count() == 17)

def t_ai_full_games(pg):
    fresh(pg)
    res = pg.evaluate("""(diff)=>{ $('difficulty').value=diff; const stats=[]; let dup=0, bad=0;
      for(let g=0; g<200; g++){ state.player=newBoard(); randomFleet(state.player); let shots=0; const seen=new Set();
        while(!allSunk(state.player) && shots<100){ const p=aiPick(); if(!p){bad++;break;}
          const k=p.join(); if(seen.has(k)) dup++; seen.add(k); fire(state.player,p[0],p[1]); shots++; }
        if(!allSunk(state.player)) bad++; stats.push(shots); }
      return {avg: stats.reduce((a,b)=>a+b)/stats.length, max: Math.max(...stats), dup, bad}; }""", "hard")
    check("hard AI never repeats a shot / always finishes", res["dup"] == 0 and res["bad"] == 0, str(res))
    check("hard AI average under 60 shots", res["avg"] < 60, str(res))
    res2 = pg.evaluate("""(diff)=>{ $('difficulty').value=diff; let dup=0, bad=0, tot=0;
      for(let g=0; g<100; g++){ state.player=newBoard(); randomFleet(state.player); let shots=0; const seen=new Set();
        while(!allSunk(state.player) && shots<100){ const p=aiPick(); const k=p.join(); if(seen.has(k)) dup++; seen.add(k); fire(state.player,p[0],p[1]); shots++; }
        if(!allSunk(state.player)) bad++; tot+=shots; }
      return {avg: tot/100, dup, bad}; }""", "easy")
    check("easy AI never repeats a shot / always finishes", res2["dup"] == 0 and res2["bad"] == 0, str(res2))

def t_mobile_layout(br):
    for w in (320, 375, 414):
        ctx = br.new_context(viewport={"width": w, "height": 800}); pg = ctx.new_page(); fresh(pg)
        off = pg.evaluate("[...document.querySelectorAll('.cell')].filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth||r.width<20}).length")
        check(f"all cells fully visible at {w}px width", off == 0, f"offscreen={off}")
        ctx.close()

def t_shots(pg):
    fresh(pg)
    s = enemy_ships(pg)[0]["cells"][0]
    cell(pg, "enemy", *s).click()
    check("enemy click ignored during placement", count_shots(pg, "enemy") == 0)
    start_random(pg)
    check("enemy ships hidden during battle", pg.locator("#enemy .cell.ship").count() == 0)
    cell(pg, "enemy", *s).click()
    check("turn passes to AI immediately after firing", pg.evaluate("state.turn") == "ai")
    check("target lock reticle shown on fired cell", "locked" in classes(pg, "enemy", *s))
    cell(pg, "enemy", *enemy_water(pg)[0]).click()
    pg.wait_for_function(f"state.enemy.shots[{s[0]}][{s[1]}] !== 0")
    check("hit detected", "hit" in classes(pg, "enemy", *s))
    check("second click during missile flight ignored", count_shots(pg, "enemy") == 1)
    wait_player_turn(pg)
    check("AI fires exactly one shot", count_shots(pg, "player") == 1)
    w = enemy_water(pg)[0]
    shoot(pg, *w)
    check("miss detected", "miss" in classes(pg, "enemy", *w) and "hit" not in classes(pg, "enemy", *w))
    wait_player_turn(pg)
    cell(pg, "enemy", *s).click()
    check("re-firing same cell ignored, keeps turn", pg.evaluate("state.turn") == "player" and count_shots(pg, "enemy") == 2)
    pb = pg.evaluate("(()=>{for(let r=0;r<10;r++)for(let c=0;c<10;c++)if(state.player.shots[r][c])return [r,c,state.player.shots[r][c]]})()")
    cls = classes(pg, "player", pb[0], pb[1])
    check("AI shot rendered on player board", ("miss" in cls) if pb[2] == 1 else ("hit" in cls))

def t_sinking(pg):
    fresh(pg); start_random(pg)
    d = [x for x in enemy_ships(pg) if x["name"] == "Abyss Watchtower"][0]["cells"]
    shoot(pg, *d[0]); wait_player_turn(pg)
    check("one hit does not sink", "sunk" not in classes(pg, "enemy", *d[0]))
    shoot(pg, *d[1])
    check("destroyer sunk after all cells hit", all("sunk" in classes(pg, "enemy", *c) for c in d))
    check("sunk ship revealed as wreck on enemy grid", all("ship" in classes(pg, "enemy", *c) for c in d))
    check("sinking animation applied", all("sinking" in classes(pg, "enemy", *c) for c in d))
    check("destroyed callout shown", pg.inner_text("#callout") == "ABYSS WATCHTOWER DESTROYED")
    check("sunk message shown", "destroyed their Abyss Watchtower" in pg.inner_text("#log"))
    check("fleet list crosses out Abyss Watchtower", pg.locator("#enemyFleet .dead").inner_text() == "Abyss Watchtower")
    wait_player_turn(pg)
    check("other enemy ships still hidden", pg.locator("#enemy .cell.ship").count() == 2)

def t_win(pg):
    fresh(pg); start_random(pg)
    cells = sink_all(pg)
    check("win detected", pg.evaluate("state.phase") == "over" and pg.evaluate("state.winner") == "player" and "Victory" in pg.inner_text("#status"))
    check("player's final shot message kept on win", "destroyed their" in pg.inner_text("#log"))
    w = enemy_water(pg)[0]; before = count_shots(pg, "enemy")
    cell(pg, "enemy", *w).click()
    check("no firing after win (before end screen appears)", count_shots(pg, "enemy") == before)
    wait_overlay(pg)
    check("ATLANTIS IS YOURS screen shown", pg.inner_text("#endTitle") == "ATLANTIS IS YOURS")
    check("ship-destroyed banner cleared from end screen", pg.evaluate("getComputedStyle(document.getElementById('callout')).opacity") == "0")
    check("city illuminated with golden light on victory", "city-lit" in pg.get_attribute("body", "class") and "sepia" in pg.evaluate("getComputedStyle(document.getElementById('endCity')).filter") and pg.evaluate("getComputedStyle(document.getElementById('sceneGlow')).opacity") != "0")
    check("golden halo rises over the city", pg.evaluate("getComputedStyle(document.getElementById('endHalo')).animationName") == "halo")
    check("victory screen celebrates (golden light motes)", pg.locator("#overlay .spark").count() > 0)
    check("victory screen shows stats", "17 hits" in pg.inner_text("#endStats"))
    check("play again button visible", pg.is_visible("#playAgain"))
    covered = pg.evaluate(f"(()=>{{const r=document.querySelector(\"#enemy .cell[data-r='{w[0]}'][data-c='{w[1]}']\").getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2).closest('#overlay')!==null}})()")
    check("end screen covers the boards", covered)
    cell(pg, "enemy", *w).click(force=True)
    check("no firing after game over", count_shots(pg, "enemy") == before)
    pg.click("#viewBoard")
    check("view board hides end screen", not pg.is_visible("#overlay"))
    cell(pg, "enemy", *w).click()
    check("no firing after game over (board view)", count_shots(pg, "enemy") == before)
    pg.wait_for_timeout(600)
    check("AI does not fire after player wins", count_shots(pg, "player") == len(cells) - 1)
    pg.click("#reset")
    check("new game after victory resets", pg.evaluate("state.phase") == "place" and count_shots(pg, "enemy") == 0)

def t_loss(pg):
    fresh(pg); start_random(pg)
    pg.evaluate("() => { window.__targets = state.player.ships.flatMap(s => s.cells); aiPick = () => window.__targets.shift(); }")
    for _ in range(17):
        if pg.evaluate("state.phase") != "battle": break
        shoot(pg, *enemy_water(pg)[0]); wait_player_turn(pg)
    check("loss detected", pg.evaluate("state.phase") == "over" and pg.evaluate("state.winner") == "ai" and "Defeat" in pg.inner_text("#status"))
    check("enemy fleet revealed on loss", pg.locator("#enemy .cell.ship").count() == 17)
    check("all player ships marked dead", pg.locator("#playerFleet .dead").count() == 5)
    wait_overlay(pg)
    check("THE KINGDOM HAS FALLEN screen shown for AI win", pg.inner_text("#endTitle") == "THE KINGDOM HAS FALLEN" and "AI wins" in pg.inner_text("#endMsg"))
    check("city goes dark on defeat", "city-dark" in pg.get_attribute("body", "class") and "brightness(0.3)" in pg.evaluate("getComputedStyle(document.getElementById('endCity')).filter")
          and "brightness" in pg.evaluate("getComputedStyle(document.getElementById('endCity')).filter"))
    check("no golden motes on defeat", pg.locator("#overlay .spark").count() == 0)
    before = count_shots(pg, "enemy"); cell(pg, "enemy", *enemy_water(pg)[0]).click(force=True)
    check("no firing after AI wins", count_shots(pg, "enemy") == before)
    pg.click("#playAgain")
    check("play again after defeat starts fresh game", not pg.is_visible("#overlay") and pg.evaluate("state.phase") == "place"
          and count_shots(pg, "player") == 0 and pg.locator("#player .cell.ship").count() == 0)

def t_restart(pg):
    fresh(pg); start_random(pg)
    shoot(pg, *enemy_water(pg)[0]); wait_player_turn(pg)
    pg.click("#reset")
    check("restart clears boards", count_shots(pg, "player") == 0 and count_shots(pg, "enemy") == 0
          and pg.locator("#player .cell.ship").count() == 0 and pg.locator("#enemy .cell.miss, #enemy .cell.hit").count() == 0)
    check("restart returns to placement phase", pg.evaluate("state.phase") == "place" and pg.is_enabled("#random") and pg.is_disabled("#start"))
    check("restart generates new enemy fleet", pg.evaluate("state.enemy.ships.length") == 5)
    check("restart clears log", pg.inner_text("#log") == "")
    start_random(pg)                                       # restart while our missile is in flight
    cell(pg, "enemy", *enemy_water(pg)[0]).click()
    pg.click("#reset"); start_random(pg); pg.wait_for_timeout(1500)
    check("in-flight missile does not land in new game", count_shots(pg, "enemy") == 0 and count_shots(pg, "player") == 0
          and pg.evaluate("state.turn") == "player", f"enemy={count_shots(pg,'enemy')} player={count_shots(pg,'player')}")
    shoot(pg, *enemy_water(pg)[0])                         # restart while the AI is aiming
    pg.wait_for_function("state.lock && state.lock[0]==='player'")
    pg.click("#reset"); start_random(pg); pg.wait_for_timeout(1500)
    check("stale AI turn does not fire into new game", count_shots(pg, "player") == 0 and pg.evaluate("state.turn") == "player",
          f"player shots={count_shots(pg,'player')}")
    fresh(pg); start_random(pg)                            # restart from the end screen
    pg.evaluate("state.enemy.ships.forEach(s=>s.cells.slice(1).forEach(([r,c])=>fire(state.enemy,r,c)))")
    for s in enemy_ships(pg):
        if pg.evaluate("state.phase") != "battle": break
        shoot(pg, *s["cells"][0]); wait_player_turn(pg)
    wait_overlay(pg); pg.click("#playAgain")
    check("restart after game over works", pg.evaluate("state.phase") == "place" and "Place your Poseidon's Palace" in pg.inner_text("#status"))
    st = pg.inner_text("#status")
    check("placement instruction shown once, not duplicated", st.count("Poseidon's Palace") == 1 and "Deploy" not in st, st)
    check("restart restores the city lighting", pg.get_attribute("body", "class") in (None, ""))
    check("restart clears leftover effects", pg.locator("#fx > *").count() == 0)

def t_effects(pg):
    fresh(pg, ROOT); start_random(pg)                      # normal speed so effects can be observed
    d = [x for x in enemy_ships(pg) if x["name"] == "Abyss Watchtower"][0]["cells"]
    cell(pg, "enemy", *d[0]).click(); pg.wait_for_timeout(450)
    check("trident lightning strikes toward target", pg.locator("#fx .lightning path.core").count() >= 1)
    check("trident energy blast animates toward target", pg.locator("#fx .bolt").count() == 1)
    pg.wait_for_function(f"state.enemy.shots[{d[0][0]}][{d[0][1]}] !== 0")
    check("glowing burst on hit", pg.locator("#fx .burst").count() >= 1 and pg.locator("#fx .glint").count() > 0)
    check("screen shake on hit", "shake" in pg.get_attribute(".panel.enemy", "class"))
    pg.wait_for_function("state.lock && state.lock[0]==='player'", timeout=5000)
    check("AI target lock shown on player grid", pg.locator("#player .cell.locked").count() == 1)
    wait_player_turn(pg)
    w = enemy_water(pg)[0]; cell(pg, "enemy", *w).click()
    pg.wait_for_function(f"state.enemy.shots[{w[0]}][{w[1]}] !== 0")
    check("shockwave and bubbles on miss", pg.locator("#fx .ring").count() >= 1 and pg.locator("#fx .bubble").count() > 0)
    for name in ["player", "enemy"]:
        r = pg.evaluate(f"(()=>{{const c=document.querySelector('#{name} .cell[data-r=\"4\"][data-c=\"4\"]').getBoundingClientRect();return document.elementFromPoint(c.x+c.width/2,c.y+c.height/2).classList.contains('cell')}})()")
        check(f"radar/sonar overlay does not block clicks on {name} grid", r)
    check("effect layers ignore pointer", pg.evaluate("['fx','flash','callout'].every(id=>getComputedStyle(document.getElementById(id)).pointerEvents==='none')"))
    pg.locator("#enemy .cell[data-r='5'][data-c='5']").hover()
    wait_player_turn(pg); pg.locator("#enemy .cell[data-r='5'][data-c='6']").hover()
    check("targeting crosshair highlights row/column", pg.locator("#enemy .cell.aimline").count() >= 10 and "F7" in pg.inner_text("#aimReadout"))

def t_structures(pg):
    fresh(pg)
    names = ["Poseidon's Palace","Temple of Triton","Royal Citadel","Golden Temple","Atlantis Watchtower"]
    foes = ["Hades' Palace","Temple of Nyx","Dark Citadel","Shadow Temple","Abyss Watchtower"]
    check("Atlantis kingdom roster (same lengths 5,4,3,3,2)", pg.evaluate("SHIPS") == [[n,l] for n,l in zip(names,[5,4,3,3,2])])
    check("Abyssal roster (same lengths 5,4,3,3,2)", [s["name"] for s in enemy_ships(pg)] == foes and [len(s["cells"]) for s in enemy_ships(pg)] == [5,4,3,3,2])
    cell(pg, "player", 2, 2).hover()
    check("ghost building previews placement", pg.locator("#player .structure.ghost").count() == 1)
    cell(pg, "player", 0, 0).click()
    pg.click("#rotate"); cell(pg, "player", 2, 0).click()
    check("horizontal building sprite placed", pg.locator("#player .structure.h:not(.ghost)").count() == 1 and pg.locator("#player .structure[data-name=\"Poseidon's Palace\"]").count() == 1)
    check("vertical building sprite placed", pg.locator("#player .structure.v:not(.ghost)").count() == 1 and pg.locator("#player .structure[data-name=\"Temple of Triton\"]").count() == 1)
    def span(names_cells, sel):
        bs = [cell(pg, "player", r, c).bounding_box() for r, c in names_cells]
        x0 = min(b["x"] for b in bs); y0 = min(b["y"] for b in bs); x1 = max(b["x"]+b["width"] for b in bs); y1 = max(b["y"]+b["height"] for b in bs)
        a = pg.locator(sel).bounding_box()
        return abs(a["x"]-x0) < 2 and abs(a["y"]-y0) < 2 and abs(a["x"]+a["width"]-x1) < 2 and abs(a["y"]+a["height"]-y1) < 2
    check("horizontal sprite covers exactly its 5 cells", span([(0,i) for i in range(5)], "#player .structure[data-name=\"Poseidon's Palace\"]"))
    check("vertical sprite covers exactly its 4 cells", span([(2+i,0) for i in range(4)], "#player .structure[data-name=\"Temple of Triton\"]"))
    art = pg.locator("#player .structure[data-name=\"Temple of Triton\"] .art").bounding_box()
    check("vertical building is drawn upright as a tall tower", art["height"] > art["width"] * 2.5, str(art))
    check("each building has its own painted sprite (both orientations), all load", pg.evaluate("new Set([...SHIPS,...FOES].flatMap(([n])=>[spriteURL(n,true),spriteURL(n,false)])).size") == 20 and pg.evaluate("Promise.all([...SHIPS,...FOES].flatMap(([n])=>[spriteURL(n,true),spriteURL(n,false)]).map(u=>new Promise(r=>{const i=new Image(); i.onload=()=>r(i.naturalWidth>100); i.onerror=()=>r(false); i.src=u;}))).then(a=>a.every(Boolean))") and pg.locator("#player .structure .art").count() >= 2)
    b = cell(pg, "player", 0, 2).bounding_box()
    check("building sprites never block clicks", pg.evaluate(f"document.elementFromPoint({b['x']+b['width']/2},{b['y']+b['height']/2}).classList.contains('cell')"))
    fresh(pg); start_random(pg)
    check("all 5 Atlantean buildings shown", pg.locator("#player .structure").count() == 5)
    check("enemy buildings hidden during battle", pg.locator("#enemy .structure").count() == 0)
    wt = [x for x in enemy_ships(pg) if x["name"] == "Abyss Watchtower"][0]["cells"]
    shoot(pg, *wt[0]); wait_player_turn(pg)
    check("hit alone does not reveal the enemy building", pg.locator("#enemy .structure").count() == 0)
    shoot(pg, *wt[1]); pg.wait_for_timeout(120)
    check("destroyed enemy building revealed and collapses tower by tower", pg.locator("#enemy .structure.gone[data-name='Abyss Watchtower']").count() == 1
          and pg.locator("#enemy .structure.gone .slice").count() >= 3 and pg.evaluate("document.querySelector('#enemy .structure.gone .slice').getAnimations().length") > 0)
    check("whirlpool and rubble on destruction", pg.locator("#fx .vortex.big").count() == 1 and pg.locator("#fx .rubble").count() > 0)
    check("whole building lights up on its final hit", pg.locator("#fx .footflash").count() == 1)
    pg.wait_for_timeout(1300)
    check("destroyed building keeps a red outline around all its squares", pg.evaluate("getComputedStyle(document.querySelector('#enemy .structure.gone'),'::after').borderTopColor") == "rgba(255, 86, 86, 0.85)")
    check("destroyed squares show cracked, darkened ruins", pg.evaluate("(()=>{const c=[...document.querySelectorAll('#enemy .cell.sunk')]; return c.length===2 && c.every(x=>getComputedStyle(x).backgroundImage.includes('svg'))})()"))
    wait_player_turn(pg)
    check("destroyed building replaced by its painted ruins", pg.evaluate("(()=>{const r=document.querySelector('#enemy .structure.gone .ruin'); return !!r && r.style.backgroundImage.includes('ruin_') && getComputedStyle(r).opacity==='1'})()"))
    check("all 20 ruin images load", pg.evaluate("Promise.all([...SHIPS,...FOES].flatMap(([n])=>[ruinURL(n,true),ruinURL(n,false)]).map(u=>new Promise(r=>{const i=new Image(); i.onload=()=>r(i.naturalWidth>100); i.onerror=()=>r(false); i.src=u;}))).then(a=>a.every(Boolean))"))
    check("ruins stay marked on later turns", pg.locator("#enemy .structure.gone[data-name='Abyss Watchtower']").count() == 1)
    pg.evaluate("aiPick=()=>state.player.ships[0].cells.find(([r,c])=>!state.player.shots[r][c])")
    before = pg.evaluate("state.player.ships[0].hits")
    shoot(pg, *enemy_water(pg)[0]); pg.wait_for_timeout(int(1000*0.15)+400)
    pg.wait_for_function(f"state.player.ships[0].hits==={before}+1", timeout=5000); pg.wait_for_timeout(30)
    check("hit visibly damages the player's building", "wounded" in pg.get_attribute("#player .structure[data-name=\"Poseidon's Palace\"]", "class"))

def t_attack_sounds(pg):
    fresh(pg); start_random(pg)
    water = "aiPick=()=>{for(let r=0;r<10;r++)for(let c=0;c<10;c++)if(!state.player.grid[r][c]&&!state.player.shots[r][c])return [r,c]}"
    pg.evaluate(water); pg.evaluate("audio.log.length=0")
    shoot(pg, *enemy_water(pg)[0]); wait_player_turn(pg)
    log = pg.evaluate("audio.log")
    check("misses (player and AI) play the underwater splash, never lightning/thunder", log.count("miss") == 2 and "hit" not in log and "sunk" not in log, str(log))
    pg.evaluate("aiPick=()=>state.player.ships[0].cells.find(([r,c])=>!state.player.shots[r][c])"); pg.evaluate("audio.log.length=0")
    big = [x for x in enemy_ships(pg) if len(x["cells"]) == 5][0]["cells"]
    shoot(pg, *big[0]); wait_player_turn(pg)
    log = pg.evaluate("audio.log")
    check("hits (player and AI) play the lightning crack and thunder, no splash", log.count("hit") == 2 and "miss" not in log, str(log))
    pg.click("#mute"); pg.evaluate("audio.log.length=0"); pg.evaluate(water)
    shoot(pg, *enemy_water(pg)[0]); wait_player_turn(pg)
    check("attack sounds respect mute (game still plays, master volume is 0)", pg.evaluate("audio.isMuted()") and pg.evaluate("audio.log").count("miss") == 2 and (pg.evaluate("audio.info().gain") or 0) < 0.01)
    pg.click("#mute")

def t_scene(pg):
    fresh(pg)
    check("painted underwater world loaded (backdrop art, light shafts, bubbles)", "bg.webp" in pg.evaluate("getComputedStyle(document.getElementById('scene')).backgroundImage") and pg.evaluate("new Promise(r=>{const i=new Image(); i.onload=()=>r(i.naturalWidth>=1500); i.onerror=()=>r(false); i.src='assets/bg.webp';})") and pg.locator("#scene .shaft").count() == 5 and pg.locator("#scene .bub").count() >= 10)
    check("scene never intercepts clicks", pg.evaluate("getComputedStyle(document.getElementById('scene')).pointerEvents") == "none")
    check("title and story shown", pg.inner_text("h1") == "ATLANTIS" and "WAR FOR THE LOST KINGDOM" in pg.inner_text("header"))
    start_random(pg)
    check("disabled buttons stay opaque so the scene can't show through their labels", pg.evaluate("['rotate','random','start','difficulty'].every(id=>{const e=document.getElementById(id); return e.disabled && getComputedStyle(e).opacity==='1'})"))
    fresh(pg)
    check("enemy board themed separately (purple/emerald)", pg.evaluate("getComputedStyle(document.querySelector('.panel.enemy')).borderTopColor") != pg.evaluate("getComputedStyle(document.querySelector('.panel.friendly')).borderTopColor"))
    fresh(pg); start_random(pg)
    for _ in range(6):
        shoot(pg, *enemy_water(pg)[0]); wait_player_turn(pg)
    pg.wait_for_timeout(1500)
    check("effect elements are cleaned up (no buildup)", pg.locator("#fx > *").count() == 0, str(pg.locator("#fx > *").count()))
    t = pg.evaluate("""async()=>{ const s=performance.now(); let n=0; await new Promise(r=>{ const f=()=>{ n++; if(performance.now()-s<1000) requestAnimationFrame(f); else r(); }; requestAnimationFrame(f); }); return n; }""")
    check("animations keep a smooth frame rate (>= 30 fps)", t >= 30, f"fps={t}")

def t_audio(pg):
    fresh(pg)
    check("no audio before user interaction", pg.evaluate("audio.info().created") is False)
    check("mute control visible", pg.is_visible("#mute") and "SOUND ON" in pg.inner_text("#mute"))
    pg.click("#random")
    info = pg.evaluate("audio.info()")
    check("audio starts after first interaction", info["created"] and info["musicOn"], str(info))
    pg.click("#start")
    check("music intensifies in battle", pg.evaluate("audio.info().level") == 1)
    pg.click("#mute"); pg.wait_for_timeout(300)
    info = pg.evaluate("audio.info()")
    check("mute silences master output", pg.get_attribute("#mute", "aria-pressed") == "true" and "MUTED" in pg.inner_text("#mute") and info["gain"] < 0.01, str(info))
    pg.reload(); pg.wait_for_function("typeof state !== 'undefined'")
    check("mute setting persists after reload", pg.get_attribute("#mute", "aria-pressed") == "true")
    pg.keyboard.press("m"); pg.wait_for_timeout(300)
    check("M key unmutes", pg.get_attribute("#mute", "aria-pressed") == "false" and pg.evaluate("audio.info().gain") > 0.5)
    pg.evaluate("() => { for (const n of ['lock','launch','hit','miss','sunk','victory','defeat','ping']) audio.play(n, true); }")
    check("all sound effects synthesize without errors", True)

def t_full_speed_game(pg):
    fresh(pg, ROOT); pg.select_option("#difficulty", "easy"); start_random(pg)
    cells = sink_all(pg, timeout=10000)
    wait_overlay(pg, 6000)
    check("full-speed game reaches ATLANTIS IS YOURS", pg.inner_text("#endTitle") == "ATLANTIS IS YOURS")
    check("full-speed game: AI took one turn per player shot", count_shots(pg, "player") == len(cells) - 1)

def t_desktop_layout(br):
    for w in (768, 1280):
        ctx = br.new_context(viewport={"width": w, "height": 900}); pg = ctx.new_page(); fresh(pg)
        off = pg.evaluate("[...document.querySelectorAll('.cell')].filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth}).length")
        check(f"all cells fully visible at {w}px width", off == 0, f"offscreen={off}")
        ctx.close()

def t_mobile_victory(br):
    ctx = br.new_context(viewport={"width": 375, "height": 700}); pg = ctx.new_page(); fresh(pg); start_random(pg)
    sink_all(pg); wait_overlay(pg)
    box = pg.locator("#endCard").bounding_box()
    check("victory screen fully visible on phone", box and box["y"] >= 0 and box["y"] + box["height"] <= 700, str(box))
    mb = pg.locator("#mute").bounding_box()
    check("mute control fully visible on phone, with text label", mb["x"] >= 0 and mb["x"] + mb["width"] <= 375 and pg.is_visible("#mute .lbl"), str(mb))
    pg.click("#viewBoard"); pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(100)
    mb = pg.locator("#mute").bounding_box(); tb = pg.locator("header .tag").bounding_box()
    check("mute control does not overlap title on phone", tb["y"] >= mb["y"] + mb["height"] or tb["x"] + tb["width"] <= mb["x"], f"{tb} {mb}")
    pg.evaluate("document.getElementById('enemy').scrollIntoView({block:'center'})"); pg.wait_for_timeout(150)
    sb = pg.locator("#status").bounding_box(); mb = pg.locator("#mute").bounding_box()
    check("mute control does not cover the sticky status text while scrolled (phone)", sb["y"] >= mb["y"] + mb["height"] or sb["x"] + sb["width"] <= mb["x"] or sb["y"] + sb["height"] <= mb["y"], f"{sb} {mb}")
    ctx.close()

def t_status_feedback(pg):
    fresh(pg); start_random(pg)
    shoot(pg, *enemy_water(pg)[0]); wait_player_turn(pg)
    log = pg.inner_text("#log")
    check("log shows player's own shot result after AI moves", "You fire at" in log, repr(log))
    check("log shows AI shot result", "Enemy fires at" in log, repr(log))

with sync_playwright() as p:
    br = p.chromium.connect_over_cdp("http://localhost:29229")
    ctx = br.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page(); errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    for t in [t_placement, t_orientation, t_random_fleets, t_shots, t_sinking, t_win, t_loss, t_ai_full_games,
              t_restart, t_status_feedback, t_effects, t_structures, t_attack_sounds, t_scene, t_audio, t_full_speed_game]:
        try: t(pg)
        except Exception: check(f"{t.__name__} crashed", False, traceback.format_exc().splitlines()[-1])
    for t in [t_mobile_layout, t_desktop_layout, t_touch_orientation, t_mobile_victory]:
        try: t(br)
        except Exception: check(f"{t.__name__} crashed", False, traceback.format_exc().splitlines()[-1])
    check("no JS errors", not errors, "; ".join(errors))
    ctx.close()

fails = [r for r in results if not r[1]]
for n, ok, d in results:
    print(("PASS " if ok else "FAIL ") + n + (f"  [{d}]" if d and not ok else ""))
print(f"\n{len(results)-len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
