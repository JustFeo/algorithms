-- Lua script to be executed by VCMI to extract map data.
-- This script will collect map dimensions, tile information (terrain, objects),
-- and information about other relevant map objects (towns, mines, resources, artifacts etc.)
-- The output should be structured as JSON and printed to stdout or saved to a file
-- that the Python map_exporter.py script can then read.

-- VCMI Lua API Reference (Conceptual - based on vcmi.eu documentation):
-- GAME: IGameInfoCallback API
-- SERVICES: Access to static game objects (artifacts, creatures, etc.)
-- require("core:json") -- Hypothetical JSON library if VCMI provides one, or use a manual builder.

-- For robust JSON creation, a library is preferred. If VCMI doesn't bundle one,
-- we might need to include a simple Lua JSON encoder or build strings carefully.
-- Let's assume a simple JSON encoder for now or careful string concatenation.

local function escape_json_string(value)
    local replacements = {
        ['\\'] = '\\\\',
        ['"'] = '\\"',
        ['\b'] = '\\b',
        ['\f'] = '\\f',
        ['\n'] = '\\n',
        ['\r'] = '\\r',
        ['\t'] = '\\t',
        ['/'] = '\\/' -- Though not strictly necessary for JSON, good practice
    }
    -- For characters not in replacements, check for control characters
    return '"' .. string.gsub(value, '[\\"%c%/]', function(c)
        if replacements[c] then
            return replacements[c]
        elseif string.byte(c) < 32 then
            return string.format('\\u%04x', string.byte(c)) -- Control characters
        else
            return c -- Should not happen with the regex, but as a fallback
        end
    end) .. '"'
end

local function serialize_to_json(lua_table)
    local result_parts = {}
    local function serialize_internal(tbl)
        if type(tbl) == "table" then
            local is_array = true
            local max_key = 0
            for k, _ in pairs(tbl) do
                if type(k) ~= "number" or k < 1 or k > #tbl + 1000 then -- Heuristic for array detection
                    is_array = false
                    break
                end
                if k > max_key then max_key = k end
            end
            if max_key > 0 and #tbl ~= max_key then is_array = false end


            if is_array then
                table.insert(result_parts, "[")
                for i = 1, #tbl do
                    serialize_internal(tbl[i])
                    if i < #tbl then table.insert(result_parts, ",") end
                end
                table.insert(result_parts, "]")
            else -- Object
                table.insert(result_parts, "{")
                local first = true
                for k, v in pairs(tbl) do
                    if not first then table.insert(result_parts, ",") end
                    serialize_internal(tostring(k)) -- Ensure key is string
                    table.insert(result_parts, ":")
                    serialize_internal(v)
                    first = false
                end
                table.insert(result_parts, "}")
            end
        elseif type(tbl) == "string" then
            table.insert(result_parts, escape_json_string(tbl))
        elseif type(tbl) == "number" or type(tbl) == "boolean" then
            table.insert(result_parts, tostring(tbl))
        elseif type(tbl) == "nil" then
            table.insert(result_parts, "null")
        else
            table.insert(result_parts, escape_json_string("unsupported_type:" .. type(tbl)))
        end
    end

    serialize_internal(lua_table)
    return table.concat(result_parts)
end


-- Main function to gather data
local function get_map_data()
    local map_data = {}

    if not GAME then
        print("Error: GAME API not available. This script must be run within VCMI environment.")
        -- For testing outside VCMI, return dummy data
        return {
            map_name = "Dummy Map (GAME API not found)",
            width = 2,
            height = 2,
            tiles = {
                {x=0, y=0, terrain_type="grass", objects={}, reward=0, movement_cost=100},
                {x=1, y=0, terrain_type="dirt", objects={}, reward=5, movement_cost=100},
                {x=0, y=1, terrain_type="sand", objects={{type="resource", name="gold", amount=100}}, reward=100, movement_cost=150},
                {x=1, y=1, terrain_type="swamp", objects={{type="monster", name="Gnoll", strength=10}}, reward=0, movement_cost=175}
            },
            objects = { -- Global list of specific objects if needed, tiles can reference them by ID or contain full info
                {id="obj1", type="resource", name="gold", amount=100, x=0, y=1},
                {id="obj2", type="monster", name="Gnoll", strength=10, x=1, y=1}
            },
            heroes = {}, -- Placeholder for hero data
            towns = {}   -- Placeholder for town data
        }
    end

    map_data.map_name = GAME:getMapName() -- Hypothetical API call
    map_data.width = GAME:getMapWidth()   -- Hypothetical API call
    map_data.height = GAME:getMapHeight() -- Hypothetical API call
    map_data.tiles = {}
    map_data.objects = {} -- For objects not directly on tiles or for a global list

    for y = 0, map_data.height - 1 do
        for x = 0, map_data.width - 1 do
            local tile_info = {}
            tile_info.x = x
            tile_info.y = y

            -- Hypothetical API calls, actual functions will depend on VCMI Lua API
            tile_info.terrain_type = GAME:getTerrainType(x, y)
            tile_info.terrain_subtype = GAME:getTerrainSubtype(x,y) -- e.g. specific grass type
            tile_info.road_type = GAME:getRoadType(x,y) -- nil if no road, else "dirt", "gravel", "cobblestone"
            tile_info.has_road = tile_info.road_type ~= nil

            tile_info.objects = {} -- Objects on this specific tile
            local map_objects_on_tile = GAME:getObjectsOnTile(x, y) -- Returns a list/table of object handles/data

            local tile_reward = 0

            for _, obj_handle in ipairs(map_objects_on_tile or {}) do
                local obj_data = {}
                -- Common properties
                obj_data.type_id = GAME:getObjectType(obj_handle) -- numeric ID
                obj_data.type_name = SERVICES:getObjectName(obj_data.type_id) -- string name like "Resource" or "Artifact"
                obj_data.x = x -- Redundant if only in tile_info.objects, useful for global object list
                obj_data.y = y

                -- Type-specific properties
                if obj_data.type_name == "Resource" then
                    obj_data.resource_type = GAME:getResourceType(obj_handle) -- e.g. "wood", "gold"
                    obj_data.amount = GAME:getResourceAmount(obj_handle)
                    -- Calculate reward based on resource type and amount
                    -- tile_reward = tile_reward + calculate_resource_value(obj_data.resource_type, obj_data.amount)
                elseif obj_data.type_name == "Artifact" then
                    obj_data.artifact_id = GAME:getArtifactId(obj_handle)
                    -- tile_reward = tile_reward + calculate_artifact_value(obj_data.artifact_id)
                elseif obj_data.type_name == "Monster" then
                    obj_data.monster_id = GAME:getMonsterId(obj_handle)
                    obj_data.quantity = GAME:getMonsterQuantity(obj_handle)
                    obj_data.disposition = GAME:getMonsterDisposition(obj_handle)
                    -- Guards usually don't give direct reward, but cost to fight
                elseif obj_data.type_name == "Mine" then
                    obj_data.mine_type = GAME:getMineType(obj_handle) -- e.g. "gold_mine", "ore_mine"
                    obj_data.owner = GAME:getMineOwner(obj_handle)
                -- Add more object types: dwellings, garrisons, towns, Pandora's Boxes, etc.
                end
                table.insert(tile_info.objects, obj_data)
            end
            tile_info.reward = tile_reward -- Sum of rewards from objects on this tile
            table.insert(map_data.tiles, tile_info)
        end
    end

    -- TODO: Extract global objects like heroes, towns if not covered by tile iteration
    -- map_data.heroes = GAME:getAllHeroesInfo()
    -- map_data.towns = GAME:getAllTownsInfo()

    return map_data
end

-- Execute and print JSON
local data_to_serialize = get_map_data()
local json_output = serialize_to_json(data_to_serialize)

-- Output the JSON. This might go to stdout or a file depending on how VCMI runs scripts.
-- For now, assume printing to stdout is one way Python script can capture it.
print(json_output)

-- Alternative: Write to a file if VCMI Lua API supports it.
-- local file = io.open("map_export.json", "w")
-- if file then
--     file:write(json_output)
--     file:close()
-- else
--     print("Error: Could not open file for writing map_export.json")
-- end
-- VCMI specific log for debugging within VCMI
-- logDebug("Map data extraction complete. JSON output generated.")
