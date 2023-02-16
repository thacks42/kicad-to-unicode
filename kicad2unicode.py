#!/usr/bin/env python3
from pyparsing import nestedExpr
import argparse
import copy
import re
import pprint

EMPTY = ((0,0),
    [
    ])

R = ((0,0),
    [
     "╭┴╮",
     "│ │",
     "│ │",
     "│ │",
     "╰┬╯"
    ])

R_SMALL = ((0,0),
    [
     "╭┴╮",
     "│ │",
     "╰┬╯"
    ])

R_PHOTO = ((0,0),
    [
     "╭┴╮",
     "│ │",
     "│⇉│",
     "│ │",
     "╰┬╯"
    ])

C = ((0,0),
    [
     " │ ",
     "▁╽▁",
     "   ",
     "▔╿▔",
     " │ "
    ])

L = ((0,0),
    [
     " │ ",
     " ) ",
     " ) ",
     " ) ",
     " │ "
    ])

L_SMALL = ((0,0),
    [
     " ) ",
     " ) ",
     " ) ",
    ])

L_FERRITE = ((0,0),
    [
     " │ ",
     " )║",
     " )║",
     " )║",
     " │ "
    ])

C_SMALL = ((0,0),
    [
     "▁╽▁",
     "   ",
     "▔╿▔",
    ])

LED = ((0,0),
    [
     " │ ",
     "▁╽▁",
     "╲⇉╱",
     "━┳━",
     " │ "
    ])

LED2 = ((0,0),
    [
     " │ ",
     "━┷━",
     "╱⇉╲",
     "▔╿▔",
     " │ "
    ])

DIODE = ((0,0),
    [
     " │ ",
     "▁╽▁",
     "╲ ╱",
     "━┳━",
     " │ "
    ])

DIODE2 = ((0,0),
    [
     " │ ",
     "━┷━",
     "╱ ╲",
     "▔╿▔",
     " │ "
    ])

BJT = ((1,0),
    [
     "     │  ",
     " ╭───┼─╮",
     " │  ╱  │",
     "─┼─┥   │",
     " │  ➘  │",
     " ╰───┼─╯",
     "     │  "
    ])

BJT2 = ((0,0),
    [
     "     │ ",
     "     │ ",
     "    ╱  ",
     "───┥   ",
     "    ➘  ",
     "     │ ",
     "     │ "
    ])

NMOS = ((1,0),
    [
     "     │  ",
     " ╭───┼─╮",
     " │ │┠┘ │",
     "─┼─┥←┐ │",
     " │ │┠┤ │",
     " ╰───┼─╯",
     "     │  "
    ])

NMOS2 = ((1,0),
    [
     "     │  ",
     "     │  ",
     "   │┠┘  ",
     "───┥←┐  ",
     "   │┠┤  ",
     "     │  ",
     "     │  "
    ])

PMOS = ((1,0),
    [
     "     │  ",
     " ╭───┼─╮",
     " │ │┠┘ │",
     "─┼─┥→┐ │",
     " │ │┠┤ │",
     " ╰───┼─╯",
     "     │  "
    ])

PMOS2 = ((1,0),
    [
     "     │  ",
     "     │  ",
     "   │┠┘  ",
     "───┥→┐  ",
     "   │┠┤  ",
     "     │  ",
     "     │  "
    ])

JUNCTION = ((0,0),
    [
     "╋"
    ])

GND = ((0,1),
      [
       "▔▔▔"
      ],
      (-1,0))

PWR = ((0,-1),
      [
        "━┯━",
        " │ "
      ],
      (-1,1))

POLYLINE_BASE = 0x13000
WIRE_BASE = 0x14000
BASE_MASK = 0xff000

UP = 1
RIGHT = 2
DOWN = 4
LEFT = 8
JUNC = 16

UP_DASHED = 32
RIGHT_DASHED = 64
DOWN_DASHED = 128
LEFT_DASHED = 256

    
def draw_symbol(fb, symbol, pos):
    if len(symbol[1]) == 0:
        return
    pos_x = int(pos[0] + 0.5)
    pos_y = int(pos[1] + 0.5)
    rot = pos[2]
    
    symbol_data = symbol[1]
    
    x_start = pos_x - len(symbol_data[0])//2 + symbol[0][0]
    y_start = pos_y - len(symbol_data)//2 + symbol[0][1]
    for y in range(len(symbol_data)):
        for x in range(len(symbol_data[0])):
            fb[y_start + y][x_start + x] = symbol_data[y][x]
                

def draw_reference(fb, ref, offset = (0,0)):
    pos = ref[0]
    pos_x = int(pos[0] + 0.5)
    pos_y = int(pos[1] + 0.5)
    rot = pos[2]
    
    pos_x += offset[0]
    pos_y += offset[1]
    
    r = ref[1]
    if rot == 0 or True:
        for x in range(len(r)):
            fb[pos_y-1][pos_x + x] = r[x]

def draw_value(fb, val, offset = (0,0)):
    draw_reference(fb, val, offset)

def draw_text(fb, t):
    pos = t[0]
    pos_x = int(pos[0] + 0.5)
    pos_y = int(pos[1] + 0.5)
    
    for i,c in enumerate(t[2]):
        fb[pos_y-1][pos_x+i] = c

def add_direction_to_metachar(fb, x, y, direction, base):
    cur = fb[y][x]
    if cur == ' ':
        fb[y][x] = chr(base | direction)
    else:
        if ord(cur) & BASE_MASK == base:
            fb[y][x] = chr(ord(cur) | direction)
        else: #existing other thing
            fb[y][x] = chr(ord(cur) | base | direction)
    
        

def draw_polylines(fb, lines):
    for l in lines:
        start = l[0]
        end = l[1]
        x0 = min(start[0], end[0])
        x1 = max(start[0], end[0])
        
        y0 = min(start[1], end[1])
        y1 = max(start[1], end[1])
        
        
        horizontal = LEFT_DASHED | RIGHT_DASHED
        vertical = UP_DASHED | DOWN_DASHED
        
        style = l[2]
        if style == "solid":
            horizontal = LEFT | RIGHT
            vertical = UP | DOWN 
            
        if y0 == y1: #horizontal
            add_direction_to_metachar(fb, x0, y0, RIGHT, POLYLINE_BASE)
            add_direction_to_metachar(fb, x1, y1, LEFT, POLYLINE_BASE)
            
            for x in range(x0+1, x1):
                add_direction_to_metachar(fb, x, y0, horizontal, POLYLINE_BASE)
        
        elif x0 == x1: #vertical
            add_direction_to_metachar(fb, x0, y0, DOWN, POLYLINE_BASE)
            add_direction_to_metachar(fb, x1, y1, UP, POLYLINE_BASE)
            
            for y in range(y0 + 1, y1):
                add_direction_to_metachar(fb, x0, y, vertical, POLYLINE_BASE)
                
        else:
            print("error, polyline neither horizontal nor vertical")
        


def draw_wires(fb, wires):
    for w in wires:
        start = w[0]
        end = w[1]
        x0 = min(start[0], end[0])
        x1 = max(start[0], end[0])
        
        y0 = min(start[1], end[1])
        y1 = max(start[1], end[1])
        
        horizontal = LEFT | RIGHT
        vertical = UP | DOWN 
        
        if y0 == y1: #horizontal
            add_direction_to_metachar(fb, x0, y0, RIGHT, WIRE_BASE)
            add_direction_to_metachar(fb, x1, y1, LEFT, WIRE_BASE)
            
            for x in range(x0+1, x1):
                add_direction_to_metachar(fb, x, y0, horizontal, WIRE_BASE)
        
        elif x0 == x1: #vertical
            add_direction_to_metachar(fb, x0, y0, DOWN, WIRE_BASE)
            add_direction_to_metachar(fb, x1, y1, UP, WIRE_BASE)
            
            for y in range(y0 + 1, y1):
                add_direction_to_metachar(fb, x0, y, vertical, WIRE_BASE)
                
        else:
            print("error, wire neither horizontal nor vertical")

def draw_junctions(fb, junctions):
    for i in range(len(junctions)):
        pos = junctions[i]
        pos_x = int(pos[0] + 0.5)
        pos_y = int(pos[1] + 0.5)
        add_direction_to_metachar(fb, pos_x, pos_y, JUNC, WIRE_BASE)


def draw_device(fb, device):
    pos, outlines, pins, name, ref, val = device
    lines = []
    
    for o in outlines:
        
        start = (o[0][0] + pos[0], o[0][1] + pos[1])
        end = (o[1][0] + pos[0], o[1][1] + pos[1])
        lines.append( ((start[0], start[1]), (start[0], end[1])) )
        lines.append( ((start[0], end[1]), (end[0], end[1])) )
        lines.append( ((end[0], end[1]), (end[0], start[1])) )
        lines.append( ((end[0], start[1]), (start[0], start[1])) )
    
    draw_value(fb, val, (-len(val[1])//2+1,1))
    
    texts = []
    
    for i in pins:
        start = (i[0][0] + pos[0], i[0][1] + pos[1])
        text_pos = start
        name_pos = start
        rotation = i[0][2]
        length = i[1]-1
        number = i[2]
        name = i[3]
        end = None
        
        
        if rotation == 0:
            start = (start[0]+1, start[1])
            end = (start[0] + length, start[1])
            name_pos = (name_pos[0] + 4, name_pos[1] + 1)
        elif rotation == 90:
            start = (start[0], start[1]-1)
            end = (start[0], start[1] - length)
            name_pos = (name_pos[0]-len(name)//2, name_pos[1] - 2)
            text_pos = (text_pos[0]-1, text_pos[1])
        elif rotation == 180:
            start = (start[0]-1, start[1])
            end = (start[0] - length, start[1])
            name_pos = (name_pos[0] - len(name) - 3, name_pos[1] + 1)
        elif rotation == 270:
            start = (start[0], start[1]+1)
            end = (start[0], start[1] + length)
            name_pos = (name_pos[0]-len(name)//2, name_pos[1] + 4)
            text_pos = (text_pos[0]-1, text_pos[1]+2)
        else:
            print("rotation of device pins not implemented!")
            continue
        
        lines.append((start, end))
        texts.append((text_pos, None, number))
        if name != '~':
            texts.append((name_pos, None, name))
    
    draw_wires(fb, lines)
    for t in texts:
        draw_text(fb, t)




def select_polyline_piece(c):
    polyline_dashed_pieces = ['x', ' ', ' ', '╰', ' ', '╎', '╭', '├', ' ', '╯', '╌', '┴', '╮', '┤', '┬', '┼']
    polyline_solid_pieces =  ['x', ' ', ' ', '╰', ' ', '│', '╭', '├', ' ', '╯', '─', '┴', '╮', '┤', '┬', '┼']
    directions = c & 0x1ff
    num_directions = c.bit_count()
    if num_directions == 0:
        print("invalid polyline metachar...")
    elif num_directions == 2:
        dashed = (directions & 0x1e0) != 0
        solid = (directions & 0xf) != 0
        if dashed and not solid:
            return polyline_dashed_pieces[directions >> 5]
        if solid and not dashed:
            return polyline_solid_pieces[directions]
        directions = (directions & 0xf) | (directions >> 5)
        return polyline_solid_pieces[directions]
    else:
        directions = (directions & 0xf) | (directions >> 5)
        return polyline_solid_pieces[directions]
    

def render(fb):
    wire_endpieces =     ['x', '╽', '╾', '└', '╿', '│', '┌', '├', '╼', '┘', '─', '┴', '┐', '┤', '┬', '┼']
    junctions =          ['x', '╽', '╾', '└', '╿', '┃', '┏', '┣', '╼', '┛', '━', '┻', '┓', '┫', '┳', '╋']
    
    fb_2 = copy.deepcopy(fb)
    for y in range(len(fb)):
        for x in range(len(fb[0])):
            if ord(fb[y][x]) & BASE_MASK == POLYLINE_BASE:
                fb_2[y][x] = select_polyline_piece(ord(fb[y][x]) & 0x1ff)
            
            elif ord(fb[y][x]) & BASE_MASK == WIRE_BASE:
                if ord(fb[y][x]) & JUNC:
                    fb_2[y][x] = junctions[ord(fb[y][x]) & 15]
                else:
                    fb_2[y][x] = wire_endpieces[ord(fb[y][x]) & 15]
            elif ord(fb[y][x]) & BASE_MASK == (WIRE_BASE | POLYLINE_BASE):
                fb_2[y][x] = select_polyline_piece(ord(fb[y][x]) & 0x1ff)
    
    start_x = 999999
    start_y = 999999
    end_x = 0
    end_y = 0
    
    for y in range(len(fb_2)):
        for x in range(len(fb_2[0])):
            if fb_2[y][x] != ' ':
                start_x = min(start_x, x)
                start_y = min(start_y, y)
                end_x = max(end_x, x)
                end_y = max(end_y, y)
    end_x += 1
    end_y += 1
    for y in range(start_y, end_y):
        for x in range(start_x, end_x):
            print(fb_2[y][x], end='')
        print()

def parse_position(line, norm):
    if line[0] == 'at':
        x = int(round(float(line[1]) * norm ))
        y = int(round(float(line[2]) * norm ))
        rot = 0.0
        if len(line) > 3:
            rot = float(line[3])
        return (x,y,rot)

def parse_reference(line, norm):
    for k in range(len(line)):
        if line[k][0] == 'property':
            if line[k][1] == '"Reference"':
                for s in line[k]:
                    if s == 'hide':
                        return None
                value = line[k][2].strip('"')
                pos = parse_position(line[k][4], norm)
                return (pos, value)

def parse_value(line, norm):
    for k in range(len(line)):
        if line[k][0] == 'property':
            if line[k][1] == '"Value"':
                for s in line[k]:
                    if s == 'hide':
                        return None
                value = line[k][2].strip('"')
                pos = parse_position(line[k][4], norm)
                return (pos, value)

def parse_line_coords(line, norm):
    result = (int(round(float(line[1]) * norm)), int(round(float(line[2]) * norm)) )
    return result

def parse_rectangle(line, norm):
    start = ( -int(round(float(line[1][1]) * norm)), -int(round(float(line[1][2]) * norm)) )
    end = ( -int(round(float(line[2][1]) * norm )), -int(round(float(line[2][2]) * norm)) )
    if start[0] > end[0]:
        return (end, start)
    return (start, end)

def parse_pin(line, norm):
    pos = None
    length = None
    number = None
    name = None
    for i in line:
        if type(i) is list:
            if i[0] == 'at':
                pos = parse_position(i,norm)
            if i[0] == 'length':
                length = int(round(float(i[1]) * norm))
            if i[0] == 'number':
                number = i[1].strip('"')
            if i[0] == 'name':
                name = i[1].strip('"')
    return ((pos[0], -pos[1], pos[2]), length, number, name)
                

def lookup_outline(prop, norm):
    outlines = []
    for i in prop:
        if type(i) is list:
            if i[0] == 'rectangle':
                outlines.append(parse_rectangle(i, norm))
    return outlines
                

def lookup_pins(prop, norm):
    pins = []
    for i in prop:
        if type(i) is list:
            if i[0] == 'pin' and 'hide' not in i:
                pins.append(parse_pin(i, norm))
    return pins

def lookup_device(data, name, norm):
    pins = []
    outlines = []
    for i in data[0]:
        if i[0] == 'lib_symbols':
            for symbol in i:
                if symbol[0] == 'symbol':
                    if symbol[1] == name:
                        for prop in symbol:
                            if type(prop) is list:
                                if prop[0] == 'symbol':
                                    new_outlines = lookup_outline(prop, norm)
                                    for o in new_outlines:
                                        outlines.append(o)
                                    new_pins = lookup_pins(prop, norm)
                                    for p in new_pins:
                                        pins.append(p)
    
    return (outlines, pins)
                                    

def init_argparse():
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] FILE",
        description="Convert Kicad Schematic file to Unicode"
    )
    parser.add_argument(
        "-r", "--draw-references", action=argparse.BooleanOptionalAction, default=False, help="draw kicad reference labels"
    )
    parser.add_argument(
        "-v", "--draw-values", action=argparse.BooleanOptionalAction, default=True, help="draw kicad value labels"
    )
    parser.add_argument(
        "-b", "--box-transistors", action=argparse.BooleanOptionalAction, default=True, help="draw boxes around transistors (bjt/fet)"
    )
    parser.add_argument(
        "--width", type=int, default=190, help = "width of the framebuffer"
    )
    parser.add_argument(
        "--height", type=int, default=80, help = "height of the framebuffer"
    )
    parser.add_argument('file', nargs=1)

    return parser

def main():
    parser = init_argparse()
    args = parser.parse_args()
    
    if not args.file:
        print("no file")
        return None

    filename = args.file[0]
    
    draw_references = args.draw_references
    draw_values = args.draw_values
    box_transistors = args.box_transistors
    
    fb_width = args.width
    fb_heigth = args.height
    
    if not box_transistors:
        global NMOS
        global PMOS
        global BJT
        NMOS = NMOS2
        PMOS = PMOS2
        BJT = BJT2
    
    data = ""

    with open(filename) as f:
        data = f.read()
        
    
    spacing = 2.54
    norm = 2/spacing
    
    wires = []
    junctions = []
    devices = []
    texts = []
    lines = []
    
    complex_devices = []
    
    parsed = nestedExpr('(',')').parseString(data).asList()
    for i in parsed[0]:
        if i[0] == 'wire':
            start = i[1][1]
            end = i[1][2]
            
            start_coords = parse_line_coords(start, norm)
            end_coords = parse_line_coords(end, norm)
            wires.append((start_coords, end_coords))
        
        if i[0] == 'junction':
            pos = parse_position(i[1], norm)
            junctions.append(pos)
        
        if i[0] == 'polyline':
            start = i[1][1]
            end = i[1][2]
            style = i[2][2][1]
            
            start_coords = parse_line_coords(start, norm)
            end_coords = parse_line_coords(end, norm)
            lines.append( (start_coords, end_coords, style) )
        
        if i[0] == 'symbol' :
            if i[1][1] == '"Device:R"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, R, ref, val) )
            elif i[1][1] == '"Device:R_Small"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, R_SMALL, ref, val) )
            elif i[1][1] == '"Device:R_Photo"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, R_PHOTO, ref, val) )
            elif i[1][1] == '"Device:C"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, C, ref, val) )
            elif i[1][1] == '"Device:C_Small"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, C_SMALL, ref, val) )
            elif i[1][1] == '"Device:L"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, L, ref, val) )
            elif i[1][1] == '"Device:L_Small"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, L_SMALL, ref, val) )
            elif i[1][1] == '"Device:L_Ferrite"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, L_FERRITE, ref, val) )
            elif i[1][1] == '"Device:LED"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                if pos[2] == 270:
                    devices.append( (pos, LED2, ref, val) )
                else:
                    devices.append( (pos, LED, ref, val) )
            elif i[1][1] == '"power:GND"':
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                ref = None
                val = parse_value(i, norm)
                devices.append( (pos, GND, ref, val) )
            elif re.match('"power:', i[1][1]):
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                ref = None
                val = parse_value(i, norm)
                devices.append( (pos, PWR, ref, val) )
            elif re.match('"Diode:', i[1][1]):
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                if pos[2] == 270:
                    devices.append( (pos, DIODE2, ref, val) )
                else:
                    devices.append( (pos, DIODE, ref, val) )
            elif re.match('"Transistor_BJT', i[1][1]):
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, BJT, ref, val) )
            elif re.match('"Device:Q_NMOS', i[1][1]):
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, NMOS, ref, val) )
            elif re.match('"Device:Q_PMOS', i[1][1]):
                pos = parse_position(i[2], norm)
                ref = parse_reference(i, norm)
                val = parse_value(i, norm)
                devices.append( (pos, PMOS, ref, val) )
            else:#re.match('"Connector', i[1][1]):
                name = i[1][1]
                pos = parse_position(i[2], norm)
                ref = None
                val = parse_value(i, norm)
                outlines, pins = lookup_device(parsed,name, norm)
                complex_devices.append( (pos, outlines, pins, name, ref, val) )
            #else:
            #    print("unknown symbol found:")
            #    print(i)
        
        if i[0] == 'global_label' :
            pos = parse_position(i[3], norm)
            rot = pos[2]
            val = None
            ref = None
            name = i[1].strip('"')
            LABEL = None
            if rot == 180:
                LABEL = ((-len(name)//2-1,0),[name + " ᐅ"])
            if rot == 0:
                LABEL = ((len(name)//2+2,0),["ᐊ " + name])
            
            devices.append( (pos, LABEL, ref, val) )
            
        if i[0] == 'text':
            pos = parse_position(i[2], norm)
            val = i[1].strip('"')
            ref = None
            if '\\n' in val:
                vals = val.split('\\n')
                pos = (pos[0], pos[1] - len(vals)+1)
                for n,v in enumerate(vals):
                    texts.append( ((pos[0],pos[1] + n), ref, v) )
            else:
                texts.append( (pos, ref, val) )
    
    fb = [[' '] * fb_width for _ in range(fb_heigth)]
    
    for d in complex_devices:
        draw_device(fb, d)
    
    draw_wires(fb, wires)
    draw_junctions(fb, junctions)
    
    for d in devices:
        draw_symbol(fb, d[1], d[0])
        if len(d) > 2 and d[2] is not None and draw_references:
            draw_reference(fb, d[2])
            pass
        if len(d) > 3 and d[3] is not None and draw_values:
            offset = (0,0)
            if len(d[1]) > 2:
                offset = d[1][2]
            draw_value(fb, d[3],offset)
    
    for t in texts:
        draw_text(fb, t)
    
    draw_polylines(fb, lines)
    
    render(fb)

if __name__ == "__main__":
    main()
