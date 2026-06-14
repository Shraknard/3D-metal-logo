// Parametric: exports ONE part per run (relief OR backing OR handle) — no boolean
// union between dense meshes, so STL export stays fast. generate.py runs this
// twice (relief + backing) and concatenates the STLs; the overlapping volumes are
// unioned by the slicer at print time. The handle (stamp mode) is a third,
// independent run.
//
// Both logo SVGs share one canvas, imported center=false into the SAME frame, then
// translated by the RELIEF content centre and scaled so content width == target_w.
// import() returns mm directly (1 SVG unit -> k mm).
//
// `holes` are cylindrical pockets bored from the BACK (z=0) of the backing — used
// for magnet pockets (magnet mode) and the handle socket (stamp mode). They are
// only ever placed in regions with no relief above them (margins / lifted relief),
// so the concatenated relief does not refill them.

file        = "";    // relief SVG (absolute path)
backing_file = "";   // backing SVG (absolute path)
target_w    = 120;   // final relief width, mm
text_h      = 3.0;   // relief height, mm
base_h      = 1.6;   // backing thickness, mm
relief_z    = 0;     // relief Z offset, mm (stamp mode lifts it onto the slab face)
part        = 0;     // 0 relief | 1 backing offset (file) | 2 backing hull | 3 rectangle | 4 handle

k           = 0.352778;  // mm per SVG unit
cx          = 0;         // relief content centre x (SVG units)
cy          = 0;         // relief content centre y (SVG units)
content_w   = 1;         // relief content width  (SVG units)
content_h   = 1;         // relief content height (SVG units)
rect_marg   = 5;         // rectangle plaque margin, mm
holes       = [];        // list of [x, y, d, depth] pockets bored from z=0
// handle (part==4) — independent of the logo, sized to the socket
knob_d      = 25;        // grip diameter, mm
knob_h      = 18;        // grip height, mm
peg_d       = 7.8;       // peg diameter (socket_d - clearance), mm
peg_h       = 4.5;       // peg length, mm
pegs        = [[0, 0]];  // [x,y] of each peg, matching the socket holes
$fn         = 6;

s = target_w / (content_w * k);

module placed(f)
    scale([s, s, 1])
        translate([-cx * k, -cy * k, 0])
            import(f, center = false);

// Subtract every hole (bored from z=0 up) from the child solid.
module with_holes() {
    if (len(holes) == 0)
        children();
    else
        difference() {
            children();
            for (hpk = holes)
                translate([hpk[0], hpk[1], -0.01])
                    cylinder(d = hpk[2], h = hpk[3] + 0.01, $fn = 48);
        }
}

if (part == 0)
    translate([0, 0, relief_z])
        linear_extrude(height = text_h) placed(file);
else if (part == 1)
    with_holes() linear_extrude(height = base_h) placed(backing_file);
else if (part == 2)
    with_holes() linear_extrude(height = base_h) hull() placed(file);
else if (part == 3)
    with_holes() linear_extrude(height = base_h)
        square([target_w + 2 * rect_marg,
                content_h * k * s + 2 * rect_marg], center = true);
else if (part == 4) {
    // Multi-peg grip: an oblong grip (hull of knobs over every peg position)
    // with a peg on top of each. Prints base-down, pegs up, no support. A single
    // peg collapses the hull back to the original round knob.
    hull()
        for (p = pegs)
            translate([p[0], p[1], 0])
                cylinder(d = knob_d, h = knob_h, $fn = 64);
    for (p = pegs)
        translate([p[0], p[1], knob_h])
            cylinder(d = peg_d, h = peg_h, $fn = 48);
}
