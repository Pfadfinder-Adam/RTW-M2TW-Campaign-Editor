-- ============================================================================
-- Raze Settlement - a 4th choice on the capture scroll, for any mod on M2EX
-- (Medieval II: Total War). The Medieval II brother of Sack Settlement (REX).
--
-- Install: the tool puts this file in <mod>\eopData\eopScripts\ and adds one
-- line to that folder's luaPluginScript.lua (made if the mod has none) that
-- loads it. M2EX runs eopData\eopScripts\luaPluginScript.lua of the running
-- mod (its EOP-compatible Lua). A mod's own handlers keep working: this file
-- wraps them and calls them first.
--
-- What it does: when the player takes a settlement, a "Raze Settlement" button
-- appears under Occupy / Sack / Exterminate. It presses the engine's own
-- Exterminate (native loot, sounds and events all run), waits for the scroll to
-- close, then:
--   1. demolishes every building except the kept chains (core, roads),
--   2. removes most of the people and pays a reward,
--   3. hands the ruins to the rebels: give_settlement slave <town> - M2EX turns
--      it rebel and installs a fresh rebel garrison itself.
-- Plain Exterminate stays a plain extermination. Computer factions allowed
-- below raze whenever they exterminate a town.
-- Log lines start with "[RAZE]".
-- ============================================================================

-- @needs M2EX (Medieval II: Total War). Vanilla Medieval II runs no scripts - the add-on then does nothing.
local RAZE_ENABLED = true                    -- off keeps the file but does nothing
local RAZE_WHO = "player"                    -- player / everyone / ai / list
local RAZE_FACTIONS = {}                     -- for "list": faction names
local RAZE_GIVE_TO_REBELS = true             -- off: the razed town stays yours
local RAZE_GOLD_PER_BUILDING = 300           -- florins per building torn down
local RAZE_GOLD_PER_CITIZEN = 1              -- florins per inhabitant removed
local RAZE_PEOPLE_LEFT = 400                 -- inhabitants left in the ruins
local RAZE_KEEP_CHAINS = {
    core_building = true,
    core_castle_building = true,
    hinterland_roads = true,
}
local RAZE_BUTTON = true                     -- off: no 4th button; Exterminate razes for the allowed factions
local RAZE_BUTTON_LABEL = "Raze Settlement"
local RAZE_BUTTON_TIP = "Exterminate, tear down every building but the core and roads, and leave the ruins to the rebels"

local PREFIX = "[RAZE] "

local function log(msg)
    pcall(function() print(PREFIX .. tostring(msg)) end)
end

-- ---------------------------------------------------------------------------
-- small helpers, every engine call guarded: a missing name only logs
-- ---------------------------------------------------------------------------
local function try(f, ...)
    local ok, res = pcall(f, ...)
    if ok then return res end
    return nil
end

local function command(cmd)
    -- a script / console command through whichever entry this M2EX build offers
    local tries = {
        function() return M2TWEOP.runScriptCommand(cmd) end,
        function() return M2TW.runScriptCommand(cmd) end,
        function() return M2TWEOP.runConsoleCommand(cmd) end,
        function() return M2TW.runConsoleCommand(cmd) end,
    }
    for _, f in ipairs(tries) do
        local ok = pcall(f)
        if ok then
            log("command: " .. cmd)
            return true
        end
    end
    log("could not run: " .. cmd)
    return false
end

local function faction_name(fac)
    return try(function() return fac:getFactionName() end) or try(function() return fac.name end) or "?"
end

local function is_player(fac)
    local v = try(function() return fac.isPlayerControlled end)
    return v == true or v == 1
end

local function in_list(name)
    for _, f in ipairs(RAZE_FACTIONS) do
        if f == name then return true end
    end
    return false
end

local function allowed(fac)
    if not RAZE_ENABLED or fac == nil then return false end
    local player = is_player(fac)
    if RAZE_WHO == "player" then return player end
    if RAZE_WHO == "ai" then return not player end
    if RAZE_WHO == "list" then return in_list(faction_name(fac)) end
    return true                                 -- everyone
end

local function settlement_of(eventData)
    local s = try(function() return eventData.settlement end)
    if s then return s end
    local id = try(function() return eventData.regionID end) or try(function() return eventData.regionId end)
    if id then
        return try(function() return M2TW.stratMap.getRegion(id).settlement end)
    end
    return nil
end

local function settlement_name(s)
    return try(function() return s.name end) or try(function() return s:getName() end)
end

-- ---------------------------------------------------------------------------
-- the raze itself
-- ---------------------------------------------------------------------------
local function raze(s, fac)
    local name = settlement_name(s) or "?"
    local torn = 0
    local n = try(function() return s.buildingsNum end) or 0
    local chains = {}
    for i = 0, n - 1 do
        local b = try(function() return s:getBuilding(i) end)
        local chain = b and try(function() return b:getType() end)
        if chain and not RAZE_KEEP_CHAINS[chain] then
            chains[#chains + 1] = chain
        end
    end
    for _, chain in ipairs(chains) do
        if try(function() s:destroyBuilding(chain, false); return true end) then
            torn = torn + 1
        end
    end
    local people = try(function() return s.populationSize end) or 0
    local gone = math.max(0, people - RAZE_PEOPLE_LEFT)
    if gone > 0 then
        command(string.format("add_population %s %d", name, -gone))
    end
    local reward = torn * RAZE_GOLD_PER_BUILDING + gone * RAZE_GOLD_PER_CITIZEN
    if reward > 0 then
        try(function() fac.money = fac.money + reward end)
    end
    log(string.format("%s razed by %s: %d building(s) torn down, %d people gone, %d florins", name,
        faction_name(fac), torn, gone, reward))
    if RAZE_GIVE_TO_REBELS then
        command("give_settlement slave " .. name)
    end
end

-- ---------------------------------------------------------------------------
-- the player's 4th button on the capture scroll
-- ---------------------------------------------------------------------------
local captured = nil      -- { settlement, faction } of the player's last capture
local waiting = nil       -- a raze waiting for the scroll to close
local pressed = false

local function element(name)
    return try(function() return gameSTDUI.getUiElement(name) end)
end

local function scroll_open()
    local el = element("loot_settlement_scroll")
    return el ~= nil and (try(function() return el.xSize end) or 0) > 0
end

local function draw_button()
    if not RAZE_BUTTON or captured == nil or not allowed(captured.faction) then return end
    local ext = element("loot_settlement_extermintate_button")       -- the game's own spelling
    local sack = element("loot_settlement_sack_button")
    if ext == nil then return end
    local x, y = ext.xPos, ext.yPos
    local w, h = ext.xSize, ext.ySize
    if w == nil or w <= 0 then return end
    local step = h + 4
    if sack ~= nil and sack.yPos ~= nil then step = math.abs(ext.yPos - sack.yPos) end
    ImGui.SetNextWindowPos(x, y + step)
    ImGui.SetNextWindowBgAlpha(0.0)
    local flags = ImGuiWindowFlags.NoDecoration + ImGuiWindowFlags.NoMove + ImGuiWindowFlags.NoSavedSettings
    ImGui.Begin("##raze_settlement", true, flags)
    if ImGui.Button(RAZE_BUTTON_LABEL, w, h) then
        pressed = true
    end
    if ImGui.IsItemHovered() then
        ImGui.SetTooltip(RAZE_BUTTON_TIP)
    end
    ImGui.End()
    if pressed then
        pressed = false
        waiting = captured
        captured = nil
        try(function() ext:execute() end)                              -- the engine's own Exterminate
        log("Raze pressed - Exterminate runs first")
    end
end

local function tick()
    if waiting ~= nil and not scroll_open() then
        local job = waiting
        waiting = nil
        raze(job.settlement, job.faction)
    end
end

-- ---------------------------------------------------------------------------
-- hooks, wrapping whatever the mod already defined
-- ---------------------------------------------------------------------------
local prev_capture = onGeneralCaptureSettlement
function onGeneralCaptureSettlement(eventData)
    if prev_capture then pcall(prev_capture, eventData) end
    local fac = try(function() return eventData.faction end)
    local s = settlement_of(eventData)
    if s ~= nil and fac ~= nil and is_player(fac) then
        captured = { settlement = s, faction = fac }
    end
end

local prev_exterminate = onExterminatePopulation
function onExterminatePopulation(eventData)
    if prev_exterminate then pcall(prev_exterminate, eventData) end
    local fac = try(function() return eventData.faction end)
    if fac == nil or (RAZE_BUTTON and is_player(fac)) or not allowed(fac) then return end
    local s = settlement_of(eventData)
    if s ~= nil then
        if is_player(fac) then
            waiting = { settlement = s, faction = fac }               -- no button: Exterminate razes
        else
            raze(s, fac)                                               -- a computer faction allowed to raze
        end
    end
end

local prev_draw = draw
function draw(device)
    if prev_draw then pcall(prev_draw, device) end
    local ok, err = pcall(draw_button)
    if not ok then log("draw: " .. tostring(err)) end
    pcall(tick)
end

log("Raze Settlement loaded (" .. (RAZE_ENABLED and "on" or "off") .. ", who: " .. RAZE_WHO .. ")")
