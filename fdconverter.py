# Quick script to convert farlands items into BPHMod items
# Needs json5 to allow for comments in files and trailing commas

import argparse
import json5, json, os, math, decimal, shutil

# Placeholder value that gets picked up by cleanup function to remove the field
DELETEFIELD=-13371234567

def ExitError(filename,message):
    print("Error with",filename+":",message)
    os._exit(1)

def Warning(filename, message):
    print("Warning with",filename+":",message)

# Floating point range function
def frange(x, y, jump):
  while x < y:
    yield x
    x += jump

# Returns value if it exists at dictionary[key], returns default if it doesn't
def valOrDef(dictionary, key, default):
    if key in dictionary: return dictionary[key]
    else: return default

# Returns true if dictionary[key] is not null, not empty array, object or string (e.g has actual data to process)
def HasData(dictionary, key):
    if key not in dictionary: return False
    if len(dictionary[key])==0: return False
    return True

# Parses string to int or float, based on if it's representing a decimal number
def ToIntFloat(string):
    try:
        return int(string)
    except:
        return float(string)

# Clean up function, removes empty arrays, objects and any field marked with DELETEFIELD, 
def RemoveEmptyValues(obj):
    if isinstance(obj, dict):
        # Remove empty values from dictionaries
        obj = {k: RemoveEmptyValues(v) for k, v in obj.items() if RemoveEmptyValues(v)}
        return {k: v for k, v in obj.items() if v}
    elif isinstance(obj, list):
        # Remove empty values from lists
        return [RemoveEmptyValues(item) for item in obj if RemoveEmptyValues(item)]
    elif isinstance(obj, int):
        # Remove field if value is '#DELETEFIELD'
        return obj if obj != DELETEFIELD else None
    else:
        # Return non-empty values
        return obj

# Converts shape into ascii representation
def Convert_Shape(item_shape):
    # Find the maximum size and offset of the shape
    box = {'minx': 999, 'miny': 999, 'maxx':-999, 'maxy':-999}
    for shape in item_shape:
        offset = shape['Offset']
        size = shape['Size']
        
        box["minx"]=min(box["minx"],((decimal.Decimal(size["x"])/2)*-1)+(decimal.Decimal(offset["x"])))
        box["miny"]=min(box["miny"],((decimal.Decimal(size["y"])/2)*-1)+(decimal.Decimal(offset["y"])))
        box["maxx"]=max(box["maxx"],((decimal.Decimal(size["x"])/2))+(decimal.Decimal(offset["x"])))
        box["maxy"]=max(box["maxy"],((decimal.Decimal(size["y"])/2))+(decimal.Decimal(offset["y"])))
    
    new_shape=[]
    for y in frange(box["miny"],box["maxy"],1):
        line=""
        y+=decimal.Decimal('0.5')
        for x in frange(box["minx"],box["maxx"],1):
            
            x+=decimal.Decimal('0.5')
            filled=False
            for shape in item_shape:
                offset = shape['Offset']
                size = shape['Size']
                minx=((decimal.Decimal(size["x"])/2)*-1)+(decimal.Decimal(offset["x"]))
                miny=((decimal.Decimal(size["y"])/2)*-1)+(decimal.Decimal(offset["y"]))
                maxx=((decimal.Decimal(size["x"])/2))+(decimal.Decimal(offset["x"]))
                maxy=((decimal.Decimal(size["y"])/2))+(decimal.Decimal(offset["y"]))
                if x>=minx and x<= maxx and y>=miny and y<=maxy:
                    filled=True
                    break
            line+=("-","X")[filled]
        new_shape.append(line)
    new_shape=list(reversed(new_shape))
    return new_shape


def ProcessItemStatusEffect(ise_in):
    ise={}
    ise["apply_immediately"]=valOrDef(ise_in,"applyRightAway",DELETEFIELD)
    ise["type"]=ise_in["type"]
    ise["value"]=ToIntFloat(valOrDef(ise_in,"value",DELETEFIELD))
    ise["length"]=ise_in["length"]
    return ise

def ProcessTrigger(trigger_in):
    trigger_out={}
    trigger_out["trigger"]=valOrDef(trigger_in,"trigger","constant")
    if HasData(trigger_in,"areas"):
        if trigger_in["areas"]!=["self"]:
            trigger_out["trigger_area"]=trigger_in["areas"]
    if HasData(trigger_in,"types"):
        if trigger_in["types"]!=["Any"]:
            trigger_out["trigger_on_type"]=trigger_in["types"]
    if HasData(trigger_in,"areaDistance"):
        if trigger_in["areaDistance"]!="all":
            trigger_out["trigger_distance"]=trigger_in["areaDistance"]
    if HasData(trigger_in,"requiresActivation"):
        trigger_out["needs_activation"]=trigger_in["requiresActivation"]

    return trigger_out

def ProcessEffect(effect_in):
    effect_out={}
    effect_out["type"]=valOrDef(effect_in,"type","damage")
    effect_out["value"]=ToIntFloat(valOrDef(effect_in,"value",DELETEFIELD))
    effect_out["target"]=valOrDef(effect_in,"target",DELETEFIELD)
    if effect_out["target"]=="unspecified": effect_out["target"]=DELETEFIELD
    if HasData(effect_in,"mathType"):
        if effect_in["mathType"]=="multiplicative": effect_out["math"]="mul"
    if HasData(effect_in,"statuses"):
        effect_out["item_status_effects"]=[]
        for ise in effect_in["statuses"]:
            ise_out={}
            ise_out.update(ProcessItemStatusEffect(ise))
            effect_out["item_status_effects"].append(ise_out)
    return effect_out

def ProcessModifier(mod):
    mod_out={}
    if HasData(mod,"areas"):
        if mod["areas"]!=["self"]:
            mod_out["mod_area"]=mod["areas"]
    if HasData(mod,"affectedTypes"):
        if mod["affectedTypes"]!=["Any"]:
            mod_out["mod_types"]=mod["affectedTypes"]
    if HasData(mod,"areaDistance"):
        if mod["areaDistance"]!="all":
            mod_out["mod_distance"]=mod["areaDistance"]
    mod_out["length"]=valOrDef(mod,"length",DELETEFIELD)
    mod_out["mod_length"]=valOrDef(mod,"lengthForThisModifier",DELETEFIELD)
    mod_out.update(ProcessTrigger(mod["Trigger"]))
    mod_out["effects"]=[]
    for effect in mod["effects"]:
        mod_out["effects"].append(ProcessEffect(effect))
    return mod_out


def Convert(json_in, path):
    dir,filename=os.path.split(path)
    json_out={}
    sprites_to_copy=[]
    # item name
    try: json_out["name"]=json_in["Name"]
    except: ExitError(filename,"no valid name")

    # item sprite
    if "NumOfSprites" in json_in and int(json_in["NumOfSprites"])>1:
        sprite_filename=[]
        for i in range(0,int(json_in["NumOfSprites"])):
            sprite_filename.append("sprite@"+filename.split("@")[1].split(".json")[0]+"_"+str(i)+".png")
            if not os.path.exists(dir+"/"+sprite_filename[-1]):
                sprite_filename[-1]=sprite_filename[-1].replace(" ","_")
                if not os.path.exists(dir+"/"+sprite_filename[-1]):
                    sprite_filename[-1]=sprite_filename[-1].replace("_"," ")
                    if not os.path.exists(dir+"/"+sprite_filename[-1]):
                        ExitError(dir+"/"+sprite_filename[-1],"Sprite does not exist") 
            sprites_to_copy.append(dir+"/"+sprite_filename[-1])
    else:
        sprite_filename="sprite@"+filename.split("@")[1].split(".json")[0]+".png"
        if not os.path.exists(dir+"/"+sprite_filename):
            sprite_filename=sprite_filename.replace(" ","_")
            if not os.path.exists(dir+"/"+sprite_filename):
                sprite_filename=sprite_filename.replace("_"," ")
                if not os.path.exists(dir+"/"+sprite_filename):
                    ExitError(dir+"/"+sprite_filename,"Sprite does not exist") 
        sprites_to_copy.append(dir+"/"+sprite_filename)
    json_out["sprite"]=sprite_filename
    

    # type
    try: json_out["type"]=json_in["ItemType"]
    except: ExitError(filename,"no valid type")

    # rarity
    json_out["rarity"]=valOrDef(json_in,"Rarity","common"); 

    # player animation
    json_out["animation"]=valOrDef(json_in,"Animation",DELETEFIELD); 
    if json_out["animation"]=="UseItem":
        json_out["animation"]=DELETEFIELD

    # sound effects
    json_out["soundeffect"]=valOrDef(json_in,"SoundEffect",DELETEFIELD); 
    if json_out["soundeffect"]=="" or json_out["soundeffect"]=="None":
        json_out["soundeffect"]=DELETEFIELD

    # playtype
    json_out["playtype"]=valOrDef(json_in,"Playtype",DELETEFIELD); 
    if json_out["playtype"]=="active":
        json_out["playtype"]=DELETEFIELD
    
    #shape
    json_out["shape"]=Convert_Shape(json_in["ItemShape"])

    #use costs
    if HasData(json_in,"ItemUseCosts"):
        json_out["use_costs"]={}
        for cost in json_in["ItemUseCosts"]:
            if "type" in cost:
                json_out["use_costs"][cost["type"]]=int(cost["value"])
            else:
                if "value" in cost:
                    json_out["use_costs"]["energy"]=int(cost["value"])


    #flavor text
    if HasData(json_in,"Flavor"):
        json_out["flavor"]=json_in["Flavor"]
    else: 
        if HasData(json_in,"descriptions"):
            d=""
            for description in json_in["descriptions"]:
                if isinstance(description,dict):
                    ExitError("Old-school descriptions (converting to flavor text) cannot be multi-language. Please change field name to 'flavor'")
                d+=description
            json_out["flavor"]=d


    #use limits
    if HasData(json_in,"UseLimits"):
        json_out["use_limits"]={}
        for cost in json_in["UseLimits"]:
            if "type" not in cost:
                cost["type"]="total"
            json_out["use_limits"][cost["type"]]=int(cost["value"])

    #spawn_limits
    #supported characters
    if HasData(json_in,"SpawnLimits"):
        if HasData(json_in["SpawnLimits"],"Characters"):
            json_out["supported_characters"]=json_in["SpawnLimits"]["Characters"]
        if HasData(json_in["SpawnLimits"],"Zones"):
            json_out["found_in"]=json_in["SpawnLimits"]["Zones"]

    #combat effects
    if HasData(json_in,"Effects"):
        json_out["combat_effects"]=[]
        for effect in json_in["Effects"]:
            ceffect={}
            ceffect.update(ProcessTrigger(effect["Trigger"]))
            ceffect.update(ProcessEffect(effect["Effect"]))
            json_out["combat_effects"].append(ceffect)

    #create effects
    if HasData(json_in,"CreateEffects"):
        json_out["create_effects"]=[]
        for effect in json_in["CreateEffects"]:
            ceffect={}
            ceffect.update(ProcessTrigger(effect["Trigger"]))
            ceffect["create_type"]=valOrDef(effect,"createType","set")
            ceffect["create_areas"]=([["self"],effect["allowedAreas"]])[HasData(effect,"allowedAreas")]
            if ceffect["create_areas"]==["self"]:
                ceffect["create_areas"]=DELETEFIELD
            if HasData(effect,"areaDistance"):
                if effect["areaDistance"]!="all":
                    ceffect["create_distance"]=ceffect["areaDistance"]
            ceffect["create_items"]=valOrDef(effect,"itemsToCreate",[])
            ceffect["create_types"]=valOrDef(effect,"typesToCreate",[])
            ceffect["create_rarities"]=valOrDef(effect,"raritesToCreate",[])
            json_out["create_effects"].append(ceffect)

    # modifiers
    if HasData(json_in,"Modifiers"):
        json_out["modifiers"]=[]
        for mod in json_in["Modifiers"]:
            mod_out=ProcessModifier(mod)
            json_out["modifiers"].append(mod_out)

    # add modifiers
    if HasData(json_in,"AddModifiers"):
        json_out["add_modifiers"]=[]
        for addmod in json_in["AddModifiers"]:
            addmod_out={}
            addmod_out.update(ProcessTrigger(addmod["Trigger"]))
            if HasData(addmod,"areas"):
                if addmod["areas"]!=["self"]:
                    addmod_out["addmod_area"]=addmod["areas"]
            if HasData(addmod,"affectedTypes"):
                if addmod["affectedTypes"]!=["Any"]:
                    addmod_out["addmod_types"]=addmod["affectedTypes"]
            if HasData(addmod,"areaDistance"):
                if addmod["areaDistance"]!="all":
                    addmod_out["addmod_distance"]=addmod["areaDistance"]
            addmod_out["addmod_length"]=valOrDef(addmod,"lengthForThisModifier",DELETEFIELD)
            addmod_out["modifier"]=ProcessModifier(addmod["modifier"])
            json_out["add_modifiers"].append(addmod_out)

    # active item statuses
    if HasData(json_in,"ItemStatuses"):
        json_out["item_status_effects"]=[]
        for ise in json_in["ItemStatuses"]:
            json_out["item_status_effects"].append(ProcessItemStatusEffect(ise))

    # MovementEffects
    if HasData(json_in,"MovementEffects"):
        json_out["movement_effects"]=[]
        for move in json_in["MovementEffects"]:
            move_out={}
            move_out.update(ProcessTrigger(move["Trigger"]))
            if HasData(move,"MoveAreas"):
                if move["MoveAreas"]!=["self"]:
                    move_out["affected_area"]=move["MoveAreas"]
            if HasData(move,"affected_area_distance"):
                if move["areaDistance"]!="all":
                    move_out["affected_area_distance"]=move["areaDistance"]
            if HasData(move["Movement"],"move"):
                move_out.update(move["Movement"]["move"])
            if HasData(move["Movement"],"rotation"):
                move_out["rotation"]=move["Movement"]["rotation"]
            if HasData(move["Movement"],"type"):
                move_out["movement_type"]=move["Movement"]["type"]
            if HasData(move["Movement"],"length"):
                move_out["movement_type"]=move["Movement"]["length"]
            json_out["movement_effects"].append(move_out)

    # Movable Item
    json_out["movable"]={}
    json_out["movable"]["area"]=valOrDef(json_in,"MoveArea",DELETEFIELD)
    if json_out["movable"]["area"]=="self": json_out["movable"]["area"]=DELETEFIELD
    json_out["movable"]["distance"]=valOrDef(json_in,"MoveDistance",DELETEFIELD)
    if json_out["movable"]["distance"]=="all": json_out["movable"]["distance"]=DELETEFIELD
    json_out["movable"]["place_on_type"]=valOrDef(json_in,"MustBePlacedOnItemType",DELETEFIELD)
    if json_out["movable"]["place_on_type"]=="Grid": json_out["movable"]["place_on_type"]=DELETEFIELD
    json_out["movable"]["place_on_type_combat"]=valOrDef(json_in,"MustBePlacedOnItemTypeInCombat",DELETEFIELD)
    if json_out["movable"]["place_on_type_combat"]=="Grid": json_out["movable"]["place_on_type_combat"]=DELETEFIELD

            
    # manastone
    if HasData(json_in,"ManaStonePower"):
        manastonePower=int(json_in["ManaStonePower"])
        if manastonePower > 0:
            json_out["manastone"]={"max_mana":manastonePower}

    if HasData(json_in,"ContextMenuOptions"):
        print("CONTEXT MENU OPTIONS NOT SUPPORTED")


    json_out=RemoveEmptyValues(json_out)
    return RemoveEmptyValues(json_out), sprites_to_copy
    
    





if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='FDConverter.py',
        description='Converts FD items into BPHMod items. Not 100% compatible yet',)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--single", action="store_true",
                       help="Single File Mode")
    group.add_argument(
        "-f", "--folder", action="store_true", help="Folder Mode")
    parser.add_argument("-m", "--minify", action="store_true",
                       help="Minify output")
    parser.add_argument("-c", "--copy_sprites", action="store_true",
                       help="Copy sprites")
    parser.add_argument("input", help="Input file or folder")
    parser.add_argument("-o", "--output", help="Output file or folder. If not set, default folder is 'output', default filename is based on Item Name",
                        required=False, default="output")

    args = parser.parse_args()

    if(args.single):
        json_string=open(args.input).read()
        json_string=json_string[json_string.find('{'):] # Filter out garbage characters at the beginning of the file
        json_in=json5.loads(json_string)
        if(args.minify):
            jstring=json.dumps(Convert(json_in,args.input), separators=(',', ':'))
        else:
            jstring=json.dumps(Convert(json_in,args.input), indent=4)
        print(jstring)
    else:
        i=1
        for filename in os.listdir(args.input):
            if filename.endswith('.json') and filename.startswith("item"):
                f = os.path.join(args.input, filename)
                print(i,"Converting",filename)
                json_string=open(f).read()
                json_string=json_string[json_string.find('{'):] # Filter out garbage characters at the beginning of the file
                json_in=json5.loads(json_string)
                j,sprites_to_copy=Convert(json_in,f)
                if(args.minify):
                    jstring=json.dumps(j, separators=(',', ':'))
                else:
                    jstring=json.dumps(j, indent=4)
                open(args.output+"/Items/"+filename.split("@")[1].split(".")[-2].strip()+".item.json","w").write(jstring)
                if args.copy_sprites:
                    for sprite in sprites_to_copy:
                        print("Copying",os.path.basename(sprite))
                        shutil.copy2(sprite,args.output+"/Items/")
                i+=1



    
